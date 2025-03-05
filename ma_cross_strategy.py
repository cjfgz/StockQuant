from stockquant.market import Market
from stockquant.message import DingTalk
import tushare as ts
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import os

class MACrossScreener:
    def __init__(self):
        self.market = Market()
        
        # 设置tushare token
        ts.set_token('b097f86043c6f0860d20de8978e988db375113f4250c6f263886d1a3')
        self.pro = ts.pro_api()
        
        # 钉钉机器人配置
        try:
            # 创建配置对象
            from stockquant.config import config
            config.loads("docs/config.json")  # 加载配置文件
            self.ding = DingTalk()
            # 发送测试消息
            test_message = """【股票提醒】连接测试
--------------------------------
股票提醒助手已成功连接！
当前时间：{}
--------------------------------""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            self.ding.send_message(test_message)
            print("钉钉机器人连接测试成功！")
        except Exception as e:
            print(f"钉钉机器人连接失败：{str(e)}")
            print("请检查token是否正确")
            
        self.setup_logging()
        
        # 测试股票池
        self.test_stocks = {
            'sz300616': '300616.SZ',  # 尚品宅配
            'sh600000': '600000.SH',  # 浦发银行
            'sh601318': '601318.SH',  # 中国平安
            'sz000001': '000001.SZ',  # 平安银行
            'sh600519': '600519.SH',  # 贵州茅台
            'sz000858': '000858.SZ',  # 五粮液
            'sh601888': '601888.SH',  # 中国中免
            'sz002594': '002594.SZ',  # 比亚迪
            'sz300750': '300750.SZ',  # 宁德时代
            'sh600036': '600036.SH'   # 招商银行
        }
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ma_cross_screen.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_ma_data(self, stock_code):
        """获取均线数据"""
        try:
            # 获取实时数据
            price_info = self.market.sina.get_realtime_data(stock_code)
            if not price_info:
                return None
                
            # 获取历史K线数据（使用tushare）
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            # 转换为tushare格式的股票代码
            ts_code = self.test_stocks[stock_code]
            
            # 获取日线数据
            df = self.pro.daily(ts_code=ts_code, 
                              start_date=start_date,
                              end_date=end_date)
            
            if df is None or len(df) < 20:
                return None
                
            # 按照日期正序排列
            df = df.sort_values('trade_date')
            
            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            # 获取最新数据
            current_price = float(price_info['price'])
            latest_data = {
                'code': stock_code,
                'name': price_info['name'],
                'price': current_price,
                'volume': float(price_info['volume']),
                'amount': float(price_info['amount']),
                'MA5': df['MA5'].iloc[-1],
                'MA10': df['MA10'].iloc[-1],
                'MA20': df['MA20'].iloc[-1],
                'prev_MA5': df['MA5'].iloc[-2],
                'prev_MA10': df['MA10'].iloc[-2]
            }
            
            return latest_data
            
        except Exception as e:
            self.logger.error(f"获取股票{stock_code}数据失败: {str(e)}")
            return None

    def check_ma_signal(self, data):
        """检查均线金叉信号"""
        try:
            if not data:
                return False
                
            # 计算指标
            golden_cross = (data['prev_MA5'] <= data['prev_MA10'] and 
                          data['MA5'] > data['MA10'])
            ma20_above_price = data['MA20'] > data['price']
            
            # 记录日志
            self.logger.info(f"\n检查股票 {data['name']}({data['code']}) 的均线信号：")
            self.logger.info(f"当前价格: {data['price']:.2f}")
            self.logger.info(f"5日均线: {data['MA5']:.2f}")
            self.logger.info(f"10日均线: {data['MA10']:.2f}")
            self.logger.info(f"20日均线: {data['MA20']:.2f}")
            self.logger.info(f"是否金叉: {'是' if golden_cross else '否'}")
            self.logger.info(f"20日线是否高于当前价: {'是' if ma20_above_price else '否'}")
            
            return golden_cross and ma20_above_price
            
        except Exception as e:
            self.logger.error(f"检查均线信号出错: {str(e)}")
            return False

    def screen_stocks(self):
        """执行选股"""
        try:
            self.logger.info("开始执行均线选股...")
            matched_stocks = []
            
            for stock_code in self.test_stocks:
                try:
                    # 获取股票数据
                    stock_data = self.get_ma_data(stock_code)
                    if not stock_data:
                        continue
                        
                    # 检查均线信号
                    if self.check_ma_signal(stock_data):
                        matched_stocks.append({
                            'code': stock_data['code'],
                            'name': stock_data['name'],
                            'price': stock_data['price'],
                            'MA5': stock_data['MA5'],
                            'MA10': stock_data['MA10'],
                            'MA20': stock_data['MA20']
                        })
                        self.logger.info(f"发现符合条件的股票：{stock_data['name']}({stock_code})")
                        
                except Exception as e:
                    self.logger.error(f"处理股票 {stock_code} 时出错: {str(e)}")
                    continue
            
            # 构建推送消息
            if matched_stocks:
                message = f"""【股票提醒】均线金叉选股结果
--------------------------------
选股时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
选股条件:
1. 5日均线上穿10日均线（金叉）
2. 20日均线高于当前价格
--------------------------------
符合条件的股票:
"""
                for stock in matched_stocks:
                    message += f"""
{stock['name']}({stock['code']})
当前价格: {stock['price']:.2f}
5日均线: {stock['MA5']:.2f}
10日均线: {stock['MA10']:.2f}
20日均线: {stock['MA20']:.2f}
--------------------------------"""
                
                # 推送到钉钉
                self.ding.send_message(message)
                self.logger.info("选股结果已推送到钉钉")
            else:
                message = """【股票提醒】均线金叉选股结果
--------------------------------
当前没有符合条件的股票
选股条件:
1. 5日均线上穿10日均线（金叉）
2. 20日均线高于当前价格
--------------------------------"""
                self.ding.send_message(message)
                self.logger.info("没有找到符合条件的股票，已推送消息")
                
            return matched_stocks
            
        except Exception as e:
            error_msg = f"选股程序运行出错: {str(e)}"
            self.logger.error(error_msg)
            self.ding.send_message(f"【股票提醒】错误提醒：{error_msg}")
            return []

if __name__ == "__main__":
    screener = MACrossScreener()
    screener.screen_stocks() 