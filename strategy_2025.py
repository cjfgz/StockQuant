import pandas as pd
import numpy as np
import baostock as bs
from stockquant.market import Market
from stockquant.message import DingTalk
import logging
from datetime import datetime, timedelta
import time

class Strategy2025:
    def __init__(self):
        self.market = Market()
        self.ding = DingTalk()
        self.setup_logging()
        
        # 交易标的
        self.security = 'sz.300677'  # 尚品宅配
        
        # 资金控制
        self.initial_capital = 1000000  # 初始资金100万
        self.position = 0  # 当前持仓数量
        self.buy_price = 0  # 买入价格
        
        # 仓位控制
        self.max_position_ratio = 0.8  # 最大仓位80%
        self.min_position_ratio = 0.3  # 初始仓位30%
        self.add_position_ratio = 0.2  # 加仓比例20%
        
        # 技术指标参数
        self.rsi_period = 6  # RSI周期
        self.rsi_buy = 35  # RSI买入阈值
        self.rsi_sell = 80  # RSI卖出阈值
        self.volume_ratio = 1.2  # 放量阈值
        
        # 止盈止损参数
        self.profit_stop = {
            0.08: 0.03,  # 盈利8%时，回撤3%止盈
            0.15: 0.05,  # 盈利15%时，回撤5%止盈
            0.20: 0.08   # 盈利20%时，回撤8%止盈
        }
        self.stop_loss = 0.05  # 止损比例5%
        self.max_hold_days = 20  # 最大持仓天数
        
        # 连接BaoStock
        self.bs = bs.login()
        if self.bs.error_code != '0':
            self.logger.error(f"BaoStock登录失败: {self.bs.error_msg}")
            raise Exception("BaoStock登录失败")
            
        self.holding_days = 0  # 持仓天数
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('strategy_2025.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def __del__(self):
        """析构函数，确保退出时登出BaoStock"""
        try:
            bs.logout()
        except:
            pass
            
    def get_real_time_data(self):
        """获取实时数据"""
        try:
            # 使用新浪数据源获取实时数据
            price_info = self.market.sina.get_realtime_data(self.security.replace('sz.', 'sz'))
            if not price_info:
                return None
            return price_info
        except Exception as e:
            self.logger.error(f"获取实时数据出错: {str(e)}")
            return None
            
    def get_history_data(self, days=30):
        """获取历史数据"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                self.security,
                "date,close,volume,high,low,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            df = pd.DataFrame(data_list, columns=['date', 'close', 'volume', 'high', 'low', 'amount'])
            df[['close', 'volume', 'high', 'low', 'amount']] = df[['close', 'volume', 'high', 'low', 'amount']].apply(pd.to_numeric)
            return df
            
        except Exception as e:
            self.logger.error(f"获取历史数据出错: {str(e)}")
            return None
            
    def calculate_indicators(self, df):
        """计算技术指标"""
        try:
            # 计算移动平均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            # 计算RSI
            df['RSI'] = df.ta.rsi(close='close', length=self.rsi_period)
            
            # 计算MACD
            macd = df.ta.macd(close='close')
            df['MACD'] = macd['MACD_12_26_9']
            df['SIGNAL'] = macd['MACDs_12_26_9']
            
            # 计算KDJ
            stoch = df.ta.stoch(high='high', low='low', close='close')
            df['K'] = stoch['STOCHk_14_3_3']
            df['D'] = stoch['STOCHd_14_3_3']
            
            # 计算成交量变化
            df['VOL_MA5'] = df['volume'].rolling(window=5).mean()
            df['VOL_RATIO'] = df['volume'] / df['VOL_MA5']
            
            return df
            
        except Exception as e:
            self.logger.error(f"计算技术指标出错: {str(e)}")
            return None
            
    def check_buy_signals(self, df):
        """检查买入信号"""
        try:
            if len(df) < 2:
                return False
                
            current = df.iloc[-1]
            prev = df.iloc[-2]
            
            signals = []
            
            # 1. RSI低于买入阈值
            if current['RSI'] < self.rsi_buy:
                signals.append("RSI超卖")
            
            # 2. 5日均线上穿10日均线
            if current['MA5'] > current['MA10'] and prev['MA5'] <= prev['MA10']:
                signals.append("均线金叉")
            
            # 3. MACD金叉
            if current['MACD'] > current['SIGNAL'] and prev['MACD'] <= prev['SIGNAL']:
                signals.append("MACD金叉")
            
            # 4. 成交量放大
            if current['VOL_RATIO'] > self.volume_ratio:
                signals.append("成交放量")
            
            # 5. KDJ金叉
            if current['K'] > current['D'] and prev['K'] <= prev['D']:
                signals.append("KDJ金叉")
            
            # 需要至少3个信号同时满足
            if len(signals) >= 3:
                return signals
            return []
            
        except Exception as e:
            self.logger.error(f"检查买入信号出错: {str(e)}")
            return []
            
    def check_sell_signals(self, df, buy_price):
        """检查卖出信号"""
        try:
            if len(df) < 2:
                return False
                
            current = df.iloc[-1]
            prev = df.iloc[-2]
            
            signals = []
            
            # 计算收益率
            profit_ratio = (current['close'] - buy_price) / buy_price
            
            # 1. 止损
            if current['close'] < buy_price * (1 - self.stop_loss):
                signals.append(f"止损: 亏损达到{self.stop_loss*100}%")
            
            # 2. 移动止盈
            for target, stop in self.profit_stop.items():
                if profit_ratio >= target:
                    if current['close'] < current['high'] * (1 - stop):
                        signals.append(f"移动止盈: 盈利{target*100}%后回撤{stop*100}%")
            
            # 3. RSI超买
            if current['RSI'] > self.rsi_sell:
                signals.append("RSI超买")
            
            # 4. MACD死叉且有盈利
            if current['MACD'] < current['SIGNAL'] and prev['MACD'] >= prev['SIGNAL'] and profit_ratio > 0:
                signals.append("MACD死叉")
            
            # 5. 均线死叉且有盈利
            if current['MA5'] < current['MA10'] and prev['MA5'] >= prev['MA10'] and profit_ratio > 0:
                signals.append("均线死叉")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"检查卖出信号出错: {str(e)}")
            return []
            
    def send_signal_message(self, signal_type, signals, price_info, position_info=""):
        """发送信号消息到钉钉"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if signal_type == "BUY":
                message = f"""
【买入信号提醒】
--------------------------------
股票：{price_info['name']}({self.security})
当前价格：{price_info['price']}
触发信号：{'、'.join(signals)}
建议操作：买入
{position_info}
--------------------------------
时间：{current_time}
"""
            else:
                message = f"""
【卖出信号提醒】
--------------------------------
股票：{price_info['name']}({self.security})
当前价格：{price_info['price']}
触发信号：{'、'.join(signals)}
建议操作：卖出
{position_info}
--------------------------------
时间：{current_time}
"""
            
            self.ding.send_message(message)
            self.logger.info(f"已发送{signal_type}信号到钉钉")
            
        except Exception as e:
            self.logger.error(f"发送钉钉消息出错: {str(e)}")
            
    def run_strategy(self):
        """运行策略"""
        self.logger.info("开始运行2025年策略...")
        
        while True:
            try:
                # 获取当前时间
                now = datetime.now()
                current_time = now.time()
                
                # 检查是否在交易时间
                if (current_time < datetime.strptime("09:30:00", "%H:%M:%S").time() or 
                    current_time > datetime.strptime("15:00:00", "%H:%M:%S").time()):
                    time.sleep(60)  # 非交易时间休眠1分钟
                    continue
                
                # 获取实时数据
                price_info = self.get_real_time_data()
                if not price_info:
                    time.sleep(10)
                    continue
                
                # 获取历史数据
                df = self.get_history_data()
                if df is None:
                    time.sleep(10)
                    continue
                
                # 计算指标
                df = self.calculate_indicators(df)
                if df is None:
                    time.sleep(10)
                    continue
                
                # 检查买入信号
                if self.position == 0:
                    buy_signals = self.check_buy_signals(df)
                    if buy_signals:
                        # 计算建议买入数量
                        available_amount = self.initial_capital * self.min_position_ratio
                        suggested_shares = int(available_amount / float(price_info['price']) / 100) * 100
                        position_info = f"""
建议买入：{suggested_shares}股
预计资金：{suggested_shares * float(price_info['price']):,.2f}元
仓位比例：{self.min_position_ratio*100}%"""
                        
                        self.send_signal_message("BUY", buy_signals, price_info, position_info)
                
                # 检查卖出信号
                elif self.position > 0:
                    self.holding_days += 1
                    sell_signals = self.check_sell_signals(df, self.buy_price)
                    
                    # 检查是否需要强制平仓
                    if self.holding_days >= self.max_hold_days:
                        sell_signals.append(f"持仓达到{self.max_hold_days}天，强制平仓")
                    
                    if sell_signals:
                        profit_ratio = (float(price_info['price']) - self.buy_price) / self.buy_price * 100
                        position_info = f"""
持仓数量：{self.position}股
持仓天数：{self.holding_days}天
当前收益：{profit_ratio:.2f}%"""
                        
                        self.send_signal_message("SELL", sell_signals, price_info, position_info)
                
                # 休眠一段时间
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                self.logger.error(f"策略运行出错: {str(e)}")
                time.sleep(60)

if __name__ == "__main__":
    strategy = Strategy2025()
    strategy.run_strategy() 