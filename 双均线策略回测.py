import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import baostock as bs
from datetime import datetime
import logging
import itertools

class DualMABacktest:
    def __init__(self, stock_code, start_date, end_date, short_window=3, long_window=10):
        """
        初始化回测参数

        参数:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        short_window: 短期均线周期
        long_window: 长期均线周期
        """
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.short_window = short_window
        self.long_window = long_window
        self.data = None
        self.positions = None
        self.returns = None
        
        # 策略参数
        self.stop_loss = 0.03      # 止损比例
        self.take_profit = 0.03    # 第一档止盈比例
        self.take_profit2 = 0.05   # 第二档止盈比例
        self.take_profit3 = 0.08   # 第三档止盈比例
        self.trailing_stop = 0.02  # 追踪止损比例
        self.volume_ratio = 1.2    # 成交量放大倍数
        self.rsi_period = 14       # RSI周期
        self.rsi_buy = 35          # RSI买入阈值
        self.rsi_sell = 70         # RSI卖出阈值
        self.position_size = 0.3   # 单次建仓比例
        self.max_position = 0.8    # 最大仓位比例
        
        # 新增参数
        self.atr_period = 14       # ATR周期
        self.vwap_period = 10      # VWAP周期
        self.momentum_period = 5    # 动量周期
        self.obv_ma_period = 10    # OBV均线周期
        self.min_amount = 500000   # 最小成交额(万元)
        
        # 设置日志
        self.setup_logging()
        
        # 初始化baostock
        bs.login()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backtest.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def __del__(self):
        """析构函数，确保退出时登出baostock"""
        try:
            bs.logout()
        except:
            pass

    def get_data(self):
        """获取股票数据"""
        try:
            # 转换股票代码格式
            if self.stock_code.startswith('6'):
                bs_code = f"sh.{self.stock_code}"
            else:
                bs_code = f"sz.{self.stock_code}"

            self.logger.info(f"获取股票 {bs_code} 的历史数据...")

            # 使用baostock获取数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,close,volume,amount,high,low,open",
                start_date=self.start_date,
                end_date=self.end_date,
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != '0':
                raise Exception(f"获取数据失败: {rs.error_msg}")

            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 转换数据类型
            numeric_columns = ['close', 'volume', 'amount', 'high', 'low', 'open']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)

            # 按日期升序排序
            df = df.sort_values('date')
            df.set_index('date', inplace=True)

            # 计算技术指标
            self.calculate_indicators(df)

            self.data = df
            self.logger.info(f"成功获取 {len(df)} 条历史数据")
            return True

        except Exception as e:
            self.logger.error(f"获取数据失败: {str(e)}")
            return False

    def calculate_indicators(self, df):
        """计算技术指标"""
        try:
            # 基础均线指标
            df.loc[:, 'short_ma'] = df['close'].rolling(window=self.short_window).mean()
            df.loc[:, 'long_ma'] = df['close'].rolling(window=self.long_window).mean()
            df.loc[:, 'ma20'] = df['close'].rolling(window=20).mean()
            df.loc[:, 'ma60'] = df['close'].rolling(window=60).mean()
            
            # 成交量指标
            df.loc[:, 'volume_ma'] = df['volume'].rolling(window=self.short_window).mean()
            df.loc[:, 'amount_ma'] = df['amount'].rolling(window=self.short_window).mean()
            
            # VWAP
            df.loc[:, 'vwap'] = (df['amount'].rolling(window=self.vwap_period).sum() / 
                                df['volume'].rolling(window=self.vwap_period).sum())
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df.loc[:, 'atr'] = true_range.rolling(window=self.atr_period).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df.loc[:, 'rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df.loc[:, 'macd'] = exp1 - exp2
            df.loc[:, 'signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
            df.loc[:, 'macd_hist'] = df['macd'] - df['signal_line']
            
            # OBV
            df.loc[:, 'obv'] = (df['volume'] * (~df['close'].diff().le(0) * 2 - 1)).cumsum()
            df.loc[:, 'obv_ma'] = df['obv'].rolling(window=self.obv_ma_period).mean()
            
            # 动量指标
            df.loc[:, 'momentum'] = df['close'] / df['close'].shift(self.momentum_period)
            
            # 趋势强度
            df.loc[:, 'trend_strength'] = ((df['close'] - df['close'].rolling(window=20).mean()) / 
                                         df['close'].rolling(window=20).std())
            
            # 布林带
            df.loc[:, 'bb_middle'] = df['close'].rolling(window=20).mean()
            df.loc[:, 'bb_std'] = df['close'].rolling(window=20).std()
            df.loc[:, 'bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
            df.loc[:, 'bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
            df.loc[:, 'bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # 趋势确认
            df.loc[:, 'uptrend'] = (df['close'] > df['ma20']) & (df['ma20'] > df['ma60'])
            df.loc[:, 'downtrend'] = (df['close'] < df['ma20']) & (df['ma20'] < df['ma60'])
            
            return df
            
        except Exception as e:
            self.logger.error(f"计算技术指标失败: {str(e)}")
            return None

    def check_market_condition(self, i):
        """检查市场条件"""
        try:
            # 检查成交量
            if self.data['amount'].iloc[i] < self.min_amount:
                return False
                
            # 检查趋势（放宽条件）
            if self.data['close'].iloc[i] < self.data['ma20'].iloc[i]:
                return False
                
            # 检查波动率（放宽条件）
            if (self.data['bb_width'].iloc[i] > self.data['bb_width'].rolling(window=20).mean().iloc[i] * 2):
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"检查市场条件失败: {str(e)}")
            return False

    def generate_signals(self):
        """生成交易信号"""
        try:
            # 初始化信号
            self.data.loc[:, 'signal'] = 0
            self.data.loc[:, 'position'] = 0
            
            position = 0
            entry_price = 0
            highest_price = 0
            
            for i in range(self.long_window, len(self.data)):
                if position == 0:  # 无仓位，检查买入信号
                    # 首先检查市场条件
                    if not self.check_market_condition(i):
                        continue
                        
                    # 均线系统（放宽条件）
                    ma_trend = (self.data['short_ma'].iloc[i] > self.data['long_ma'].iloc[i] and
                              self.data['close'].iloc[i] > self.data['short_ma'].iloc[i])
                    
                    # MACD系统（放宽条件）
                    macd_signal = (self.data['macd'].iloc[i] > self.data['signal_line'].iloc[i])
                    
                    # 成交量系统（放宽条件）
                    volume_confirm = (self.data['volume'].iloc[i] > self.data['volume_ma'].iloc[i] * self.volume_ratio)
                    
                    # RSI系统（放宽条件）
                    rsi_signal = (self.data['rsi'].iloc[i] > self.rsi_buy and 
                                self.data['rsi'].iloc[i] < 65)
                    
                    # 动量系统
                    momentum_signal = self.data['momentum'].iloc[i] > 1.01
                    
                    # 买入条件组合（放宽条件）
                    if ((ma_trend and (macd_signal or volume_confirm)) or  # 均线+MACD或量能
                        (rsi_signal and momentum_signal)):  # RSI+动量
                        
                        self.data.loc[self.data.index[i], 'signal'] = 1
                        self.data.loc[self.data.index[i], 'position'] = 1
                        position = 1
                        entry_price = self.data['close'].iloc[i]
                        highest_price = entry_price
                        self.logger.info(f"买入信号 - 日期: {self.data.index[i]}, 价格: {entry_price:.2f}")
                        
                elif position == 1:  # 有仓位，检查卖出信号
                    current_price = self.data['close'].iloc[i]
                    price_change = (current_price - entry_price) / entry_price
                    
                    # 更新最高价
                    if current_price > highest_price:
                        highest_price = current_price
                    
                    # 计算动态止损
                    atr = self.data['atr'].iloc[i]
                    dynamic_stop = max(self.stop_loss, 1.2 * atr / current_price)
                    
                    # 追踪止损
                    trailing_stop_triggered = (highest_price - current_price) / highest_price > self.trailing_stop
                    
                    # 分段止盈
                    if price_change > self.take_profit3:  # 超过8%
                        dynamic_stop = max(dynamic_stop * 0.6, 0.02)  # 收紧止损
                    elif price_change > self.take_profit2:  # 超过5%
                        dynamic_stop = max(dynamic_stop * 0.7, 0.02)  # 收紧止损
                    elif price_change > self.take_profit:  # 超过3%
                        dynamic_stop = max(dynamic_stop * 0.8, 0.02)  # 收紧止损
                    
                    # 止损
                    if price_change < -dynamic_stop:
                        self.data.loc[self.data.index[i], 'signal'] = 0
                        self.data.loc[self.data.index[i], 'position'] = -1
                        position = 0
                        self.logger.info(f"止损卖出 - 日期: {self.data.index[i]}, 价格: {current_price:.2f}, 损失: {price_change*100:.2f}%")
                        continue
                    
                    # 止盈或追踪止损
                    if trailing_stop_triggered:
                        self.data.loc[self.data.index[i], 'signal'] = 0
                        self.data.loc[self.data.index[i], 'position'] = -1
                        position = 0
                        self.logger.info(f"追踪止损卖出 - 日期: {self.data.index[i]}, 价格: {current_price:.2f}, 收益: {price_change*100:.2f}%")
                        continue
                    
                    # 技术指标卖出信号（放宽条件）
                    ma_reversal = (self.data['short_ma'].iloc[i] < self.data['long_ma'].iloc[i] and
                                 self.data['close'].iloc[i] < self.data['long_ma'].iloc[i])
                    
                    macd_reversal = (self.data['macd'].iloc[i] < self.data['signal_line'].iloc[i] and
                                   self.data['macd_hist'].iloc[i] < 0)
                    
                    volume_reversal = self.data['volume'].iloc[i] > self.data['volume_ma'].iloc[i] * 1.8
                    
                    momentum_reversal = self.data['momentum'].iloc[i] < 0.99
                    
                    # 卖出条件组合（放宽条件）
                    if ((ma_reversal and macd_reversal) or  # 均线死叉+MACD死叉
                        (volume_reversal and momentum_reversal)):  # 放量下跌+动量反转
                        
                        self.data.loc[self.data.index[i], 'signal'] = 0
                        self.data.loc[self.data.index[i], 'position'] = -1
                        position = 0
                        self.logger.info(f"卖出信号 - 日期: {self.data.index[i]}, 价格: {current_price:.2f}, 收益: {price_change*100:.2f}%")

            # 确保最后一个持仓日期卖出
            if position == 1:
                last_price = self.data['close'].iloc[-1]
                price_change = (last_price - entry_price) / entry_price
                self.data.loc[self.data.index[-1], 'signal'] = 0
                self.data.loc[self.data.index[-1], 'position'] = -1
                self.logger.info(f"最终卖出 - 日期: {self.data.index[-1]}, 价格: {last_price:.2f}, 收益: {price_change*100:.2f}%")

            return True

        except Exception as e:
            self.logger.error(f"生成信号失败: {str(e)}")
            return False

    def calculate_returns(self):
        """计算策略收益"""
        try:
            # 计算每日收益
            self.data.loc[:, 'returns'] = np.log(self.data['close'] / self.data['close'].shift(1))
            
            # 计算策略收益
            self.data.loc[:, 'strategy_returns'] = self.data['signal'].shift(1) * self.data['returns']
            
            # 计算考虑交易成本后的收益
            trade_cost = 0.002  # 双向交易成本
            self.data.loc[:, 'cost'] = abs(self.data['position']) * trade_cost
            self.data.loc[:, 'strategy_returns_after_cost'] = self.data['strategy_returns'] - self.data['cost']
            
            # 计算累计收益
            self.data.loc[:, 'cum_returns'] = self.data['returns'].cumsum()
            self.data.loc[:, 'cum_strategy_returns'] = self.data['strategy_returns_after_cost'].cumsum()

            return True

        except Exception as e:
            self.logger.error(f"计算收益失败: {str(e)}")
            return False

    def analyze_performance(self):
        """分析策略表现"""
        try:
            # 计算交易天数
            days = len(self.data)
            trading_days_per_year = 252
            
            # 计算总收益率
            total_returns = np.exp(self.data['cum_strategy_returns'].iloc[-1]) - 1
            
            # 计算年化收益率
            annual_returns = (1 + total_returns) ** (trading_days_per_year / days) - 1
            
            # 计算夏普比率
            daily_returns = self.data['strategy_returns_after_cost'].dropna()
            if len(daily_returns) > 0:
                excess_returns = daily_returns - 0.03/trading_days_per_year  # 假设无风险利率为3%
                sharpe_ratio = np.sqrt(trading_days_per_year) * excess_returns.mean() / excess_returns.std() if excess_returns.std() != 0 else 0
            else:
                sharpe_ratio = 0
            
            # 计算最大回撤
            cum_returns = np.exp(self.data['cum_strategy_returns']) - 1
            running_max = cum_returns.cummax()
            drawdown = (running_max - cum_returns) / (1 + running_max)
            max_drawdown = drawdown.max()
            
            # 计算交易统计
            trades = self.data[self.data['position'] != 0]
            total_trades = len(trades) // 2  # 每次交易包含买入和卖出两个操作
            
            # 计算胜率和盈亏比
            if total_trades > 0:
                winning_trades = trades[trades['strategy_returns_after_cost'] > 0]
                losing_trades = trades[trades['strategy_returns_after_cost'] <= 0]
                
                win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0
                avg_win = winning_trades['strategy_returns_after_cost'].mean() if len(winning_trades) > 0 else 0
                avg_loss = losing_trades['strategy_returns_after_cost'].mean() if len(losing_trades) > 0 else 0
                profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
                
                # 计算最大连续盈亏天数
                returns = self.data['strategy_returns_after_cost']
                pos_returns = returns > 0
                neg_returns = returns < 0
                
                try:
                    max_consecutive_wins = max((sum(1 for _ in group) for key, group in itertools.groupby(pos_returns) if key), default=0)
                    max_consecutive_losses = max((sum(1 for _ in group) for key, group in itertools.groupby(neg_returns) if key), default=0)
                except:
                    max_consecutive_wins = 0
                    max_consecutive_losses = 0
            else:
                win_rate = 0
                avg_win = 0
                avg_loss = 0
                profit_loss_ratio = 0
                max_consecutive_wins = 0
                max_consecutive_losses = 0
            
            # 计算换手率
            turnover_rate = total_trades * 100 / days if days > 0 else 0  # 日均换手率(%)
            
            # 计算Beta和信息比率
            market_returns = self.data['returns']
            strategy_returns = self.data['strategy_returns_after_cost']
            
            if len(strategy_returns) > 1 and market_returns.std() != 0:
                beta = np.cov(strategy_returns, market_returns)[0,1] / np.var(market_returns)
                excess_returns = strategy_returns - market_returns
                information_ratio = np.sqrt(trading_days_per_year) * excess_returns.mean() / excess_returns.std() if excess_returns.std() != 0 else 0
            else:
                beta = 0
                information_ratio = 0
            
            # 汇总结果
            performance = {
                '总收益率 (%)': total_returns * 100,
                '年化收益率 (%)': annual_returns * 100,
                '夏普比率': sharpe_ratio,
                '最大回撤 (%)': max_drawdown * 100,
                '胜率 (%)': win_rate * 100,
                '盈亏比': profit_loss_ratio,
                '总交易次数': total_trades,
                '日均换手率 (%)': turnover_rate,
                'Beta系数': beta,
                '信息比率': information_ratio,
                '最大连续盈利天数': max_consecutive_wins,
                '最大连续亏损天数': max_consecutive_losses,
                '平均盈利 (%)': avg_win * 100,
                '平均亏损 (%)': avg_loss * 100
            }
            
            # 输出结果
            self.logger.info("\n=== 策略表现分析 ===")
            for metric, value in performance.items():
                if isinstance(value, float):
                    self.logger.info(f"{metric}: {value:.2f}")
                else:
                    self.logger.info(f"{metric}: {value}")
                
            return performance
            
        except Exception as e:
            self.logger.error(f"分析表现失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def plot_results(self):
        """绘制回测结果图表"""
        try:
            plt.style.use('seaborn')
            fig = plt.figure(figsize=(15, 12))

            # 1. 价格和均线
            ax1 = plt.subplot(3, 1, 1)
            ax1.plot(self.data.index, self.data['close'], label='Price', alpha=0.7)
            ax1.plot(self.data.index, self.data['short_ma'], label=f'{self.short_window}MA', alpha=0.7)
            ax1.plot(self.data.index, self.data['long_ma'], label=f'{self.long_window}MA', alpha=0.7)

            # 标记买卖点
            buy_points = self.data[self.data['position'] == 1]
            sell_points = self.data[self.data['position'] == -1]
            ax1.scatter(buy_points.index, buy_points['close'], marker='^', c='g', s=100, label='Buy', alpha=0.7)
            ax1.scatter(sell_points.index, sell_points['close'], marker='v', c='r', s=100, label='Sell', alpha=0.7)

            ax1.set_title('Price and Moving Averages')
            ax1.set_ylabel('Price')
            ax1.legend()
            ax1.grid(True)

            # 2. RSI和成交量
            ax2 = plt.subplot(3, 1, 2)
            ax2.plot(self.data.index, self.data['rsi'], label='RSI', color='purple', alpha=0.7)
            ax2.axhline(y=self.rsi_buy, color='g', linestyle='--', alpha=0.5)
            ax2.axhline(y=self.rsi_sell, color='r', linestyle='--', alpha=0.5)
            ax2.set_title('RSI Indicator')
            ax2.set_ylabel('RSI')
            ax2.grid(True)

            ax2_volume = ax2.twinx()
            ax2_volume.bar(self.data.index, self.data['volume'], color='gray', alpha=0.3)
            ax2_volume.plot(self.data.index, self.data['volume_ma'], color='blue', alpha=0.7)
            ax2_volume.set_ylabel('Volume')

            # 3. 累计收益对比
            ax3 = plt.subplot(3, 1, 3)
            ax3.plot(self.data.index, 100 * np.exp(self.data['cum_returns']) - 100, label='Buy and Hold', alpha=0.7)
            ax3.plot(self.data.index, 100 * np.exp(self.data['cum_strategy_returns']) - 100, label='Strategy', alpha=0.7)
            ax3.set_title('Cumulative Returns (%)')
            ax3.set_ylabel('Returns (%)')
            ax3.legend()
            ax3.grid(True)

            plt.tight_layout()
            plt.show()

        except Exception as e:
            self.logger.error(f"绘制图表失败: {str(e)}")

    def run_backtest(self):
        """运行回测"""
        self.logger.info("开始回测...")
        
        if not self.get_data():
            return False

        if not self.generate_signals():
            return False

        if not self.calculate_returns():
            return False

        # 分析和展示结果
        performance = self.analyze_performance()
        if performance:
            self.logger.info("\n=== 策略表现 ===")
            for metric, value in performance.items():
                self.logger.info(f"{metric}: {value:.4f}")

        # 绘制图表
        self.plot_results()

        return True

# 使用示例
if __name__ == "__main__":
    # 回测参数
    stock_code = '300677'  # 股票代码
    start_date = '2022-01-01'
    end_date = '2023-12-31'
    short_window = 3  # 短期均线周期
    long_window = 10  # 长期均线周期
    
    print("开始回测...")
    print(f"股票代码: {stock_code}")
    print(f"回测区间: {start_date} 至 {end_date}")
    print(f"参数设置: 短期均线={short_window}日, 长期均线={long_window}日")

    # 创建回测实例
    backtest = DualMABacktest(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        short_window=short_window,
        long_window=long_window
    )
    
    # 运行回测
    backtest.run_backtest()

