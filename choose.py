from stockquant.market import Market
from stockquant.message import DingTalk
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import os

class StockChooser:
    def __init__(self):
        self.market = Market()
        self.setup_logging()
        
        # 初始化钉钉机器人
        try:
            from stockquant.config import config
            config.loads("docs/config.json")  # 加载配置文件
            self.ding = DingTalk()
            # 发送测试消息
            test_message = """【交易提醒】选股助手连接测试
--------------------------------
选股助手已成功连接！
当前时间：{}
--------------------------------""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            self.ding.send_message(test_message)
            self.logger.info("钉钉机器人连接测试成功！")
        except Exception as e:
            self.logger.error(f"钉钉机器人初始化失败：{str(e)}")
            self.ding = None
        
        # 选股参数
        self.MAX_PRICE = 100.0    # 股价上限
        self.MIN_VOLUME = 100.0   # 最小成交量（万）
        self.UP_PERCENT = 9.8     # 涨幅限制
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('stock_chooser.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_stock_data(self, stock_code):
        """获取单个股票数据"""
        try:
            # 获取实时数据
            price_info = self.market.sina.get_realtime_data(stock_code)
            if not price_info:
                self.logger.error(f"获取股票{stock_code}数据失败")
                return None
            
            # 添加股票代码到数据中
            price_info['code'] = stock_code
                
            # 转换数据类型，添加错误检查
            try:
                price_info['price'] = float(price_info.get('price', 0))
                price_info['volume'] = float(price_info.get('volume', 0))
                price_info['amount'] = float(price_info.get('amount', 0))
                price_info['open'] = float(price_info.get('open', 0))
                price_info['close'] = float(price_info.get('close', 0))
                price_info['high'] = float(price_info.get('high', 0))
                price_info['low'] = float(price_info.get('low', 0))
                
                # 检查是否有name字段，如果没有则使用代码作为名称
                if 'name' not in price_info:
                    price_info['name'] = stock_code
                
                # 检查数据有效性
                if price_info['price'] == 0 or price_info['volume'] == 0:
                    self.logger.error(f"股票{stock_code}数据无效")
                    return None
                
            except (ValueError, TypeError) as e:
                self.logger.error(f"转换股票{stock_code}数据类型时出错: {str(e)}")
                return None
            
            return price_info
            
        except Exception as e:
            self.logger.error(f"处理股票{stock_code}数据时出错: {str(e)}")
            return None
            
    def check_stock_condition(self, price_info):
        """检查股票是否满足条件"""
        try:
            if not price_info or not isinstance(price_info, dict):
                return False
            
            # 检查必要字段是否存在
            required_fields = ['price', 'volume', 'close', 'name', 'code']
            if not all(field in price_info for field in required_fields):
                self.logger.error(f"股票数据缺少必要字段: {price_info.get('code', 'unknown')}")
                return False
                
            # 检查价格条件
            if price_info['price'] > self.MAX_PRICE:
                return False
                
            # 检查成交量条件（转换为万为单位）
            volume_wan = price_info['volume'] / 10000
            if volume_wan < self.MIN_VOLUME:
                return False
                
            # 计算涨幅
            price_change = (price_info['price'] - price_info['close']) / price_info['close'] * 100
            if price_change > self.UP_PERCENT:
                return False
                
            # 记录日志
            self.logger.info(f"""
检查股票 {price_info['name']}({price_info['code']}) 的条件：
当前价格: {price_info['price']:.2f} (限制: {self.MAX_PRICE})
成交量: {volume_wan:.2f}万 (限制: {self.MIN_VOLUME}万)
涨幅: {price_change:.2f}% (限制: {self.UP_PERCENT}%)
结果: 满足条件
""")
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查股票条件时出错: {str(e)}")
            return False
            
    def send_ding_message(self, message):
        """发送钉钉消息"""
        try:
            if self.ding:
                # 确保消息中包含关键词
                if "【交易提醒】" not in message:
                    message = "【交易提醒】\n" + message
                self.ding.send_message(message)
                self.logger.info("钉钉消息发送成功")
            else:
                self.logger.warning("钉钉机器人未初始化，消息未发送")
        except Exception as e:
            self.logger.error(f"发送钉钉消息失败: {str(e)}")

    def format_stock_message(self, matched_stocks):
        """格式化股票信息为钉钉消息"""
        message = f"""【交易提醒】股票选股结果
