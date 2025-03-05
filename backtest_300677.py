import pandas as pd
import numpy as np
import baostock as bs
import logging
from datetime import datetime
import pandas_ta as ta

class SingleStockBacktest:
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
        
    def __init__(self):
        # 初始化日志
        self.setup_logging()
        self.logger.info("开始初始化回测系统...")
        
        # 回测参数
        self.initial_capital = 1000000  # 初始资金
        self.position = 0  # 当前持仓
        self.cash = self.initial_capital  # 当前现金
        
        # 仓位控制
        self.max_position_ratio = 1.0  # 最大仓位比例提高到100%
        self.min_position_ratio = 0.3  # 最小仓位比例提高到30%
        self.position_step = 0.3  # 加仓步长提高到30%
        
        # 持仓时间控制
        self.min_hold_days = 1  # 最小持仓天数减少到1天
        self.max_hold_days = 20  # 最大持仓天数增加到20天
        
        # 止损止盈参数
        self.stop_loss = 0.05  # 止损比例放宽到5%
        self.profit_stop = {
            0.08: 0.03,  # 盈利8%时，回撤3%止盈
            0.15: 0.05,  # 盈利15%时，回撤5%止盈
            0.20: 0.08   # 盈利20%时，回撤8%止盈
        }
        
        # 趋势参数
        self.trend_days = 1  # 趋势确认天数减少到1天
        self.volume_ratio = 1.2  # 放量确认倍数降低到1.2倍
        
        # 技术指标参数
        self.rsi_period = 6  # RSI周期改为6
        self.rsi_buy = 35  # RSI买入阈值提高到35
        self.rsi_sell = 80  # RSI卖出阈值提高到80
        self.ma_periods = [5, 10, 20]  # 均线周期改为5、10、20日
        
        # 回测区间
        self.start_date = '2020-01-01'
        self.end_date = '2021-12-31'
        
        # 交易标的
        self.security = 'sz.300677'
        
        # 连接BaoStock
        self.logger.info("正在连接BaoStock...")
        self.bs = bs.login()
        if self.bs.error_code != '0':
            self.logger.error(f"BaoStock登录失败: {self.bs.error_msg}")
            raise Exception("BaoStock登录失败")
        self.logger.info("BaoStock连接成功")
        
        # 交易状态
        self.trades = []
        
    def __del__(self):
        """析构函数，确保退出时登出BaoStock"""
        try:
            bs.logout()
        except:
            pass
            
    def get_stock_data(self):
        """获取股票数据"""
        try:
            rs = bs.query_history_k_data_plus(
                self.security,
                "date,close,volume,high,low,amount",
                start_date=self.start_date,
                end_date=self.end_date,
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != '0':
                self.logger.error(f"获取数据失败: {rs.error_msg}")
                return None
                
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            df = pd.DataFrame(data_list, columns=['date', 'close', 'volume', 'high', 'low', 'amount'])
            df[['close', 'volume', 'high', 'low', 'amount']] = df[['close', 'volume', 'high', 'low', 'amount']].apply(pd.to_numeric)
            return df.dropna()
            
        except Exception as e:
            self.logger.error(f"获取数据出错: {str(e)}")
            return None
            
    def calculate_indicators(self, df):
        """计算技术指标"""
        try:
            # 计算移动平均线
            for period in self.ma_periods:
                df[f'MA{period}'] = df['close'].rolling(window=period).mean()
            
            # 计算RSI
            df.ta.rsi(close='close', length=self.rsi_period, append=True)
            df.rename(columns={f'RSI_{self.rsi_period}': 'RSI'}, inplace=True)
            
            # 计算MACD
            df.ta.macd(close='close', append=True)
            
            # 计算KDJ
            df.ta.stoch(high='high', low='low', close='close', append=True)
            
            # 计算成交量变化
            df['VOL_MA5'] = df['volume'].rolling(window=5).mean()
            df['VOL_RATIO'] = df['volume'] / df['VOL_MA5']
            
            return df
            
        except Exception as e:
            self.logger.error(f"计算技术指标出错: {str(e)}")
            return None
            
    def check_buy_signal(self, row, prev_row):
        """检查买入信号"""
        try:
            signals = []
            
            # 1. 趋势条件
            trend_ok = row['close'] > row['MA5'] > row['MA10']
            if trend_ok:
                signals.append(True)
            
            # 2. MACD条件
            macd_ok = row['MACD_12_26_9'] > row['MACDs_12_26_9'] and prev_row['MACD_12_26_9'] <= prev_row['MACDs_12_26_9']
            if macd_ok:
                signals.append(True)
            
            # 3. KDJ条件
            kdj_ok = row['STOCHk_14_3_3'] > row['STOCHd_14_3_3'] and prev_row['STOCHk_14_3_3'] <= prev_row['STOCHd_14_3_3']
            if kdj_ok:
                signals.append(True)
            
            # 4. RSI条件
            rsi_ok = row['RSI'] < self.rsi_buy
            if rsi_ok:
                signals.append(True)
            
            # 5. 成交量条件
            volume_ok = row['VOL_RATIO'] > self.volume_ratio
            if volume_ok:
                signals.append(True)
            
            # 需要至少2个条件满足
            return len(signals) >= 2
            
        except Exception as e:
            self.logger.error(f"检查买入信号出错: {str(e)}")
            return False
            
    def check_sell_signal(self, row, buy_price):
        """检查卖出信号"""
        try:
            # 计算收益率
            profit_ratio = (row['close'] - buy_price) / buy_price
            
            # 1. 止损
            if row['close'] < buy_price * (1 - self.stop_loss):
                return True
            
            # 2. 移动止盈
            for target, stop in self.profit_stop.items():
                if profit_ratio >= target:
                    max_price = row['high']
                    if row['close'] < max_price * (1 - stop):
                        return True
            
            # 3. 技术指标反转
            # MACD死叉
            if row['MACD_12_26_9'] < row['MACDs_12_26_9']:
                return True
            
            # RSI超买
            if row['RSI'] > self.rsi_sell:
                return True
            
            # 均线死叉
            if row['MA5'] < row['MA10'] and profit_ratio > 0:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查卖出信号出错: {str(e)}")
            return False
            
    def run_backtest(self):
        """运行回测"""
        try:
            # 获取数据
            df = self.get_stock_data()
            if df is None:
                return
            
            # 计算指标
            df = self.calculate_indicators(df)
            if df is None:
                return
            
            # 初始化交易记录
            trades = []
            holding_days = 0
            buy_price = 0
            position_ratio = 0
            
            # 遍历数据
            for i in range(1, len(df)):
                current_row = df.iloc[i]
                prev_row = df.iloc[i-1]
                
                # 当前未持仓
                if self.position == 0:
                    if self.check_buy_signal(current_row, prev_row):
                        # 分批建仓
                        position_ratio = self.min_position_ratio
                        shares = int(self.cash * position_ratio / current_row['close'] / 100) * 100
                        if shares >= 100:
                            cost = shares * current_row['close']
                            self.cash -= cost
                            self.position = shares
                            buy_price = current_row['close']
                            holding_days = 0
                            trades.append({
                                'date': current_row['date'],
                                'action': 'buy',
                                'price': current_row['close'],
                                'shares': shares,
                                'cost': cost,
                                'cash': self.cash
                            })
                
                # 当前持仓
                else:
                    holding_days += 1
                    
                    # 检查是否需要加仓
                    if position_ratio < self.max_position_ratio and holding_days >= self.min_hold_days:
                        if self.check_buy_signal(current_row, prev_row):
                            new_position_ratio = min(position_ratio + self.position_step, self.max_position_ratio)
                            additional_ratio = new_position_ratio - position_ratio
                            additional_shares = int(self.cash * additional_ratio / current_row['close'] / 100) * 100
                            if additional_shares >= 100:
                                cost = additional_shares * current_row['close']
                                self.cash -= cost
                                self.position += additional_shares
                                position_ratio = new_position_ratio
                                trades.append({
                                    'date': current_row['date'],
                                    'action': 'add',
                                    'price': current_row['close'],
                                    'shares': additional_shares,
                                    'cost': cost,
                                    'cash': self.cash
                                })
                    
                    # 检查是否需要卖出
                    if holding_days >= self.min_hold_days and self.check_sell_signal(current_row, buy_price):
                        revenue = self.position * current_row['close']
                        self.cash += revenue
                        trades.append({
                            'date': current_row['date'],
                            'action': 'sell',
                            'price': current_row['close'],
                            'shares': self.position,
                            'revenue': revenue,
                            'cash': self.cash
                        })
                        self.position = 0
                        position_ratio = 0
                        holding_days = 0
                    
                    # 检查是否超过最大持仓时间
                    elif holding_days >= self.max_hold_days:
                        revenue = self.position * current_row['close']
                        self.cash += revenue
                        trades.append({
                            'date': current_row['date'],
                            'action': 'timeout_sell',
                            'price': current_row['close'],
                            'shares': self.position,
                            'revenue': revenue,
                            'cash': self.cash
                        })
                        self.position = 0
                        position_ratio = 0
                        holding_days = 0
            
            # 输出回测结果
            self.print_backtest_results(trades)
            
        except Exception as e:
            self.logger.error(f"回测过程出错: {str(e)}")
            
    def print_backtest_results(self, trades):
        """打印回测结果"""
        try:
            if not trades:
                self.logger.info("没有产生任何交易")
                return
                
            # 计算基础统计数据
            initial_cash = self.initial_capital
            final_cash = self.cash
            total_return = (final_cash - initial_cash) / initial_cash * 100
            
            # 计算年化收益率
            first_trade_date = datetime.strptime(trades[0]['date'], '%Y-%m-%d')
            last_trade_date = datetime.strptime(trades[-1]['date'], '%Y-%m-%d')
            years = (last_trade_date - first_trade_date).days / 365
            annual_return = (1 + total_return/100) ** (1/years) - 1 if years > 0 else 0
            
            # 计算胜率
            buy_trades = [t for t in trades if t['action'] == 'buy']
            sell_trades = [t for t in trades if t['action'] in ['sell', 'timeout_sell']]
            winning_trades = 0
            
            for i in range(len(buy_trades)):
                if i < len(sell_trades):
                    if sell_trades[i]['price'] > buy_trades[i]['price']:
                        winning_trades += 1
            
            win_rate = winning_trades / len(buy_trades) * 100 if buy_trades else 0
            
            # 打印总体结果
            self.logger.info("\n=== 回测结果 ===")
            self.logger.info(f"初始资金: {initial_cash:,.2f}")
            self.logger.info(f"最终资金: {final_cash:,.2f}")
            self.logger.info(f"总收益率: {total_return:.2f}%")
            self.logger.info(f"年化收益率: {annual_return*100:.2f}%")
            self.logger.info(f"总交易次数: {len(buy_trades)}")
            self.logger.info(f"胜率: {win_rate:.2f}%")
            
            # 打印详细交易记录
            self.logger.info("\n=== 交易记录 ===")
            current_position = None
            for trade in trades:
                if trade['action'] == 'buy':
                    current_position = trade
                    self.logger.info(f"买入 - 日期: {trade['date']}, 价格: {trade['price']:.2f}, 数量: {trade['shares']}")
                elif trade['action'] == 'add':
                    self.logger.info(f"加仓 - 日期: {trade['date']}, 价格: {trade['price']:.2f}, 数量: {trade['shares']}")
                elif trade['action'] in ['sell', 'timeout_sell']:
                    if current_position:
                        hold_days = (datetime.strptime(trade['date'], '%Y-%m-%d') - 
                                   datetime.strptime(current_position['date'], '%Y-%m-%d')).days
                        return_rate = (trade['price'] - current_position['price']) / current_position['price'] * 100
                        action = "卖出" if trade['action'] == 'sell' else "超时卖出"
                        self.logger.info(f"{action} - 日期: {trade['date']}, 价格: {trade['price']:.2f}, "
                                       f"数量: {trade['shares']}, 持仓天数: {hold_days}, 收益率: {return_rate:.2f}%")
                        current_position = None
            
        except Exception as e:
            self.logger.error(f"打印回测结果出错: {str(e)}")

if __name__ == "__main__":
    backtest = SingleStockBacktest()
    backtest.run_backtest() 