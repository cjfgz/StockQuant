import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import talib
import matplotlib.pyplot as plt
from stockquant.message import DingTalk
from stockquant.market import Market

class EnhancedMAStrategy:
    def __init__(self):
        self.setup_logging()
        self.ding = DingTalk()
        
        # 策略参数
        self.ma_short = 10     # 短期均线改为10日
        self.ma_mid = 20       # 中期均线改为20日
        self.ma_long = 60      # 长期均线改为60日
        self.rsi_period = 14   # RSI周期
        self.rsi_buy = 35      # RSI买入阈值调高
        self.rsi_sell = 75     # RSI卖出阈值调高
        self.volume_ma = 20    # 成交量均线周期加长
        self.atr_period = 20   # ATR周期加长
        
        # 资金管理
        self.initial_capital = 1000000  # 初始资金100万
        self.position_size = 0.1        # 单次建仓比例降至10%
        self.stop_loss = 0.08          # 止损比例加大到8%
        self.trailing_stop = 0.12      # 追踪止损比例加大到12%
        
        # 回测区间
        self.start_date = '2021-01-01'
        self.end_date = '2022-12-31'
        
        # 创业板股票池
        self.stock_pool = self.get_chinext_stocks()
        
        # 连接BaoStock
        bs.login()
        
    def __del__(self):
        """析构函数，确保退出时登出BaoStock"""
        try:
            bs.logout()
        except:
            pass
            
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('enhanced_strategy.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_chinext_stocks(self):
        """获取创业板股票列表"""
        try:
            # 使用固定的创业板股票列表进行测试
            test_stocks = [
                'sz.300001', 'sz.300002', 'sz.300003', 'sz.300004', 'sz.300005',
                'sz.300006', 'sz.300007', 'sz.300008', 'sz.300009', 'sz.300010',
                'sz.300011', 'sz.300012', 'sz.300013', 'sz.300014', 'sz.300015',
                'sz.300016', 'sz.300017', 'sz.300018', 'sz.300019', 'sz.300020'
            ]
            self.logger.info(f"获取到{len(test_stocks)}只创业板股票")
            return test_stocks
        except Exception as e:
            self.logger.error(f"获取创业板股票列表失败: {str(e)}")
            return []
            
    def get_stock_data(self, stock_code):
        """获取单个股票的历史数据"""
        try:
            # 获取日K线数据
            rs = bs.query_history_k_data_plus(
                stock_code,
                "date,code,open,high,low,close,volume,amount",
                start_date=self.start_date,
                end_date=self.end_date,
                frequency="d",
                adjustflag="3"  # 后复权
            )
            
            # 检查是否获取成功
            if rs.error_code != '0':
                self.logger.error(f"获取{stock_code}历史数据失败: {rs.error_msg}")
                return None
                
            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                # 验证数据有效性
                try:
                    float(row[2])  # open
                    float(row[3])  # high
                    float(row[4])  # low
                    float(row[5])  # close
                    float(row[6])  # volume
                    float(row[7])  # amount
                    data_list.append(row)
                except:
                    continue
            
            if len(data_list) < 60:  # 至少需要60个交易日的数据
                self.logger.error(f"获取的历史数据不足60天，实际获取了{len(data_list)}天")
                return None
                
            df = pd.DataFrame(data_list, columns=['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount'])
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 删除任何包含NaN的行
            df = df.dropna()
            
            if len(df) < 60:
                self.logger.error(f"清理后的数据不足60天，实际剩余{len(df)}天")
                return None
                
            self.logger.info(f"成功获取{stock_code}的历史数据，共{len(df)}条有效记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取{stock_code}数据出错: {str(e)}")
            return None
            
    def calculate_indicators(self, df):
        """计算技术指标"""
        try:
            # 移动平均线
            df['MA_short'] = df['close'].rolling(window=self.ma_short).mean()
            df['MA_mid'] = df['close'].rolling(window=self.ma_mid).mean()
            df['MA_long'] = df['close'].rolling(window=self.ma_long).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_hist'] = df['MACD'] - df['Signal']
            
            # 布林带
            df['BB_middle'] = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            df['BB_upper'] = df['BB_middle'] + 2 * std
            df['BB_lower'] = df['BB_middle'] - 2 * std
            
            # 成交量
            df['Volume_MA'] = df['volume'].rolling(window=self.volume_ma).mean()
            
            # KDJ
            low_list = df['low'].rolling(9, min_periods=9).min()
            high_list = df['high'].rolling(9, min_periods=9).max()
            rsv = (df['close'] - low_list) / (high_list - low_list) * 100
            df['K'] = rsv.ewm(com=2).mean()
            df['D'] = df['K'].ewm(com=2).mean()
            df['J'] = 3 * df['K'] - 2 * df['D']
            
            # DMI
            plus_dm = df['high'].diff()
            minus_dm = df['low'].diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm > 0] = 0
            tr = pd.DataFrame([
                df['high'] - df['low'],
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            ]).max()
            df['PDI'] = 100 * plus_dm.rolling(14).sum() / tr.rolling(14).sum()
            df['MDI'] = 100 * abs(minus_dm.rolling(14).sum()) / tr.rolling(14).sum()
            df['ADX'] = abs(df['PDI'] - df['MDI']) / (df['PDI'] + df['MDI']) * 100
            
            return df.dropna()
            
        except Exception as e:
            self.logger.error(f"计算技术指标出错: {str(e)}")
            return None
            
    def check_buy_signals(self, row, prev_row):
        """检查买入信号"""
        try:
            # 趋势确认
            trend_confirm = (row['close'] > row['MA_short']) and (row['MA_short'] > row['MA_mid'])
            
            # KDJ金叉
            kdj_cross = (row['K'] > row['D']) and (prev_row['K'] <= prev_row['D']) and (row['J'] < 80)
            
            # DMI多头排列
            dmi_bull = (row['PDI'] > row['MDI']) and (row['ADX'] > 20)
            
            # RSI条件放宽
            rsi_signal = 30 <= row['RSI'] <= 50
            
            # MACD金叉或零轴上方
            macd_signal = ((row['MACD_hist'] > 0) and (prev_row['MACD_hist'] <= 0)) or (row['MACD'] > 0)
            
            # 量价配合
            volume_price = (row['volume'] > row['Volume_MA']) and (row['close'] > prev_row['close'])
            
            # 支撑确认
            support_confirm = row['close'] > row['BB_lower'] and row['close'] < row['BB_middle']
            
            # 综合判断（降低门槛，只需满足部分条件）
            return (trend_confirm and  # 趋势必须确认
                   ((kdj_cross or dmi_bull) and  # 至少一个动量指标满足
                    (rsi_signal or macd_signal) and  # 至少一个摆动指标满足
                    (volume_price or support_confirm)))  # 至少满足量价或支撑条件
            
        except Exception as e:
            self.logger.error(f"检查买入信号出错: {str(e)}")
            return False
            
    def check_sell_signals(self, row, prev_row, buy_price):
        """检查卖出信号"""
        try:
            # 止损和追踪止损
            stop_loss = row['close'] < buy_price * (1 - self.stop_loss)
            highest_since_buy = max(row['close'], prev_row['close'])
            trailing_stop = row['close'] < highest_since_buy * (1 - self.trailing_stop)
            
            # KDJ死叉
            kdj_cross = (row['K'] < row['D']) and (prev_row['K'] >= prev_row['D']) and (row['J'] > 80)
            
            # DMI空头信号
            dmi_bear = (row['PDI'] < row['MDI']) and (row['ADX'] > 20)
            
            # 均线死叉
            ma_cross = (row['MA_short'] < row['MA_mid']) and (prev_row['MA_short'] >= prev_row['MA_mid'])
            
            # RSI超买
            rsi_signal = row['RSI'] > 75
            
            # MACD死叉
            macd_cross = (row['MACD_hist'] < 0) and (prev_row['MACD_hist'] >= 0)
            
            # 价格突破上轨
            price_break = row['close'] > row['BB_upper']
            
            # 放量下跌
            volume_drop = (row['volume'] > row['Volume_MA'] * 1.5) and (row['close'] < prev_row['close'])
            
            # 综合判断
            return (stop_loss or trailing_stop or  # 风险控制
                   (kdj_cross and dmi_bear) or  # 强势反转信号
                   (ma_cross and (rsi_signal or macd_cross)) or  # 趋势反转信号
                   (price_break and volume_drop))  # 突破失败信号
            
        except Exception as e:
            self.logger.error(f"检查卖出信号出错: {str(e)}")
            return False
            
    def backtest_stock(self, stock_code):
        """对单个股票进行回测"""
        try:
            # 获取数据
            df = self.get_stock_data(stock_code)
            if df is None:
                return None
                
            # 计算指标
            df = self.calculate_indicators(df)
            if df is None:
                return None
                
            # 初始化回测变量
            cash = self.initial_capital
            position = 0
            buy_price = 0
            trades = []
            daily_returns = []
            
            # 遍历数据
            for i in range(1, len(df)):
                current_row = df.iloc[i]
                prev_row = df.iloc[i-1]
                
                if position == 0:  # 没有持仓
                    if self.check_buy_signals(current_row, prev_row):
                        # 计算购买数量
                        available_cash = cash * self.position_size
                        shares = int(available_cash / current_row['close'] / 100) * 100
                        if shares >= 100:
                            cost = shares * current_row['close']
                            cash -= cost
                            position = shares
                            buy_price = current_row['close']
                            trades.append({
                                'date': current_row['date'],
                                'type': 'buy',
                                'price': current_row['close'],
                                'shares': shares,
                                'value': cost
                            })
                            
                elif position > 0:  # 持有仓位
                    if self.check_sell_signals(current_row, prev_row, buy_price):
                        # 全部卖出
                        revenue = position * current_row['close']
                        cash += revenue
                        trades.append({
                            'date': current_row['date'],
                            'type': 'sell',
                            'price': current_row['close'],
                            'shares': position,
                            'value': revenue
                        })
                        position = 0
                        buy_price = 0
                        
                # 计算每日收益
                total_value = cash + (position * current_row['close'])
                daily_returns.append({
                    'date': current_row['date'],
                    'value': total_value
                })
                
            # 计算回测结果
            if len(daily_returns) > 0:
                initial_value = self.initial_capital
                final_value = daily_returns[-1]['value']
                total_return = (final_value - initial_value) / initial_value
                
                # 计算年化收益率
                days = (datetime.strptime(self.end_date, '%Y-%m-%d') - 
                       datetime.strptime(self.start_date, '%Y-%m-%d')).days
                annual_return = (1 + total_return) ** (365/days) - 1
                
                # 计算最大回撤
                max_drawdown = 0
                peak = daily_returns[0]['value']
                for daily in daily_returns:
                    if daily['value'] > peak:
                        peak = daily['value']
                    drawdown = (peak - daily['value']) / peak
                    max_drawdown = max(max_drawdown, drawdown)
                
                return {
                    'stock_code': stock_code,
                    'trades': trades,
                    'total_return': total_return,
                    'annual_return': annual_return,
                    'max_drawdown': max_drawdown,
                    'final_value': final_value,
                    'daily_returns': daily_returns
                }
                
        except Exception as e:
            self.logger.error(f"回测{stock_code}出错: {str(e)}")
            return None
            
    def run_backtest(self):
        """运行回测"""
        try:
            self.logger.info("开始回测...")
            results = []
            
            for stock_code in self.stock_pool:
                self.logger.info(f"正在回测 {stock_code}")
                result = self.backtest_stock(stock_code)
                if result and result['total_return'] > 0:  # 只保存有盈利的结果
                    results.append(result)
                    
            # 对结果进行排序
            results.sort(key=lambda x: x['annual_return'], reverse=True)
            
            # 输出回测结果
            self.logger.info("\n=== 回测结果 ===")
            self.logger.info(f"测试股票数量: {len(self.stock_pool)}")
            self.logger.info(f"盈利股票数量: {len(results)}")
            
            if len(results) > 0:
                # 计算组合收益
                portfolio_returns = []
                for result in results[:10]:  # 取前10只表现最好的股票
                    self.logger.info(f"""
股票代码: {result['stock_code']}
总收益率: {result['total_return']*100:.2f}%
年化收益率: {result['annual_return']*100:.2f}%
最大回撤: {result['max_drawdown']*100:.2f}%
交易次数: {len(result['trades'])}
--------------------------------""")
                    
                    # 发送结果到钉钉
                    message = f"""
【回测结果】{result['stock_code']}
--------------------------------
总收益率: {result['total_return']*100:.2f}%
年化收益率: {result['annual_return']*100:.2f}%
最大回撤: {result['max_drawdown']*100:.2f}%
交易次数: {len(result['trades'])}
--------------------------------"""
                    self.ding.send_message(message)
                    
            return results
            
        except Exception as e:
            self.logger.error(f"运行回测出错: {str(e)}")
            return []

