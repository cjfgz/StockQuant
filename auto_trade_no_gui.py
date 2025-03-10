import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time
import os
import sys

class AutoTrader:
    def __init__(self):
        # 初始化日志
        self.setup_logging()
        
        # 登录baostock
        self.bs = bs
        self.login_result = self.bs.login()
        if self.login_result.error_code == '0':
            self.logger.info("baostock登录成功")
        else:
            self.logger.error(f"baostock登录失败: {self.login_result.error_msg}")
            
        # 策略参数
        self.security = "sz.300677"  # 股票代码
        self.short_window = 8        # 短期均线
        self.long_window = 21        # 长期均线
        self.rsi_period = 14        # RSI周期
        self.rsi_buy = 30           # RSI买入阈值
        self.rsi_sell = 75          # RSI卖出阈值
        self.volume_ratio = 1.2     # 成交量放大倍数
        self.stop_loss = 0.04       # 止损比例
        self.take_profit = 0.15     # 止盈比例
        self.trailing_stop = 0.08   # 追踪止损比例
        
        # 账户状态
        self.cash = 100000          # 初始资金
        self.position = 0           # 持仓数量
        self.buy_price = 0          # 买入价格
        self.highest_price = 0      # 持仓期间最高价格
        
        # 模拟交易模式
        self.simulation_mode = True
        
    def __del__(self):
        """析构函数，确保退出时登出"""
        try:
            self.bs.logout()
            self.logger.info("baostock已登出")
        except:
            pass
            
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('auto_trade.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_stock_data(self):
        """获取历史数据"""
        try:
            # 获取当前日期
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
            
            # 获取K线数据
            rs = bs.query_history_k_data_plus(
                self.security,
                "date,code,open,high,low,close,volume,amount,turn,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != '0':
                self.logger.error(f"获取历史数据失败: {rs.error_msg}")
                return None
                
            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            if not data_list:
                self.logger.error("未获取到历史数据")
                return None
                
            df = pd.DataFrame(data_list, columns=['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg'])
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']:
                df[col] = df[col].astype(float)
            
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
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            
            # 计算成交量均线
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma10'] = df['volume'].rolling(window=10).mean()
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 计算MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']
            
            # 计算布林带
            df['BB_Middle'] = df['close'].rolling(window=20).mean()
            df['BB_Std'] = df['close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
            df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
            
            # 计算KDJ
            low_min = df['low'].rolling(window=9).min()
            high_max = df['high'].rolling(window=9).max()
            df['RSV'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
            df['K'] = df['RSV'].ewm(com=2).mean()
            df['D'] = df['K'].ewm(com=2).mean()
            df['J'] = 3 * df['K'] - 2 * df['D']
            
            # 计算ATR
            df['TR'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['ATR'] = df['TR'].rolling(window=14).mean()
            
            # 计算趋势强度指标
            df['ADX'] = 100 * abs(df['MA5'] - df['MA20']) / df['MA20']
            
            return df
            
        except Exception as e:
            self.logger.error(f"计算信号出错: {str(e)}")
            return None
            
    def check_signals(self, df):
        """检查交易信号"""
        try:
            if len(df) < 2:
                return None
                
            current = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 输出当前状态
            self.logger.info(f"当前价格: {current['close']}")
            self.logger.info(f"5日均线: {current['MA5']:.2f} (前值: {prev['MA5']:.2f})")
            self.logger.info(f"10日均线: {current['MA10']:.2f} (前值: {prev['MA10']:.2f})")
            self.logger.info(f"20日均线: {current['MA20']:.2f}")
            self.logger.info(f"RSI: {current['RSI']:.2f}")
            self.logger.info(f"MACD: {current['MACD']:.2f}, Signal: {current['Signal']:.2f}")
            
            # 检查KDJ是否为NaN
            if not np.isnan(current['K']) and not np.isnan(current['D']) and not np.isnan(current['J']):
                self.logger.info(f"KDJ: K={current['K']:.2f}, D={current['D']:.2f}, J={current['J']:.2f}")
            else:
                self.logger.info("KDJ: 数据不足")
                
            # 检查布林带是否为NaN
            if not np.isnan(current['BB_Upper']) and not np.isnan(current['BB_Middle']) and not np.isnan(current['BB_Lower']):
                self.logger.info(f"布林带: 上轨={current['BB_Upper']:.2f}, 中轨={current['BB_Middle']:.2f}, 下轨={current['BB_Lower']:.2f}")
            else:
                self.logger.info("布林带: 数据不足")
                
            # 检查ATR是否为NaN
            if not np.isnan(current['ATR']):
                self.logger.info(f"ATR: {current['ATR']:.2f}")
            else:
                self.logger.info("ATR: 数据不足")
                
            self.logger.info(f"成交量: {int(current['volume'])}")
            self.logger.info(f"5日均量: {int(current['volume_ma5'])}")
            
            buy_price_str = "0" if self.buy_price == 0 else f"{self.buy_price:.2f}"
            self.logger.info(f"当前状态: 现金={self.cash:.2f}, 持仓={self.position}股, 买入价={buy_price_str}")
            
            total_value = self.cash
            if self.position > 0:
                total_value += self.position * float(current['close'])
            self.logger.info(f"总价值: {total_value:.2f}")
            self.logger.info("--------------------------------")
            
            # 计算买入信号
            golden_cross = (prev['MA5'] <= prev['MA10']) and (current['MA5'] > current['MA10'])
            volume_confirm = current['volume'] > current['volume_ma5'] * self.volume_ratio
            rsi_buy = current['RSI'] < self.rsi_buy and prev['RSI'] < self.rsi_buy
            macd_golden_cross = (prev['MACD'] <= prev['Signal']) and (current['MACD'] > current['Signal'])
            kdj_golden_cross = (prev['K'] <= prev['D']) and (current['K'] > current['D'])
            bb_bounce = current['close'] < current['BB_Lower'] * 1.05
            trend_up = current['close'] > current['MA20']
            
            # 计算卖出信号
            death_cross = (prev['MA5'] >= prev['MA10']) and (current['MA5'] < current['MA10'])
            rsi_sell = current['RSI'] > self.rsi_sell
            macd_death_cross = (prev['MACD'] >= prev['Signal']) and (current['MACD'] < current['Signal'])
            kdj_death_cross = (prev['K'] >= prev['D']) and (current['K'] < current['D'])
            bb_pullback = current['close'] > current['BB_Upper'] * 0.95
            trend_down = current['close'] < current['MA20']
            
            # 输出信号分析
            self.logger.info("信号分析:")
            self.logger.info(f"均线金叉: {'是' if golden_cross else '否'}")
            self.logger.info(f"成交量确认: {'是' if volume_confirm else '否'}")
            self.logger.info(f"RSI买入信号: {'是' if rsi_buy else '否'} (RSI={current['RSI']:.2f}, 阈值={self.rsi_buy})")
            self.logger.info(f"MACD金叉: {'是' if macd_golden_cross else '否'}")
            self.logger.info(f"KDJ金叉: {'是' if kdj_golden_cross else '否'}")
            self.logger.info(f"布林带下轨反弹: {'是' if bb_bounce else '否'}")
            self.logger.info(f"价格在20日均线上方: {'是' if trend_up else '否'}")
            self.logger.info(f"均线死叉: {'是' if death_cross else '否'}")
            self.logger.info(f"RSI卖出信号: {'是' if rsi_sell else '否'} (RSI={current['RSI']:.2f}, 阈值={self.rsi_sell})")
            self.logger.info(f"MACD死叉: {'是' if macd_death_cross else '否'}")
            self.logger.info(f"KDJ死叉: {'是' if kdj_death_cross else '否'}")
            self.logger.info(f"布林带上轨回落: {'是' if bb_pullback else '否'}")
            self.logger.info(f"价格在20日均线下方: {'是' if trend_down else '否'}")
            self.logger.info("--------------------------------")
            
            # 买入条件组合
            buy_signal_1 = golden_cross and volume_confirm and trend_up
            buy_signal_2 = rsi_buy and bb_bounce and volume_confirm
            buy_signal_3 = macd_golden_cross and kdj_golden_cross and trend_up
            
            # 卖出条件组合
            sell_signal_1 = death_cross and trend_down
            sell_signal_2 = rsi_sell and bb_pullback
            sell_signal_3 = macd_death_cross and kdj_death_cross
            
            # 输出交易信号
            self.logger.info("交易信号:")
            self.logger.info(f"买入信号1 (均线金叉+成交量+趋势): {'是' if buy_signal_1 else '否'}")
            self.logger.info(f"买入信号2 (RSI超卖+布林带下轨+成交量): {'是' if buy_signal_2 else '否'}")
            self.logger.info(f"买入信号3 (MACD金叉+KDJ金叉+趋势): {'是' if buy_signal_3 else '否'}")
            self.logger.info(f"卖出信号1 (均线死叉+趋势): {'是' if sell_signal_1 else '否'}")
            self.logger.info(f"卖出信号2 (RSI超买+布林带上轨): {'是' if sell_signal_2 else '否'}")
            self.logger.info(f"卖出信号3 (MACD死叉+KDJ死叉): {'是' if sell_signal_3 else '否'}")
            self.logger.info("--------------------------------")
            
            # 止损止盈信号
            if self.position > 0 and self.buy_price > 0:
                # 更新持仓期间最高价
                if current['close'] > self.highest_price:
                    self.highest_price = current['close']
                
                # 固定止损
                stop_loss_triggered = current['close'] <= self.buy_price * (1 - self.stop_loss)
                
                # 固定止盈
                take_profit_triggered = current['close'] >= self.buy_price * (1 + self.take_profit)
                
                # 追踪止损 (从最高点回撤一定比例)
                trailing_stop_triggered = current['close'] <= self.highest_price * (1 - self.trailing_stop)
                
                # 动态止损 (基于ATR)
                atr_stop_triggered = current['close'] <= self.buy_price - 2 * current['ATR']
                
                # 综合止损止盈信号
                exit_position = stop_loss_triggered or take_profit_triggered or trailing_stop_triggered or atr_stop_triggered
                
                # 输出止损止盈信号
                self.logger.info("止损止盈信号:")
                self.logger.info(f"固定止损: {'是' if stop_loss_triggered else '否'} (当前价={current['close']}, 止损价={self.buy_price * (1 - self.stop_loss):.2f})")
                self.logger.info(f"固定止盈: {'是' if take_profit_triggered else '否'} (当前价={current['close']}, 止盈价={self.buy_price * (1 + self.take_profit):.2f})")
                self.logger.info(f"追踪止损: {'是' if trailing_stop_triggered else '否'} (当前价={current['close']}, 最高价={self.highest_price}, 止损价={self.highest_price * (1 - self.trailing_stop):.2f})")
                self.logger.info(f"ATR止损: {'是' if atr_stop_triggered else '否'} (当前价={current['close']}, 止损价={self.buy_price - 2 * current['ATR']:.2f})")
                self.logger.info("--------------------------------")
                
                if exit_position:
                    # 执行卖出
                    self.execute_trade('sell', current['close'])
                    return
            
            # 执行交易
            if self.position == 0 and (buy_signal_1 or buy_signal_2 or buy_signal_3):
                # 执行买入
                self.execute_trade('buy', current['close'])
            elif self.position > 0 and (sell_signal_1 or sell_signal_2 or sell_signal_3):
                # 执行卖出
                self.execute_trade('sell', current['close'])
            
            return None
            
        except Exception as e:
            self.logger.error(f"检查信号出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
            
    def execute_trade(self, action, price):
        """执行交易"""
        try:
            if action == 'buy' and self.cash > 0:
                # 计算可买数量（整百股）
                shares = int(self.cash / price / 100) * 100
                if shares >= 100:
                    cost = shares * price
                    self.cash -= cost
                    self.position += shares
                    self.buy_price = price
                    self.highest_price = price
                    
                    self.logger.info(f"""
【交易信号】买入
--------------------------------
股票：{self.security}
价格：{price:.2f}
数量：{shares}股
金额：{cost:.2f}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------""")
                    
                    if not self.simulation_mode:
                        # 这里可以添加实际交易的代码
                        self.logger.info("实盘交易模式：执行买入操作")
                    else:
                        self.logger.info("模拟交易模式：模拟买入操作")
                    
            elif action == 'sell' and self.position > 0:
                # 计算收益
                revenue = self.position * price
                profit = revenue - (self.position * self.buy_price)
                profit_percent = (price / self.buy_price - 1) * 100
                
                self.cash += revenue
                
                self.logger.info(f"""
【交易信号】卖出
--------------------------------
股票：{self.security}
价格：{price:.2f}
数量：{self.position}股
金额：{revenue:.2f}
盈亏：{profit:.2f} ({profit_percent:.2f}%)
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------""")
                
                if not self.simulation_mode:
                    # 这里可以添加实际交易的代码
                    self.logger.info("实盘交易模式：执行卖出操作")
                else:
                    self.logger.info("模拟交易模式：模拟卖出操作")
                
                # 重置持仓相关变量
                self.position = 0
                self.buy_price = 0
                self.highest_price = 0
                
        except Exception as e:
            self.logger.error(f"执行交易出错: {str(e)}")
            
    def run(self):
        """运行策略"""
        try:
            self.logger.info("开始运行策略...")
            
            # 获取历史数据
            df = self.get_stock_data()
            if df is None:
                return
                
            # 计算信号
            df = self.calculate_signals(df)
            if df is None:
                return
                
            # 检查信号
            self.check_signals(df)
            
        except Exception as e:
            self.logger.error(f"策略运行出错: {str(e)}")
            
if __name__ == "__main__":
    trader = AutoTrader()
    trader.run() 