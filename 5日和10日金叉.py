import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# 设置Tushare的token（需要在tushare网站注册获取）
ts.set_token('你的tushare token')
pro = ts.pro_api()

def get_stock_list():
    """获取所有A股股票列表"""
    data = pro.stock_basic(exchange='', list_status='L')
    return data['ts_code'].tolist()

def calculate_ma(stock_code):
    """计算单个股票的移动平均线"""
    try:
        # 获取最近60个交易日的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=100)).strftime('%Y%m%d')

        df = pro.daily(ts_code=stock_code, start_date=start_date, end_date=end_date)
        if df.empty:
            return None

        # 按照日期正序排列
        df = df.sort_values('trade_date')

        # 计算移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()

        return df
    except Exception as e:
        print(f"处理股票 {stock_code} 时出错: {str(e)}")
        return None

def check_golden_cross(df):
    """检查是否满足选股条件"""
    if df is None or len(df) < 20:
        return False

    # 获取最新两天的数据
    last_two_days = df.tail(2)

    if len(last_two_days) < 2:
        return False

    # 检查金叉条件
    yesterday = last_two_days.iloc[0]
    today = last_two_days.iloc[1]

    # 5日线是否上穿10日线
    golden_cross = (yesterday['MA5'] <= yesterday['MA10']) and (today['MA5'] > today['MA10'])

    # 当前价格是否高于20日线
    price_above_ma20 = today['close'] > today['MA20']

    return golden_cross and price_above_ma20

def stock_scanner():
    """主扫描函数"""
    print(f"开始扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 获取所有股票列表
    stock_list = get_stock_list()

    # 存储符合条件的股票
    selected_stocks = []

    # 遍历每只股票
    for stock_code in stock_list:
        try:
            df = calculate_ma(stock_code)
            if df is not None and check_golden_cross(df):
                stock_info = {
                    'code': stock_code,
                    'name': pro.stock_basic(ts_code=stock_code)['name'].iloc[0],
                    'price': df.iloc[-1]['close']
                }
                selected_stocks.append(stock_info)
                print(f"发现符合条件的股票: {stock_info}")
        except Exception as e:
            print(f"处理股票 {stock_code} 时出错: {str(e)}")

        # 添加延时避免频繁请求
        time.sleep(0.1)

    return selected_stocks

def main():
    """主函数"""
    while True:
        try:
            # 在交易时间内运行（9:30-15:00）
            now = datetime.now()
            if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 15:
                print("当前不是交易时间，程序休眠...")
                time.sleep(300)  # 休眠5分钟
                continue

            # 运行扫描
            selected_stocks = stock_scanner()

            # 输出结果
            if selected_stocks:
                print("\n符合条件的股票：")
                for stock in selected_stocks:
                    print(f"股票代码: {stock['code']}, 名称: {stock['name']}, 当前价格: {stock['price']}")
            else:
                print("没有发现符合条件的股票")

            # 等待5分钟后再次扫描
            print("等待5分钟后进行下一次扫描...")
            time.sleep(300)

        except Exception as e:
            print(f"程序运行出错: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()
from dataclasses import dataclass


@dataclass(init=False)
class Tick:
    """ 实时行情数据"""
    symbol: str                             # 股票代码
    name: str                               # 股票名称
    percent: float                          # 涨跌幅度
    updown: float                           # 涨跌点数
    open: float                             # 今日开盘价
    yesterday_close: float                  # 昨日收盘价
    last: float                             # 当前价格
    high: float                             # 今日最高价
    low: float                              # 今日最低价
    bid_price: float                        # 竞买价
    ask_price: float                        # 竞卖价
    transactions: int                       # 成交数量
    turnover: float                         # 成交金额
    bid1_quantity: int                      # 买一数量
    bid1_price: float                       # 买一报价
    bid2_quantity: int                      # 买二数量
    bid2_price: float                       # 买二报价
    bid3_quantity: int                      # 买三数量
    bid3_price: float                       # 买三报价
    bid4_quantity: int                      # 买四数量
    bid4_price: float                       # 买四报价
    bid5_quantity: int                      # 买五数量
    bid5_price: float                       # 买五报价
    ask1_quantity: int                      # 卖一数量
    ask1_price: float                       # 卖一报价
    ask2_quantity: int                      # 卖二数量
    ask2_price: float                       # 卖二报价
    ask3_quantity: int                      # 卖三数量
    ask3_price: float                       # 卖三报价
    ask4_quantity: int                      # 卖四数量
    ask4_price: float                       # 卖四报价
    ask5_quantity: int                      # 卖五数量
    ask5_price: float                       # 卖五报价
    timestamp: str                          # 时间戳