from interface import MainFrame
import wx, wx.grid as grd
from sql import load_into_sql_table_from_dbf, fill_field_with_spaces
import keyring
from ObjectListView import ObjectListView, ColumnDefn

DBF = 'RA7683.DBF'


if __name__ == '__main__':
    app = wx.App()

    frame = MainFrame(None)
    frame.Show()

    app.MainLoop()
    # load_into_sql_table_from_dbf(DBF)