--------------------------------
交易时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

选股条件:
1. 股票价格上限: {self.MAX_PRICE}元
2. 股票成交量下限: {self.MIN_VOLUME}万
3. 股票涨幅限制: {self.UP_PERCENT}%
--------------------------------
"""
        if matched_stocks:
            message += f"共找到{len(matched_stocks)}只股票：\n"
            for stock in matched_stocks:
                message += f"""
【交易提醒】{stock['name']}({stock['code']})
当前价格: {stock['price']:.2f}元
成交量: {stock['volume']/10000:.2f}万
涨跌幅: {stock['change']:.2f}%
--------------------------------"""
        else:
            message += "【交易提醒】没有找到符合条件的股票"
            
        return message

    def choose_stocks(self, stock_list):
        """批量选股"""
        try:
            if not stock_list:
                self.logger.error("股票列表为空")
                return []
                
            matched_stocks = []
            total_stocks = len(stock_list)
            
            self.logger.info(f"开始处理{total_stocks}只股票...")
            
            for index, stock_code in enumerate(stock_list, 1):
                try:
                    self.logger.info(f"正在处理第{index}/{total_stocks}只股票: {stock_code}")
                    
                    # 获取股票数据
                    price_info = self.get_stock_data(stock_code)
                    if not price_info:
                        continue
                        
                    # 检查是否满足条件
                    if self.check_stock_condition(price_info):
                        matched_stocks.append({
                            'code': stock_code,
                            'name': price_info['name'],
                            'price': price_info['price'],
                            'volume': price_info['volume'],
                            'amount': price_info['amount'],
                            'change': (price_info['price'] - price_info['close']) / price_info['close'] * 100
                        })
                        
                except Exception as e:
                    self.logger.error(f"处理股票 {stock_code} 时出错: {str(e)}")
                    continue
            
            self.logger.info(f"选股完成，共找到{len(matched_stocks)}只符合条件的股票")
            
            # 发送钉钉消息
            message = self.format_stock_message(matched_stocks)
            self.send_ding_message(message)
            
            return matched_stocks
            
        except Exception as e:
            self.logger.error(f"选股过程出错: {str(e)}")
            error_message = f"""【股票选股】执行出错
--------------------------------
错误信息: {str(e)}
发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------"""
            self.send_ding_message(error_message)
            return []

    def get_stock_list(self):
        """获取股票列表"""
        # 沪深300成分股列表（示例）
        stock_list = [
            # 沪市主要成分股
            'sh600000', 'sh600036', 'sh600276', 'sh600309', 'sh600519',
            'sh600887', 'sh601318', 'sh601398', 'sh601668', 'sh601888',
            # 深市主要成分股
            'sz000001', 'sz000333', 'sz000651', 'sz000858', 'sz002594',
            'sz300059', 'sz300122', 'sz300616', 'sz300750', 'sz300760'
        ]
        
        self.logger.info(f"已加载{len(stock_list)}只股票")
        return stock_list

if __name__ == "__main__":
    # 创建选股器实例
    chooser = StockChooser()

    try:
        # 获取股票列表
        stock_list = chooser.get_stock_list()
        print(f"\n开始选股，共{len(stock_list)}只股票...")

        # 执行选股
        matched_stocks = chooser.choose_stocks(stock_list)

        # 查看结果
        print("\n选股结果：")
        if matched_stocks:
            for stock in matched_stocks:
                print(f"\n股票代码：{stock['code']}")
                print(f"股票名称：{stock['name']}")
                print(f"当前价格：{stock['price']:.2f}")
                print(f"成交量：{stock['volume']/10000:.2f}万")
                print(f"涨跌幅：{stock['change']:.2f}%")
                print("-" * 30)
        else:
            print("没有找到符合条件的股票")
            
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        print("请检查网络连接和股票代码是否正确")
