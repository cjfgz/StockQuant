import baostock as bs
import pandas as pd
import matplotlib.pyplot as plt
import yhzq_api  # 假设银河证券API库名为yhzq_api

# 登录baostock
bs.login()

# 获取历史数据
def fetch_data(stock_code, start_date, end_date):
    rs = bs.query_history_k_data_plus(stock_code,
        "date,code,open,high,low,close,volume",
        start_date=start_date, end_date=end_date,
        frequency="d", adjustflag="3")
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    data = pd.DataFrame(data_list, columns=rs.fields)
    return data

# 策略开发
def apply_moving_average_strategy(data):
    data['close'] = pd.to_numeric(data['close'], errors='coerce')  # 确保数据为数值类型
    data['MA5'] = data['close'].rolling(window=5).mean()
    data['MA10'] = data['close'].rolling(window=10).mean()
    data['Signal'] = 0
    data.loc[data['MA5'] > data['MA10'], 'Signal'] = 1  # 使用 loc 进行赋值
    return data

# 回测
def backtest(data):
    data['Position'] = data['Signal'].shift()
    data['Daily_Return'] = data['close'].pct_change()
    data['Strategy_Return'] = data['Position'] * data['Daily_Return']
    cumulative_return = (1 + data['Strategy_Return']).cumprod() - 1
    return cumulative_return

# 执行交易
def execute_trade(signal):
    if signal == 1:
        print("Buy Signal")
        # 执行买入操作
    elif signal == 0:
        print("Sell Signal")
        # 执行卖出操作

# 绘制带有买卖信号的图表
def plot_signals(data):
    plt.figure(figsize=(14, 7))
    plt.plot(data['date'], data['close'], label='Close Price', alpha=0.5)
    plt.plot(data['date'], data['MA5'], label='MA5', alpha=0.75)
    plt.plot(data['date'], data['MA10'], label='MA10', alpha=0.75)

    # 标记买入信号
    buy_signals = data[data['Signal'] == 1]
    plt.scatter(buy_signals['date'], buy_signals['close'], label='Buy Signal', marker='^', color='g', alpha=1)

    # 标记卖出信号
    sell_signals = data[data['Signal'] == 0]
    plt.scatter(sell_signals['date'], sell_signals['close'], label='Sell Signal', marker='v', color='r', alpha=1)

    plt.title('Stock Price with Buy/Sell Signals')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()  # 确保调用 plt.show()

# 主程序
def main():
    stock_code = "sz.300573"
    start_date = "2022-01-01"
    end_date = "2022-12-31"
    
    # 获取数据
    data = fetch_data(stock_code, start_date, end_date)
    
    # 应用策略
    data = apply_moving_average_strategy(data)
    
    # 回测
    cumulative_return = backtest(data)
    print("Cumulative Return:", cumulative_return.iloc[-1])
    
    # 绘制信号图表
    plot_signals(data)
    
    # 执行交易
    for index, row in data.iterrows():
        execute_trade(row['Signal'])

# 设置API密钥
API_KEY = 'your_api_key'
API_SECRET = 'your_api_secret'

# 创建API连接
api = yhzq_api.connect(API_KEY, API_SECRET)

# 定义交易策略
def trading_strategy():
    # 获取账户信息
    account_info = api.get_account_info()
    print(f"Account balance: {account_info['balance']}")

    # 获取当前持仓
    positions = api.get_positions()
    for position in positions:
        print(f"Current position: {position['symbol']} - {position['quantity']}")

    # 获取市场数据
    market_data = api.get_market_data('600000')  # 以股票代码600000为例

    # 简单策略：如果今天的收盘价高于前一天，则买入
    if market_data['close'] > market_data['previous_close']:
        api.place_order(
            symbol='600000',
            quantity=100,
            order_type='buy',
            price_type='market'
        )
        print("Buy order submitted for 600000")

# 执行策略
trading_strategy()

if __name__ == "__main__":
    main()
    plt.show()  # 在脚本末尾再次调用 plt.show()

# 登出baostock
bs.logout() 