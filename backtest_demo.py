#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BacktestSystem:
    def __init__(self):
        """初始化回测系统"""
        # 回测参数
        self.stock_code = "sz.300677"  # 默认股票代码：银河磁体
        self.start_date = "2022-01-01"  # 默认开始日期
        self.end_date = "2023-12-31"    # 默认结束日期
        self.initial_capital = 100000   # 默认初始资金
        
        # 策略参数优化
        self.ma_short = 5        # 短期均线周期(改为5，更敏感)
        self.ma_mid = 10        # 中期均线周期(改为10，更敏感)
        self.ma_long = 20       # 长期均线周期(改为20，更敏感)
        self.rsi_period = 6     # RSI周期(改为6，更敏感)
        self.rsi_buy = 30       # RSI买入阈值(改为30)
        self.rsi_sell = 75      # RSI卖出阈值(改为75)
        self.volume_ratio = 2.0 # 成交量放大倍数(改为2.0，要求更强的放量)
        self.stop_loss = 0.06   # 止损比例(改为6%)
        self.take_profit1 = 0.08 # 第一阶段止盈(改为8%)
        self.take_profit2 = 0.15 # 第二阶段止盈(改为15%)
        self.trailing_stop = 0.05 # 追踪止损比例(改为5%)
        self.min_holding_days = 2 # 最小持仓天数(改为2天)
        self.trend_strength_threshold = 1.0  # 趋势强度阈值(新增)
        
    def get_stock_data(self, stock_code, start_date, end_date):
        """获取回测所需的历史数据"""
        try:
            logger.info(f"获取 {stock_code} 从 {start_date} 到 {end_date} 的历史数据")
            
            # 导入baostock库
            import baostock as bs
            
            # 登录baostock
            bs_login = bs.login()
            if bs_login.error_code != '0':
                logger.error(f"登录BaoStock失败: {bs_login.error_msg}")
                return None
                
            # 查询历史数据
            rs = bs.query_history_k_data_plus(
                stock_code,
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2"  # 前复权
            )
            
            if rs.error_code != '0':
                logger.error(f"获取历史数据失败: {rs.error_msg}")
                bs.logout()
                return None
                
            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            # 登出baostock
            bs.logout()
            
            if not data_list:
                logger.error("未获取到历史数据")
                return None
                
            # 创建DataFrame
            df = pd.DataFrame(data_list, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                df[col] = df[col].astype(float)
                
            # 设置日期索引
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            logger.info(f"成功获取 {len(df)} 条历史数据")
            return df
            
        except Exception as e:
            logger.error(f"获取历史数据出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def calculate_indicators(self, df):
        """计算技术指标"""
        try:
            # 计算移动平均线
            df['MA_short'] = df['close'].rolling(window=self.ma_short).mean()
            df['MA_mid'] = df['close'].rolling(window=self.ma_mid).mean()
            df['MA_long'] = df['close'].rolling(window=self.ma_long).mean()
            
            # 计算成交量均线
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma10'] = df['volume'].rolling(window=10).mean()
            
            # 计算MACD
            exp1 = df['close'].ewm(span=9, adjust=False).mean()
            exp2 = df['close'].ewm(span=21, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=7, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 计算布林带
            df['BB_Middle'] = df['close'].rolling(window=20).mean()
            df['BB_Std'] = df['close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + 1.8 * df['BB_Std']
            df['BB_Lower'] = df['BB_Middle'] - 1.8 * df['BB_Std']
            
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
            
            # 计算趋势强度
            df['trend_strength'] = abs(df['MA_short'] - df['MA_mid']) / df['MA_mid'] * 100
            
            return df
            
        except Exception as e:
            logger.error(f"计算技术指标出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df
            
    def check_buy_signal(self, df, i):
        """检查买入信号"""
        try:
            # 获取当前和前一个交易日的数据
            current = df.iloc[i]
            prev = df.iloc[i-1]
            prev2 = df.iloc[i-2] if i > 1 else prev
            
            # 基本条件
            is_yang = current['close'] > current['open']  # 是否为阳线
            is_strong_yang = (current['close'] - current['open']) / current['open'] > 0.02  # 是否为强势阳线
            volume_increase = current['volume'] > current['volume_ma5'] * self.volume_ratio  # 成交量放大
            
            # 均线金叉
            golden_cross_short_mid = (prev['MA_short'] <= prev['MA_mid']) and (current['MA_short'] > current['MA_mid'])
            golden_cross_mid_long = (prev['MA_mid'] <= prev['MA_long']) and (current['MA_mid'] > current['MA_long'])
            
            # 趋势确认
            uptrend = (current['close'] > current['MA_long'] and  # 价格在长期均线上方
                      current['MA_short'] > current['MA_long'] and  # 短期均线在长期均线上方
                      current['MA_mid'] > current['MA_long'])  # 中期均线在长期均线上方
            trend_strength_ok = current['trend_strength'] > self.trend_strength_threshold  # 趋势强度足够
            
            # RSI条件
            rsi_buy_signal = (prev['RSI'] < self.rsi_buy and current['RSI'] >= self.rsi_buy and  # RSI从超卖区域上升
                            current['RSI'] < 50)  # RSI还未到达超买区域
            
            # MACD条件
            macd_golden_cross = (prev['MACD'] <= prev['Signal']) and (current['MACD'] > current['Signal'])
            macd_hist_turning = (prev['Histogram'] <= 0) and (current['Histogram'] > 0)  # MACD柱状图由负转正
            macd_trend = current['MACD'] > prev['MACD']  # MACD向上发展
            
            # 布林带条件
            bb_bounce = (prev['close'] <= prev['BB_Lower'] and current['close'] > current['BB_Lower'] and  # 从布林带下轨反弹
                        current['close'] < current['BB_Middle'])  # 价格未超过布林带中轨
            
            # KDJ条件
            kdj_golden_cross = (prev['K'] <= prev['D']) and (current['K'] > current['D'])  # KDJ金叉
            kdj_low = current['K'] < 40 and current['D'] < 40  # K和D都在低位
            
            # 计算满足的条件数量
            conditions_met = sum([
                is_yang,
                is_strong_yang, 
                volume_increase, 
                golden_cross_short_mid,
                golden_cross_mid_long,
                uptrend,
                trend_strength_ok,
                rsi_buy_signal, 
                macd_golden_cross or macd_hist_turning,
                macd_trend,
                bb_bounce, 
                kdj_golden_cross,
                kdj_low
            ])
            
            # 必要条件：
            # 1. 必须是阳线
            # 2. 必须有放量
            # 3. 必须满足至少6个技术指标条件
            return (is_yang and volume_increase and conditions_met >= 6)
            
        except Exception as e:
            logger.error(f"检查买入信号出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def check_sell_signal(self, df, i, buy_price, buy_date_idx):
        """检查卖出信号"""
        try:
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # 计算持仓天数
            holding_days = i - buy_date_idx
            
            # 如果持仓时间不足最小持仓天数，不卖出
            if holding_days < self.min_holding_days:
                return False, "持仓时间不足"
            
            # 计算从买入后的最高价
            highest_price = df.iloc[buy_date_idx:i+1]['high'].max()
            current_profit = (current['close'] - buy_price) / buy_price
            
            # 固定止损（亏损超过止损比例）
            if current['close'] <= buy_price * (1 - self.stop_loss):
                return True, "止损卖出"
            
            # 追踪止损（从最高点回撤超过追踪止损比例）
            if current_profit > self.take_profit1:  # 只有在盈利超过第一阶段止盈时才启用追踪止损
                if current['close'] <= highest_price * (1 - self.trailing_stop):
                    return True, "追踪止损卖出"
            
            # 分段止盈
            if current_profit >= self.take_profit2:
                return True, "止盈2卖出"
            elif current_profit >= self.take_profit1:
                # 在第一阶段止盈时，需要同时满足以下条件之一：
                # 1. 价格跌破5日均线
                # 2. RSI超买
                # 3. MACD死叉
                price_below_ma5 = current['close'] < current['MA_short']
                rsi_overbought = current['RSI'] > self.rsi_sell
                macd_death = (prev['MACD'] >= prev['Signal']) and (current['MACD'] < current['Signal'])
                
                if price_below_ma5 or rsi_overbought or macd_death:
                    return True, "止盈1卖出"
            
            # 技术指标卖出信号
            # 1. 均线死叉
            death_cross = (prev['MA_short'] >= prev['MA_mid']) and (current['MA_short'] < current['MA_mid'])
            
            # 2. RSI超买
            rsi_sell = current['RSI'] > self.rsi_sell
            
            # 3. MACD死叉
            macd_death_cross = (prev['MACD'] >= prev['Signal']) and (current['MACD'] < current['Signal'])
            
            # 4. 布林带上轨
            bb_top_touch = current['close'] >= current['BB_Upper']
            
            # 5. KDJ死叉
            kdj_death_cross = (prev['K'] >= prev['D']) and (current['K'] < current['D'])
            kdj_high = current['K'] > 80 and current['D'] > 80
            
            # 综合技术指标
            # 需要同时满足：
            # 1. 均线死叉或RSI超买
            # 2. MACD死叉或触及布林带上轨
            # 3. KDJ死叉且在高位
            if (death_cross or rsi_sell) and (macd_death_cross or bb_top_touch) and kdj_death_cross and kdj_high:
                return True, "技术指标卖出"
            
            return False, "继续持有"
            
        except Exception as e:
            logger.error(f"检查卖出信号出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, "检查出错"
            
    def run_backtest(self):
        """运行回测"""
        try:
            logger.info("开始回测...")
            
            # 获取历史数据
            df = self.get_stock_data(self.stock_code, self.start_date, self.end_date)
            if df is None or len(df) == 0:
                logger.error("获取历史数据失败")
                return None
                
            # 计算技术指标
            df = self.calculate_indicators(df)
            
            # 初始化回测变量
            cash = self.initial_capital  # 现金
            position = 0  # 持仓数量
            trades = []  # 交易记录
            daily_values = []  # 每日资产价值
            buy_price = 0  # 买入价格
            buy_date_idx = 0  # 买入日期索引
            
            # 从第20个交易日开始回测（确保有足够的历史数据计算指标）
            for i in range(20, len(df)):
                current_date = df.index[i]
                current_price = df.iloc[i]['close']
                
                # 记录每日资产价值
                total_value = cash + position * current_price
                daily_values.append({
                    'date': current_date,
                    'value': total_value,
                    'cash': cash,
                    'position': position,
                    'price': current_price
                })
                
                # 如果没有持仓，检查买入信号
                if position == 0:
                    if self.check_buy_signal(df, i):
                        # 计算可买入数量
                        buy_amount = cash * 0.95  # 预留5%现金
                        position = int(buy_amount / current_price / 100) * 100  # 买入数量必须是100的整数倍
                        if position > 0:
                            cash -= position * current_price
                            buy_price = current_price
                            buy_date_idx = i
                            trades.append({
                                'date': current_date,
                                'type': 'buy',
                                'price': current_price,
                                'shares': position,
                                'value': position * current_price,
                                'cash': cash
                            })
                            logger.info(f"买入: 日期={current_date}, 价格={current_price:.2f}, 数量={position}, 剩余现金={cash:.2f}")
                
                # 如果有持仓，检查卖出信号
                elif position > 0:
                    should_sell, reason = self.check_sell_signal(df, i, buy_price, buy_date_idx)
                    if should_sell:
                        cash += position * current_price
                        profit = (current_price - buy_price) * position
                        profit_ratio = (current_price - buy_price) / buy_price * 100
                        trades.append({
                            'date': current_date,
                            'type': 'sell',
                            'price': current_price,
                            'shares': position,
                            'value': position * current_price,
                            'cash': cash,
                            'profit': profit,
                            'profit_ratio': profit_ratio,
                            'reason': reason
                        })
                        logger.info(f"卖出: 日期={current_date}, 价格={current_price:.2f}, 数量={position}, "
                                  f"利润={profit:.2f}, 收益率={profit_ratio:.2f}%, 原因={reason}")
                        position = 0
                        buy_price = 0
            
            # 计算回测结果
            results = self.analyze_performance(daily_values, trades)
            
            # 打印回测结果
            self.print_results(results)
            
            # 绘制回测结果图表
            self.plot_results(df, trades, daily_values)
            
            return results
            
        except Exception as e:
            logger.error(f"回测过程出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def analyze_performance(self, daily_values, trades):
        """分析回测结果"""
        try:
            if not daily_values or not trades:
                return None
                
            # 计算基本指标
            initial_value = daily_values[0]['value']
            final_value = daily_values[-1]['value']
            total_return = (final_value - initial_value) / initial_value * 100
            
            # 计算年化收益率
            days = (daily_values[-1]['date'] - daily_values[0]['date']).days
            annual_return = (1 + total_return / 100) ** (365 / days) - 1
            
            # 计算最大回撤
            max_drawdown = 0
            peak_value = daily_values[0]['value']
            for daily_value in daily_values:
                if daily_value['value'] > peak_value:
                    peak_value = daily_value['value']
                drawdown = (peak_value - daily_value['value']) / peak_value
                max_drawdown = max(max_drawdown, drawdown)
            
            # 计算夏普比率
            daily_returns = []
            for i in range(1, len(daily_values)):
                daily_return = (daily_values[i]['value'] - daily_values[i-1]['value']) / daily_values[i-1]['value']
                daily_returns.append(daily_return)
            
            if daily_returns:
                annual_volatility = np.std(daily_returns) * np.sqrt(252)
                risk_free_rate = 0.03  # 假设无风险利率为3%
                if annual_volatility != 0:
                    sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
                else:
                    sharpe_ratio = 0
            else:
                sharpe_ratio = 0
            
            # 计算胜率和盈亏比
            win_trades = [t for t in trades if t.get('type') == 'sell' and t.get('profit', 0) > 0]
            loss_trades = [t for t in trades if t.get('type') == 'sell' and t.get('profit', 0) <= 0]
            
            total_trades = len([t for t in trades if t.get('type') == 'sell'])
            win_rate = len(win_trades) / total_trades if total_trades > 0 else 0
            
            avg_win = np.mean([t['profit'] for t in win_trades]) if win_trades else 0
            avg_loss = abs(np.mean([t['profit'] for t in loss_trades])) if loss_trades else 0
            profit_factor = avg_win / avg_loss if avg_loss != 0 else 0
            
            return {
                'total_return': total_return,
                'annual_return': annual_return * 100,
                'max_drawdown': max_drawdown * 100,
                'sharpe_ratio': sharpe_ratio,
                'win_rate': win_rate * 100,
                'profit_factor': profit_factor,
                'total_trades': total_trades,
                'win_trades': len(win_trades),
                'loss_trades': len(loss_trades)
            }
            
        except Exception as e:
            logger.error(f"分析回测结果出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def print_results(self, results):
        """打印回测结果"""
        if results:
            logger.info("\n====== 回测结果 ======")
            logger.info(f"总收益率: {results['total_return']:.2f}%")
            logger.info(f"年化收益率: {results['annual_return']:.2f}%")
            logger.info(f"最大回撤: {results['max_drawdown']:.2f}%")
            logger.info(f"夏普比率: {results['sharpe_ratio']:.2f}")
            logger.info(f"胜率: {results['win_rate']:.2f}%")
            logger.info(f"盈亏比: {results['profit_factor']:.2f}")
            logger.info(f"总交易次数: {results['total_trades']}")
            logger.info(f"盈利交易次数: {results['win_trades']}")
            logger.info(f"亏损交易次数: {results['loss_trades']}")
            logger.info("=====================\n")
            
    def plot_results(self, df, trades, daily_values):
        """绘制回测结果图表"""
        try:
            # 创建图表
            fig = plt.figure(figsize=(15, 10))
            ax1 = plt.subplot(211)
            ax2 = plt.subplot(212)
            fig.suptitle(f'{self.stock_code} 回测结果 ({self.start_date} 至 {self.end_date})')
            
            # 绘制K线图
            dates = [d.to_pydatetime() for d in df.index]
            ax1.plot(dates, df['close'], label='收盘价', color='gray', alpha=0.5)
            ax1.plot(dates, df['MA_short'], label=f'MA{self.ma_short}', color='blue', alpha=0.5)
            ax1.plot(dates, df['MA_mid'], label=f'MA{self.ma_mid}', color='orange', alpha=0.5)
            ax1.plot(dates, df['MA_long'], label=f'MA{self.ma_long}', color='red', alpha=0.5)
            
            # 标记买卖点
            for trade in trades:
                if trade['type'] == 'buy':
                    ax1.scatter(trade['date'].to_pydatetime(), trade['price'], color='red', marker='^', s=100)
                else:
                    ax1.scatter(trade['date'].to_pydatetime(), trade['price'], color='green', marker='v', s=100)
            
            ax1.set_ylabel('价格')
            ax1.grid(True)
            ax1.legend()
            
            # 绘制资金曲线
            dates = [dv['date'].to_pydatetime() for dv in daily_values]
            values = [dv['value'] for dv in daily_values]
            ax2.plot(dates, values, label='资金曲线', color='blue')
            
            # 标记买卖点对应的资金变化
            for trade in trades:
                if trade['type'] == 'buy':
                    ax2.scatter(trade['date'].to_pydatetime(), trade['cash'] + trade['value'], color='red', marker='^', s=100)
                else:
                    ax2.scatter(trade['date'].to_pydatetime(), trade['cash'], color='green', marker='v', s=100)
            
            ax2.set_ylabel('资金')
            ax2.grid(True)
            ax2.legend()
            
            # 调整x轴显示
            plt.gcf().autofmt_xdate()
            
            # 保存图表
            plt.savefig('backtest_result.png')
            plt.close()
            
            logger.info("回测结果图表已保存为 backtest_result.png")
            
        except Exception as e:
            logger.error(f"绘制回测结果图表出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

def main():
    """主函数"""
    try:
        # 创建回测系统实例
        backtest = BacktestSystem()
        
        # 设置回测参数
        backtest.stock_code = "sz.300677"  # 银河磁体
        backtest.start_date = "2022-01-01"
        backtest.end_date = "2023-12-31"
        backtest.initial_capital = 100000
        
        # 运行回测
        results = backtest.run_backtest()
        
        if results is None:
            logger.error("回测失败")
            
    except Exception as e:
        logger.error(f"主程序运行出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 