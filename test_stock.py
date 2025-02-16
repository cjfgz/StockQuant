from stockquant.market import Market

def get_stock_price():
    # 创建Market实例
    market = Market()
    
    # 获取300616的实时行情
    # 股票代码前需要加上交易所标识：sz(深圳) 或 sh(上海)
    stock_code = "sz300616"  # 威帝股份
    
    try:
        # 使用新浪数据源获取实时数据
        price_info = market.sina.get_realtime_data(stock_code)
        
        if price_info is None:
            print(f"无法获取股票 {stock_code} 的数据")
            return
            
        print(f"股票代码: {stock_code}")
        print(f"股票名称: {price_info['name']}")
        print(f"当前价格: {price_info['price']}")
        print(f"今日开盘价: {price_info['open']}")
        print(f"今日最高价: {price_info['high']}")
        print(f"今日最低价: {price_info['low']}")
        print(f"昨日收盘价: {price_info['close']}")
        print(f"成交量: {price_info['volume']}")
        print(f"成交额: {price_info['amount']}")
        
        # 如果需要K线数据，可以使用 baostock
        # kline_data = market.baostock.get_history_k_data(stock_code)
        # print("K线数据:", kline_data)
        
    except Exception as e:
        print(f"获取股票数据出错: {e}")

if __name__ == "__main__":
    get_stock_price() 