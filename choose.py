from stockquant.market import Market
from stockquant.message import DingTalk
from stockquant.utils.logger import logger
from datetime import datetime, timedelta


class StockChooser:
    def __init__(self):
        self.market = Market()
        self.ding = DingTalk()
        
        # 选股参数设置
        self.MAX_PRICE = 30     # 股价上限
        self.MIN_VOLUME = 1000  # 最小成交量(万)
        self.UP_PERCENT = 5     # 涨幅限制(%)

    def get_stock_data(self, stock_code):
        """获取单个股票数据"""
        try:
            # 使用新浪数据源获取实时数据
            return self.market.sina.get_realtime_data(stock_code)
        except Exception as e:
            logger.error(f"获取股票{stock_code}数据失败: {str(e)}")
            return None

    def check_stock_condition(self, price_info):
        """
        选股条件判断
        :param price_info: 股票数据
        :return: True 满足条件，False 不满足条件
        """
        try:
            if not price_info:
                return False
                
            # 计算涨跌幅
            price_change = (price_info['price'] - price_info['close']) / price_info['close'] * 100
            
            # 选股条件：
            # 1. 股价低于设定价格
            # 2. 成交量大于设定值
            # 3. 涨幅在设定范围内
            if (price_info['price'] <= self.MAX_PRICE and 
                price_info['volume'] >= self.MIN_VOLUME * 10000 and 
                0 <= price_change <= self.UP_PERCENT):
                return True
            return False
            
        except Exception as e:
            logger.error(f"选股条件判断出错: {str(e)}")
            return False

    def run(self):
        """运行选股程序"""
        try:
            # 获取所有股票列表
            stock_list = self.market.stocks_list()
            if not stock_list:
                error_msg = "【小火箭】获取股票列表失败"
                logger.error(error_msg)
                self.ding.send_message(error_msg)
                return

            # 符合条件的股票列表
            matched_stocks = []
            
            # 遍历股票列表
            for stock in stock_list:
                try:
                    # 获取股票数据
                    price_info = self.get_stock_data(stock)
                    if not price_info:
                        continue

                    # 判断是否符合条件
                    if self.check_stock_condition(price_info):
                        matched_stocks.append({
                            'code': stock,
                            'name': price_info['name'],
                            'price': price_info['price'],
                            'volume': price_info['volume'],
                            'amount': price_info['amount']
                        })

                except Exception as e:
                    logger.error(f"处理股票 {stock} 时出错: {str(e)}")
                    continue

            # 发送选股结果
            if matched_stocks:
                message = f"""【小火箭】选股结果播报
--------------------------------
选股时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
选股条件:
1. 股价 <= {self.MAX_PRICE}元
2. 成交量 >= {self.MIN_VOLUME}万
3. 涨幅 0~{self.UP_PERCENT}%
--------------------------------
符合条件的股票:
"""
                for stock in matched_stocks:
                    message += f"""
{stock['name']}({stock['code']})
当前价格: {stock['price']}元
成交量: {stock['volume']/10000:.2f}万
成交额: {stock['amount']/10000:.2f}万
--------------------------------"""
                
                print(message)
                self.ding.send_message(message)
            else:
                message = f"""【小火箭】选股结果播报
--------------------------------
当前没有符合条件的股票
选股条件:
1. 股价 <= {self.MAX_PRICE}元
2. 成交量 >= {self.MIN_VOLUME}万
3. 涨幅 0~{self.UP_PERCENT}%
--------------------------------"""
                print(message)
                self.ding.send_message(message)

        except Exception as e:
            error_msg = f"【小火箭】选股程序运行出错: {str(e)}"
            logger.error(error_msg)
            self.ding.send_message(error_msg)


if __name__ == '__main__':
    chooser = StockChooser()
    chooser.run()
