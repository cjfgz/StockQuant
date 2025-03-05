import pandas as pd
import numpy as np
import tushare as ts
import json
import time

# 初始化Tushare Pro
def init_tushare():
    try:
        with open('docs/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            token = config.get('TUSHARE', {}).get('token')
            if not token:
                raise ValueError("配置文件中未找到token")
        ts.set_token(token)
        return ts.pro_api()
    except Exception as e:
        print(f"初始化Tushare失败: {str(e)}")
        raise

def golden_cross_strategy(pro, stock_code, start_date, end_date):
    """
    判断股票是否出现5日均线和10日均线的金叉

    参数:
    pro: tushare pro接口
    stock_code: 股票代码
    start_date: 开始日期
    end_date: 结束日期

    返回:
    golden_cross_dates: 出现金叉的日期列表
    """

    # 获取股票数据
    try:
        # 转换股票代码格式
        if stock_code.startswith('6'):
            ts_code = f"{stock_code}.SH"
        else:
            ts_code = f"{stock_code}.SZ"
            
        print(f"正在获取股票 {ts_code} 的数据...")
        
        # 使用Pro接口获取数据，添加重试机制
        retry_count = 3
        for i in range(retry_count):
            try:
                df = pro.daily(ts_code=ts_code, 
                              start_date=start_date.replace('-', ''),
                              end_date=end_date.replace('-', ''))
                break
            except Exception as e:
                print(f"获取数据失败，尝试第 {i+1}/{retry_count} 次重试: {str(e)}")
                if i == retry_count - 1:  # 最后一次尝试
                    raise
                time.sleep(2)  # 等待更长时间再重试
        
        if df is None or df.empty:
            print(f"无法获取股票 {stock_code} 的数据")
            return []
            
        print(f"成功获取 {ts_code} 数据，共 {len(df)} 条记录")
            
        # 按日期排序（从旧到新）
        df = df.sort_values('trade_date')
        
        # 计算5日和10日移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()

        # 计算金叉条件
        # 今天5日均线在10日均线上方，昨天5日均线在10日均线下方
        df['golden_cross'] = (df['MA5'] > df['MA10']) & (df['MA5'].shift(1) <= df['MA10'].shift(1))

        # 获取金叉日期
        golden_cross_dates = df[df['golden_cross']]['trade_date'].tolist()
        
        # 添加延时避免频率限制
        time.sleep(0.5)

        return golden_cross_dates

    except Exception as e:
        print(f"处理股票 {stock_code} 时发生错误: {str(e)}")
        return []

def scan_stocks(pro, stock_list, start_date, end_date):
    """
    扫描多个股票，找出所有出现金叉的股票

    参数:
    pro: tushare pro接口
    stock_list: 股票代码列表
    start_date: 开始日期
    end_date: 结束日期
    """

    results = {}

    for stock in stock_list:
        golden_cross_dates = golden_cross_strategy(pro, stock, start_date, end_date)

        if golden_cross_dates:
            results[stock] = golden_cross_dates
            print(f"股票 {stock} 在以下日期出现金叉: {golden_cross_dates}")

    return results

# 使用示例
if __name__ == "__main__":
    # 初始化Tushare Pro
    pro = init_tushare()
    
    # 示例股票列表
    stock_list = ['000001', '600000', '600036']  # 可以添加更多股票代码
    start_date = '2023-01-01'
    end_date = '2023-12-31'

    # 执行选股
    results = scan_stocks(pro, stock_list, start_date, end_date)
