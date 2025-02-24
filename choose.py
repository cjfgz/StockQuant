from stockquant.market import Market
from stockquant.message import DingTalk
from stockquant.utils.logger import logger
from datetime import datetime
import os

class StockChooser:
    def __init__(self):
        self.market = Market()
        self.ding = DingTalk()
        
        # 调整选股参数设置
        self.MAX_PRICE = 100     # 提高股价上限到100元
        self.MIN_VOLUME = 100    # 降低最小成交量到100万
        self.UP_PERCENT = 9.8    # 扩大涨幅范围到9.8%

    def get_stock_data(self, stock_code):
        """获取单个股票数据"""
        try:
            # 使用新浪数据源获取实时数据
            price_info = self.market.sina.get_realtime_data(stock_code)
            if price_info:
                return {
                    'code': stock_code,
                    'name': price_info['name'],
                    'price': float(price_info['price']),
                    'close': float(price_info['close']),
                    'volume': float(price_info['volume']),
                    'amount': float(price_info['amount'])
                }
            return None
        except Exception as e:
            logger.error(f"获取股票{stock_code}数据失败: {str(e)}")
            return None

    def check_stock_condition(self, price_info):
        """选股条件判断"""
        try:
            if not price_info:
                return False
                
            # 计算涨跌幅
            price_change = (price_info['price'] - price_info['close']) / price_info['close'] * 100
            
            # 打印调试信息
            print(f"\n检查股票 {price_info['name']}({price_info['code']}) 的条件：")
            print(f"价格: {price_info['price']}元 (限制: <= {self.MAX_PRICE}元)")
            print(f"成交量: {price_info['volume']/10000:.2f}万 (限制: >= {self.MIN_VOLUME}万)")
            print(f"涨跌幅: {price_change:.2f}% (限制: 0~{self.UP_PERCENT}%)")
            
            # 选股条件：
            # 1. 股价低于设定价格
            # 2. 成交量大于设定值
            # 3. 涨幅在设定范围内
            if (price_info['price'] <= self.MAX_PRICE and 
                price_info['volume'] >= self.MIN_VOLUME * 10000 and 
                0 <= price_change <= self.UP_PERCENT):
                print("符合条件！")
                return True
            print("不符合条件")
            return False
            
        except Exception as e:
            logger.error(f"选股条件判断出错: {str(e)}")
            return False

    def run(self):
        """运行选股程序"""
        try:
            # 获取所有股票列表
            stock_list = []
            # 添加更多测试用的股票
            test_stocks = [
                'sz300616',  # 尚品宅配
                'sh600000',  # 浦发银行
                'sh601318',  # 中国平安
                'sz000001',  # 平安银行
                'sh600519',  # 贵州茅台
                'sz000858',  # 五粮液
                'sh601888',  # 中国中免
                'sz002594',  # 比亚迪
                'sz300750',  # 宁德时代
                'sh600036'   # 招商银行
            ]
            stock_list.extend(test_stocks)
            
            if not stock_list:
                error_msg = "【交易提醒】获取股票列表失败"
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
                message = f"""【交易提醒】选股结果播报
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
                message = f"""【交易提醒】选股结果播报
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
            error_msg = f"【交易提醒】选股程序运行出错: {str(e)}"
            logger.error(error_msg)
            self.ding.send_message(error_msg)

if __name__ == '__main__':
    chooser = StockChooser()
    chooser.run()