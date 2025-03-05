import pandas as pd
import numpy as np
from stockquant.market import Market
from stockquant.message import DingTalk
import logging
from datetime import datetime, timedelta
import baostock as bs

class MAStrategy:
    def __init__(self):
        self.market = Market()
        self.ding = DingTalk()
        self.setup_logging()
        # 登录baostock
        bs.login()
        
        # 设置交易标的
        self.security = 'sh.601318'  # 中国平安
        self.cash = 100000  # 初始资金
        self.position = 0   # 持仓数量
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('strategy.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_history_data(self):
        """获取历史数据"""
        try:
            # 获取当前日期
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # 使用baostock获取历史数据
            rs = bs.query_history_k_data_plus(
                self.security,
                "date,close,volume,high,low",
                start_date=start_date,
                end_date=end_date,
                frequency="d",  # 使用日线数据
                adjustflag="3"  # 使用后复权
            )
            
            # 获取数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            # 转换为DataFrame
            df = pd.DataFrame(data_list, columns=['date', 'close', 'volume', 'high', 'low'])
            
            if df is None or len(df) < 5:  # 至少需要5天数据计算均线
                self.logger.error("获取数据失败")
                return None
                    
            # 转换为DataFrame并处理数据
            df = pd.DataFrame(df)
            if 'close' not in df.columns:
                self.logger.error("数据格式不正确")
                return None
                    
            # 确保close列为数值类型
            df['close'] = df['close'].astype(float)
            
            return df
                    
        except Exception as e:
            self.logger.error(f"获取历史数据出错: {str(e)}")
            return None
            
    def calculate_signals(self, df):
        """计算交易信号"""
        try:
            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            
            # 获取最新数据
            current_ma5 = df['MA5'].iloc[-1]
            prev_ma5 = df['MA5'].iloc[-2]
            current_ma10 = df['MA10'].iloc[-1]
            prev_ma10 = df['MA10'].iloc[-2]
            current_price = df['close'].iloc[-1]
            
            # 输出调试信息
            self.logger.info(f"""
当前价格: {current_price:.2f}
5日均线: {current_ma5:.2f} (前值: {prev_ma5:.2f})
10日均线: {current_ma10:.2f} (前值: {prev_ma10:.2f})
""")
            
            # 判断买入信号：5日线上穿10日线
            if current_ma5 > current_ma10 and prev_ma5 < prev_ma10:
                return 'buy', current_price
                
            # 判断卖出信号：5日线下穿10日线
            elif current_ma5 < current_ma10 and prev_ma5 > prev_ma10:
                return 'sell', current_price
                
            return None, current_price
            
        except Exception as e:
            self.logger.error(f"计算交易信号出错: {str(e)}")
            return None, None
                
    def execute_trade(self, signal, price):
        """执行交易"""
        try:
            if signal == 'buy' and self.cash > 0:
                # 计算可买数量（假设每次使用全部现金，实际应该考虑手续费等）
                shares = int(self.cash / price / 100) * 100  # 向下取整到100的倍数
                if shares >= 100:
                    cost = shares * price
                    self.cash -= cost
                    self.position += shares
                    message = f"""
【交易信号】买入提醒
--------------------------------
股票：中国平安({self.security})
价格：{price:.2f}
数量：{shares}股
金额：{cost:.2f}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------"""
                    self.ding.send_message(message)
                    self.logger.info(f"买入 {shares} 股，价格 {price:.2f}")
                    
            elif signal == 'sell' and self.position > 0:
                # 全部卖出
                revenue = self.position * price
                self.cash += revenue
                message = f"""
【交易信号】卖出提醒
--------------------------------
股票：中国平安({self.security})
价格：{price:.2f}
数量：{self.position}股
金额：{revenue:.2f}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------"""
                self.ding.send_message(message)
                self.logger.info(f"卖出 {self.position} 股，价格 {price:.2f}")
                self.position = 0
                
        except Exception as e:
            self.logger.error(f"执行交易出错: {str(e)}")
                
    def run(self):
        """运行策略"""
        self.logger.info("开始运行策略...")
        
        try:
            # 获取历史数据
            df = self.get_history_data()
            if df is None:
                return
                
            # 计算交易信号
            signal, price = self.calculate_signals(df)
            
            # 执行交易
            if signal:
                self.execute_trade(signal, price)
                
            # 输出当前持仓状态
            total_value = self.cash + (self.position * price if price else 0)
            self.logger.info(f"""
当前状态:
现金: {self.cash:.2f}
持仓: {self.position}股
总价值: {total_value:.2f}
--------------------------------""")
            
        except Exception as e:
            self.logger.error(f"策略运行出错: {str(e)}")

if __name__ == "__main__":
    strategy = MAStrategy()
    strategy.run()
