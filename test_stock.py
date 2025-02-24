from stockquant.market import Market
from stockquant.message import DingTalk  # 导入钉钉机器人模块

def get_stock_price():
    print("开始执行获取股票数据...")
    # 创建Market实例
    market = Market()
    print("成功创建 Market 实例")
    # 创建钉钉机器人实例
    ding = DingTalk()
    print("成功创建钉钉机器人实例")
    
    # 获取300616的实时行情
    # 股票代码前需要加上交易所标识：sz(深圳) 或 sh(上海)
    stock_code = "sz300616"  # 威帝股份
    print(f"准备获取股票代码 {stock_code} 的数据...")
    
    try:
        # 使用新浪数据源获取实时数据
        print("正在从新浪获取实时数据...")
        price_info = market.sina.get_realtime_data(stock_code)
        print(f"获取到的原始数据: {price_info}")
        
        if price_info is None:
            error_msg = f"【交易提醒】无法获取股票 {stock_code} 的数据"
            print(error_msg)
            return
            
        # 构建消息内容
        message = f"""【交易提醒】实时数据播报
--------------------------------
股票代码: {stock_code}
股票名称: {price_info['name']}
当前价格: {price_info['price']}
今日开盘价: {price_info['open']}
今日最高价: {price_info['high']}
今日最低价: {price_info['low']}
昨日收盘价: {price_info['close']}
成交量: {price_info['volume']}
成交额: {price_info['amount']}
--------------------------------
"""
        
        # 打印到控制台
        print(message)
        # 尝试发送到钉钉
        print("准备发送消息到钉钉...")
        ding.send_message(message)
        print("钉钉消息发送完成")
        
        # 如果需要K线数据，可以使用 baostock
        # kline_data = market.baostock.get_history_k_data(stock_code)
        # print("K线数据:", kline_data)
        
    except Exception as e:
        error_msg = f"【交易提醒】获取数据出错: {e}"
        print(error_msg)
        import traceback
        print("详细错误信息:")
        print(traceback.format_exc())

if __name__ == "__main__":
    get_stock_price() 