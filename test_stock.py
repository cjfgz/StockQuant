from stockquant.market import Market
from stockquant.message import DingTalk  # 导入钉钉机器人模块

def get_stock_price():
    # 创建Market实例
    market = Market()
    # 创建钉钉机器人实例
    ding = DingTalk()
    
    # 获取300616的实时行情
    # 股票代码前需要加上交易所标识：sz(深圳) 或 sh(上海)
    stock_code = "sz300616"  # 威帝股份
    
    try:
        # 使用新浪数据源获取实时数据
        price_info = market.sina.get_realtime_data(stock_code)
        
        if price_info is None:
            error_msg = f"【小火箭】无法获取股票 {stock_code} 的数据"
            print(error_msg)
            return
            
        # 构建消息内容
        message = f"""【小火箭】实时数据播报
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
        ding.send_message(message)
        
        # 如果需要K线数据，可以使用 baostock
        # kline_data = market.baostock.get_history_k_data(stock_code)
        # print("K线数据:", kline_data)
        
    except Exception as e:
        error_msg = f"【小火箭】获取数据出错: {e}"
        print(error_msg)

if __name__ == "__main__":
    get_stock_price() 