from simpledbf import Dbf5
from config import *
import sqlalchemy
import keyring
import pandas as pd
import time

CONFIG_PATH = 'settings_Petrykivka.ini'
cfg = Config(CONFIG_PATH)


def connector():
    driver = 'ODBC Driver 17 for SQL Server'
    server = 'powerbivm1.dpst.kola'
    port = 1433
    database = 'petrykivka_test'
    username = 'sa'
    password = keyring.get_password('SQL', username)
    print(f'Connecting to SQL DB {database}...')
    try:
        engine = sqlalchemy.create_engine(f'mssql+pyodbc://{username}:{password}@{server}'
                                          f':{port}/{database}'
                                          f'?driver={driver}')
        engine.connect()
    except sqlalchemy.exc.InterfaceError as e:
        print(f"Can't connection to DB {database}: " + str(e))
    else:
        print(f'Connected to SQL DB {database}!')
        return engine


def get_table_fields_name(table_name: str, db_name='') -> pd.read_sql_query:
    try:
        pd_query = pd.read_sql_query("SELECT COLUMN_NAME "
                                     "FROM INFORMATION_SCHEMA.COLUMNS "
                                     f"WHERE TABLE_NAME = N'{table_name}'",
                                     connector())
        if pd_query.empty:
            raise NameError('EmptyDataFrame')
        return pd_query.values.tolist()
    except NameError as ne:
        return f'ERROR: {ne}'


def insert_into_sql_table_from_dbf(dbf_file_from: str):
    try:
        sql_table_to = get_sql_table_name_for_dbf(dbf_file_from)
        cfg_field_dict = cfg.get_dict_from_dbf(dbf_file_from)
        conn = connector()  # Initialization connector object.
        dbf = Dbf5(dbf_file_from, codec='1251')  # Initialization Dbf5 object.
        dbf_df = dbf.to_dataframe()  # Create simpledbf DataFrame.
        df = pd.DataFrame(dbf_df)  # Converting simpledbf DF to pandas DF.
        # df = df.fillna('NULL')

        # Renaming fields in DataFrame(DBF) according to SQL table and delete fields that don't exist in config-file.
        for col in df.columns:
            if cfg_field_dict.keys().__contains__(col.lower()):
                df = df.rename(columns={f'{col}': f'{cfg_field_dict.get(col.lower())}'})
            else:
                df.__delitem__(col)

        # Pad ID fields with spaces to 9 chars.
        # Create a list with ID fields.
        id_fields = []
        for field in dbf.fields:
            if field[1] == 'C' and field[2] == 9 and cfg.has_option(dbf_file_from.split('.')[0], field[0]):
                value = cfg_field_dict.get(field[0].lower())
                id_fields.append(value.upper())

        # Appending spaces to each value in the specified column.
        for col in df.columns:
            if col in id_fields:  # Check if fields is ID.
                for v in df[col].values:
                    df = df.replace({v: pad_field_with_spaces(v)})

        sql_table = pd.read_sql_table(sql_table_to, conn)  # , columns=id_fields)
        sql_table_id_columns = [c.upper() for c in sql_table.columns]

        # Writing DataFrame to SQL DB.
        # Check rows count before insert.
        before_ins_rows_count = pd.read_sql_query(f'SELECT COUNT(*) FROM {sql_table_to}', conn).values[0]
        # Inserting DF to SQL.
        for row in df.itertuples(name=None):
            if row[1] in sql_table_id_columns:
                df = df.drop(row[0])
                print(f'Table "{sql_table_to}" already exist key "{row[1]}"!')
        df.to_sql(sql_table_to, conn, if_exists='append', index=False, chunksize=500)
        # Check rows count after insert.
        after_ins_rows_count = pd.read_sql_query(f'SELECT COUNT(*) FROM {sql_table_to}', conn).values[0]
        # Calculating and output inserted rows quantity.
        inserted_rows: int = after_ins_rows_count[0] - before_ins_rows_count[0]
        print(f'{inserted_rows} rows successfully inserted from DBF "{dbf_file_from}" to table "{sql_table_to}".')
    except sqlalchemy.exc.ProgrammingError as pe:
        print(pe)
    except configparser.NoSectionError as nse:
        print(nse)
    except FileNotFoundError as fnf:
        print(fnf)
    # except FileExistsError as fee:
    #     print(f'Configuration file "{config_file}" not found! {fee}')
    except sqlalchemy.exc.IntegrityError as ie:
        print(ie)


def pad_field_with_spaces(field: str) -> str:
    field = field.strip()
    if len(field) > 1 and str(field).endswith('1'):
        return str(field).rjust(7) + '  '
    else:
        return str(field).rjust(6) + '   '


def get_sql_table_name_for_dbf(dbf_file_name: str):
    section_list = re.findall('\d+', dbf_file_name.split('.')[0])
    section = ''.join(section_list)
    if dbf_file_name.startswith('DH'):
        return 'DH_' + cfg.get_setting('Documents', section)
    elif dbf_file_name.startswith('DT'):
        return 'DT_' + cfg.get_setting('Documents', section)
    elif dbf_file_name.startswith('SC'):
        return cfg.get_setting('References', section)
    elif dbf_file_name.startswith('RA'):
        return 'RA_' + cfg.get_setting('Registers', section)
    elif dbf_file_name.startswith('RM'):
        return 'RM_' + cfg.get_setting('Registers', section)
