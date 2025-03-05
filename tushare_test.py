import tushare as ts
import pandas as pd
from datetime import datetime, timedelta

def test_tushare():
    try:
        # 初始化pro接口
        ts.set_token('b097f86043c6f0860d20de8978e988db375113f4250c6f263886d1a3')  # 这里需要替换为您的token
        pro = ts.pro_api()
        
        print("正在测试Tushare连接...")
        
        # 获取当前日期
        today = datetime.now().strftime('%Y%m%d')
        
        # 获取上证指数信息
        df = pro.index_daily(ts_code='000001.SH', 
                           start_date=(datetime.now() - timedelta(days=10)).strftime('%Y%m%d'),
                           end_date=today)
        
        print("\n最近的上证指数数据：")
        print(df.head())
        
        # 获取个股数据
        stock_df = pro.daily(ts_code='300616.SZ',
                           start_date=(datetime.now() - timedelta(days=10)).strftime('%Y%m%d'),
                           end_date=today)
        
        print("\n最近的个股数据：")
        print(stock_df.head())
        
        print("\nTushare连接测试成功！")
        
    except Exception as e:
        print(f"测试失败，错误信息：{str(e)}")
        print("\n请确保：")
        print("1. 已经注册Tushare账号")
        print("2. 已经正确设置token")
        print("3. 网络连接正常")

if __name__ == "__main__":
    test_tushare() 