class SingleStockBacktest:
    def __init__(self):
        self.market = Market()
        self.setup_logging()
        
        # 股票代码
        self.stock_code = 'sz.300677'  # 注意格式必须是sz.xxxxxx
        
        # 资金管理参数
        self.initial_capital = 1000000  # 初始资金100万
        self.position_size = 0.1        # 单次建仓比例10%
        self.stop_loss = 0.08          # 止损比例8%
        self.trailing_stop = 0.12      # 追踪止损比例12%
        
        # 技术指标参数
        self.ma_short = 10     # 短期均线
        self.ma_mid = 20       # 中期均线
        self.ma_long = 60      # 长期均线
        self.rsi_period = 14   # RSI周期
        self.rsi_buy = 35      # RSI买入阈值
        self.rsi_sell = 75     # RSI卖出阈值
        self.volume_ma = 20    # 成交量均线周期
        self.atr_period = 20   # ATR周期
        
        # 回测区间
        self.start_date = '2021-01-01'
        self.end_date = '2022-12-31'
        
        # 连接BaoStock
        bs.login()
        
    def __del__(self):
        """析构函数，确保退出时登出BaoStock"""
        try:
            bs.logout()
        except:
            pass
            
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backtest_300677.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_stock_data(self):
        """获取股票数据"""
        try:
            # 获取日K线数据
            rs = bs.query_history_k_data_plus(
                self.stock_code,
                "date,code,open,high,low,close,volume,amount",
                start_date=self.start_date,
                end_date=self.end_date,
                frequency="d",
                adjustflag="3"  # 后复权
            )
            
            if rs.error_code != '0':
                self.logger.error(f"获取股票数据失败: {rs.error_msg}")
                return None
                
            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            df = pd.DataFrame(data_list, columns=['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount'])
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                df[col] = pd.to_numeric(df[col])
                
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票数据出错: {str(e)}")
            return None
            
    def calculate_indicators(self, df):
        """计算技术指标"""
        try:
            # 移动平均线
            df['MA_short'] = df['close'].rolling(window=self.ma_short).mean()
            df['MA_mid'] = df['close'].rolling(window=self.ma_mid).mean()
            df['MA_long'] = df['close'].rolling(window=self.ma_long).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_hist'] = df['MACD'] - df['Signal']
            
            # 布林带
            df['BB_middle'] = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            df['BB_upper'] = df['BB_middle'] + 2 * std
            df['BB_lower'] = df['BB_middle'] - 2 * std
            
            # 成交量
            df['Volume_MA'] = df['volume'].rolling(window=self.volume_ma).mean()
            
            return df.dropna()
            
        except Exception as e:
            self.logger.error(f"计算技术指标出错: {str(e)}")
            return None
            
    def run_backtest(self):
        """执行回测"""
        try:
            self.logger.info(f"开始对{self.stock_code}进行回测...")
            self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
            
            # 获取数据
            df = self.get_stock_data()
            if df is None:
                return
                
            # 计算指标
            df = self.calculate_indicators(df)
            if df is None:
                return
                
            # 初始化变量
            cash = self.initial_capital
            position = 0
            trades = []
            max_value = self.initial_capital
            
            # 遍历数据
            for i in range(1, len(df)):
                current_row = df.iloc[i]
                prev_row = df.iloc[i-1]
                
                # 更新最大资产值
                current_value = cash + position * current_row['close']
                max_value = max(max_value, current_value)
                
                # 检查是否需要止损或止盈
                if position > 0:
                    # 计算持仓收益率
                    last_buy_price = trades[-1]['price']
                    current_return = (current_row['close'] - last_buy_price) / last_buy_price
                    
                    # 止损检查
                    if current_return < -self.stop_loss:
                        # 执行止损
                        cash += position * current_row['close']
                        trades.append({
                            'date': current_row['date'],
                            'type': 'sell',
                            'price': current_row['close'],
                            'shares': position,
                            'amount': position * current_row['close'],
                            'return': current_return * 100,
                            'reason': 'stop_loss'
                        })
                        position = 0
                        continue
                        
                # 检查买入信号
                if position == 0:
                    buy_signal = (
                        current_row['MA_short'] > current_row['MA_mid'] and
                        prev_row['MA_short'] <= prev_row['MA_mid'] and
                        current_row['RSI'] < self.rsi_buy and
                        current_row['volume'] > current_row['Volume_MA']
                    )
                    
                    if buy_signal:
                        # 计算购买数量
                        available_amount = cash * self.position_size
                        shares = int(available_amount / current_row['close'] / 100) * 100
                        if shares >= 100:
                            cost = shares * current_row['close']
                            cash -= cost
                            position = shares
                            trades.append({
                                'date': current_row['date'],
                                'type': 'buy',
                                'price': current_row['close'],
                                'shares': shares,
                                'amount': cost
                            })
                            
                # 检查卖出信号
                elif position > 0:
                    sell_signal = (
                        current_row['MA_short'] < current_row['MA_mid'] and
                        prev_row['MA_short'] >= prev_row['MA_mid'] or
                        current_row['RSI'] > self.rsi_sell
                    )
                    
                    if sell_signal:
                        # 执行卖出
                        revenue = position * current_row['close']
                        last_buy_price = trades[-1]['price']
                        return_rate = (current_row['close'] - last_buy_price) / last_buy_price
                        
                        trades.append({
                            'date': current_row['date'],
                            'type': 'sell',
                            'price': current_row['close'],
                            'shares': position,
                            'amount': revenue,
                            'return': return_rate * 100,
                            'reason': 'signal'
                        })
                        
                        cash += revenue
                        position = 0
            
            # 计算回测结果
            final_value = cash + position * df.iloc[-1]['close']
            total_return = (final_value - self.initial_capital) / self.initial_capital * 100
            max_drawdown = ((max_value - final_value) / max_value) * 100 if max_value > final_value else 0
            
            # 计算年化收益率
            days = (datetime.strptime(self.end_date, '%Y-%m-%d') - 
                   datetime.strptime(self.start_date, '%Y-%m-%d')).days
            annual_return = (total_return / days) * 365
            
            # 输出回测结果
            self.logger.info("\n=== 回测结果 ===")
            self.logger.info(f"初始资金: {self.initial_capital:,.2f}")
            self.logger.info(f"最终资金: {final_value:,.2f}")
            self.logger.info(f"总收益率: {total_return:.2f}%")
            self.logger.info(f"年化收益率: {annual_return:.2f}%")
            self.logger.info(f"最大回撤: {max_drawdown:.2f}%")
            self.logger.info(f"交易次数: {len(trades)}")
            
            # 输出交易记录
            self.logger.info("\n=== 交易记录 ===")
            for trade in trades:
                if trade['type'] == 'buy':
                    self.logger.info(f"买入 - 日期: {trade['date']}, 价格: {trade['price']:.2f}, 数量: {trade['shares']}, 金额: {trade['amount']:.2f}")
                else:
                    self.logger.info(f"卖出 - 日期: {trade['date']}, 价格: {trade['price']:.2f}, 数量: {trade['shares']}, 金额: {trade['amount']:.2f}, 收益率: {trade['return']:.2f}%")
            
            # 发送钉钉通知
            message = f"""
【回测结果】{self.stock_code}
--------------------------------
回测期间: {self.start_date} 至 {self.end_date}
初始资金: {self.initial_capital:,.2f}
最终资金: {final_value:,.2f}
总收益率: {total_return:.2f}%
年化收益率: {annual_return:.2f}%
最大回撤: {max_drawdown:.2f}%
交易次数: {len(trades)}
--------------------------------"""
            self.ding = DingTalk()
            self.ding.send_message(message)
            
        except Exception as e:
            self.logger.error(f"回测执行出错: {str(e)}")

if __name__ == "__main__":
    strategy = EnhancedMAStrategy()
    strategy.run_backtest()
    backtest = SingleStockBacktest()
    backtest.run_backtest() 