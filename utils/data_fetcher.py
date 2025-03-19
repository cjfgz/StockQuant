import baostock as bs
import pandas as pd

def fetch_data(stock_code, start_date, end_date):
    bs.login()
    rs = bs.query_history_k_data_plus(stock_code,
        "date,code,open,high,low,close,volume",
        start_date=start_date, end_date=end_date,
        frequency="d", adjustflag="3")
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)
    bs.logout()
    return result 