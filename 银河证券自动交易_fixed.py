#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
import json
import easytrader
from datetime import datetime
import pandas as pd

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('yh_trader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class YHAutoTrader:
    def __init__(self):
        """初始化银河证券自动交易"""
        self.user = None
        self.config_file = 'yh_config.json'
        self.exe_path = None  # 客户端路径
        self.username = None  # 用户名
        self.password = None  # 密码
        self.comm_password = None  # 通讯密码
        
        # 交易参数
        self.stock_code = None  # 股票代码
        self.buy_price = 0  # 买入价格
        self.buy_amount = 0  # 买入数量
        self.sell_price = 0  # 卖出价格
        self.sell_amount = 0  # 卖出数量
        
        # 加载配置
        self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                self.exe_path = config.get('exe_path')
                self.username = config.get('username')
                self.password = config.get('password')
                self.comm_password = config.get('comm_password')
                
                logger.info("配置文件加载成功")
            else:
                logger.warning(f"配置文件 {self.config_file} 不存在，将使用默认配置")
                # 创建默认配置
                self.create_default_config()
        except Exception as e:
            logger.error(f"加载配置文件出错: {str(e)}")
            
    def create_default_config(self):
        """创建默认配置文件"""
        try:
            default_config = {
                "exe_path": "C:\\中国银河证券双子星3.2\\Binarystar.exe",
                "username": "你的账号",
                "password": "你的密码",
                "comm_password": "你的通讯密码"
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
                
            logger.info(f"已创建默认配置文件 {self.config_file}，请修改后再运行")
        except Exception as e:
            logger.error(f"创建默认配置文件出错: {str(e)}")
            
    def login(self):
        """登录银河证券客户端"""
        try:
            logger.info("开始登录银河证券客户端...")
            
            # 检查配置
            if not self.exe_path or not self.username or not self.password:
                logger.error("配置不完整，请检查配置文件")
                return False
                
            # 创建客户端
            self.user = easytrader.use('yh_client')
            
            # 登录
            self.user.login(
                user=self.username,
                password=self.password,
                exe_path=self.exe_path,
                comm_password=self.comm_password
            )
            
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def get_balance(self):
        """获取账户余额"""
        try:
            if not self.user:
                logger.error("尚未登录")
                return None
                
            balance = self.user.balance
            logger.info(f"账户余额: {balance}")
            return balance
        except Exception as e:
            logger.error(f"获取账户余额失败: {str(e)}")
            return None
            
    def get_position(self):
        """获取持仓"""
        try:
            if not self.user:
                logger.error("尚未登录")
                return None
                
            position = self.user.position
            logger.info(f"当前持仓: {position}")
            return position
        except Exception as e:
            logger.error(f"获取持仓失败: {str(e)}")
            return None
            
    def buy(self, stock_code, price, amount):
        """买入股票"""
        try:
            if not self.user:
                logger.error("尚未登录")
                return False
                
            logger.info(f"买入 {stock_code}, 价格: {price}, 数量: {amount}")
            result = self.user.buy(stock_code, price=price, amount=amount)
            logger.info(f"买入结果: {result}")
            return result
        except Exception as e:
            logger.error(f"买入失败: {str(e)}")
            return False
            
    def sell(self, stock_code, price, amount):
        """卖出股票"""
        try:
            if not self.user:
                logger.error("尚未登录")
                return False
                
            logger.info(f"卖出 {stock_code}, 价格: {price}, 数量: {amount}")
            result = self.user.sell(stock_code, price=price, amount=amount)
            logger.info(f"卖出结果: {result}")
            return result
        except Exception as e:
            logger.error(f"卖出失败: {str(e)}")
            return False
            
    def cancel_entrust(self, entrust_no):
        """撤销委托"""
        try:
            if not self.user:
                logger.error("尚未登录")
                return False
                
            logger.info(f"撤销委托 {entrust_no}")
            result = self.user.cancel_entrust(entrust_no)
            logger.info(f"撤销结果: {result}")
            return result
        except Exception as e:
            logger.error(f"撤销委托失败: {str(e)}")
            return False
            
    def get_today_entrusts(self):
        """获取今日委托"""
        try:
            if not self.user:
                logger.error("尚未登录")
                return None
                
            entrusts = self.user.today_entrusts
            logger.info(f"今日委托: {entrusts}")
            return entrusts
        except Exception as e:
            logger.error(f"获取今日委托失败: {str(e)}")
            return None
            
    def get_today_trades(self):
        """获取今日成交"""
        try:
            if not self.user:
                logger.error("尚未登录")
                return None
                
            trades = self.user.today_trades
            logger.info(f"今日成交: {trades}")
            return trades
        except Exception as e:
            logger.error(f"获取今日成交失败: {str(e)}")
            return None
            
    def run_demo(self):
        """运行演示"""
        try:
            logger.info("开始运行演示...")
            
            # 登录
            if not self.login():
                return
                
            # 获取账户余额
            balance = self.get_balance()
            if not balance:
                return
                
            # 获取持仓
            position = self.get_position()
            
            # 获取今日委托
            entrusts = self.get_today_entrusts()
            
            # 获取今日成交
            trades = self.get_today_trades()
            
            logger.info("演示完成")
        except Exception as e:
            logger.error(f"运行演示失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    def check_technical_conditions(self, stock_code):
        # 获取历史数据
        df = self.get_stock_data(stock_code)
        
        # 计算技术指标
        df = self.calculate_indicators(df)
        
        # 检查"一阳穿三线"条件
        if self.check_three_line_breakthrough(df):
            return True
            
        return False
    
    def check_three_line_breakthrough(self, df):
        """检查一阳穿三线条件"""
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # 今日是阳线
        is_yang = last_row['close'] > last_row['open']
        
        # 昨日收盘价低于三条均线
        below_three_lines_yesterday = (
            prev_row['close'] < prev_row['MA5'] and
            prev_row['close'] < prev_row['MA10'] and
            prev_row['close'] < prev_row['MA20']
        )
        
        # 今日收盘价高于三条均线
        above_three_lines_today = (
            last_row['close'] > last_row['MA5'] and
            last_row['close'] > last_row['MA10'] and
            last_row['close'] > last_row['MA20']
        )
        
        return is_yang and below_three_lines_yesterday and above_three_lines_today
            
    def backtest(self, stock_code, start_date, end_date, initial_capital=100000):
        """
        回测指定股票的交易策略
        
        参数:
        stock_code (str): 股票代码
        start_date (str): 开始日期，格式：YYYY-MM-DD
        end_date (str): 结束日期，格式：YYYY-MM-DD
        initial_capital (float): 初始资金
        
        返回:
        dict: 回测结果
        """
        logger.info(f"开始回测 {stock_code}，时间段: {start_date} 至 {end_date}")
        
        # 获取历史数据
        df = self.get_backtest_data(stock_code, start_date, end_date)
        if df is None or len(df) < 30:  # 确保有足够的数据
            logger.error("获取回测数据失败或数据不足")
            return None
        
        # 计算技术指标
        df = self.calculate_indicators(df)
        
        # 初始化回测变量
        cash = initial_capital  # 现金
        position = 0  # 持仓数量
        buy_price = 0  # 买入价格
        trades = []  # 交易记录
        
        # 模拟交易过程
        for i in range(20, len(df)):  # 从第20个交易日开始，确保有足够的历史数据计算指标
            date = df.index[i]
            current_price = df['close'].iloc[i]
            
            # 如果没有持仓，检查买入信号
            if position == 0:
                # 检查买入条件
                if self.check_buy_signal(df, i):
                    # 计算可买入数量（整百股）
                    shares = int(cash / current_price / 100) * 100
                    if shares >= 100:
                        cost = shares * current_price
                        cash -= cost
                        position = shares
                        buy_price = current_price
                        
                        # 记录交易
                        trades.append({
                            'date': date,
                            'action': 'buy',
                            'price': current_price,
                            'shares': shares,
                            'value': cost,
                            'cash': cash
                        })
                        
                        logger.info(f"回测买入: {date}, 价格: {current_price}, 数量: {shares}")
            
            # 如果有持仓，检查卖出信号
            elif position > 0:
                # 检查卖出条件
                if self.check_sell_signal(df, i, buy_price):
                    # 计算卖出收益
                    revenue = position * current_price
                    cash += revenue
                    
                    # 记录交易
                    trades.append({
                        'date': date,
                        'action': 'sell',
                        'price': current_price,
                        'shares': position,
                        'value': revenue,
                        'cash': cash,
                        'profit': (current_price / buy_price - 1) * 100  # 收益率(%)
                    })
                    
                    logger.info(f"回测卖出: {date}, 价格: {current_price}, 数量: {position}, 收益率: {(current_price / buy_price - 1) * 100:.2f}%")
                    
                    # 重置持仓
                    position = 0
                    buy_price = 0
        
        # 计算回测结果
        result = self.analyze_backtest_performance(df, trades, initial_capital)
        
        # 输出回测结果
        self.print_backtest_results(result)
        
        # 绘制回测图表
        self.plot_backtest_results(df, trades, result)
        
        return result

    def analyze_backtest_performance(self, df, trades, initial_capital):
        """分析回测性能"""
        if not trades:
            return {
                'total_return': 0,
                'annual_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'win_rate': 0,
                'profit_factor': 0
            }
        
        # 计算每日资产价值
        daily_value = []
        position = 0
        cash = initial_capital
        buy_price = 0
        
        for i, row in df.iterrows():
            # 检查是否有交易发生
            day_trades = [t for t in trades if t['date'] == i]
            
            for trade in day_trades:
                if trade['action'] == 'buy':
                    position = trade['shares']
                    cash = trade['cash']
                    buy_price = trade['price']
                elif trade['action'] == 'sell':
                    position = 0
                    cash = trade['cash']
            
            # 计算当日总资产
            total_value = cash + (position * row['close'])
            daily_value.append(total_value)
        
        # 转换为Series
        equity_curve = pd.Series(daily_value, index=df.index)
        
        # 计算收益率
        returns = equity_curve.pct_change().dropna()
        
        # 计算总收益率
        total_return = (equity_curve.iloc[-1] / initial_capital - 1) * 100
        
        # 计算年化收益率
        days = (df.index[-1] - df.index[0]).days
        annual_return = ((1 + total_return/100) ** (365/days) - 1) * 100 if days > 0 else 0
        
        # 计算最大回撤
        cumulative_max = equity_curve.cummax()
        drawdown = (equity_curve - cumulative_max) / cumulative_max * 100
        max_drawdown = abs(drawdown.min())
        
        # 计算夏普比率
        risk_free_rate = 0.03  # 假设无风险利率为3%
        sharpe_ratio = (annual_return/100 - risk_free_rate) / (returns.std() * (252**0.5)) if returns.std() > 0 else 0
        
        # 计算胜率
        profitable_trades = [t for t in trades if t['action'] == 'sell' and t['profit'] > 0]
        win_rate = len(profitable_trades) / len([t for t in trades if t['action'] == 'sell']) * 100 if trades else 0
        
        # 计算盈亏比
        avg_profit = sum([t['profit'] for t in profitable_trades]) / len(profitable_trades) if profitable_trades else 0
        losing_trades = [t for t in trades if t['action'] == 'sell' and t['profit'] <= 0]
        avg_loss = sum([t['profit'] for t in losing_trades]) / len(losing_trades) if losing_trades else 0
        profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'equity_curve': equity_curve,
            'trades_count': len([t for t in trades if t['action'] == 'sell']),
            'avg_holding_days': 0  # 需要计算平均持仓天数
        }

    def get_backtest_data(self, stock_code, start_date, end_date):
        """
        获取回测所需的历史数据
        
        参数:
        stock_code (str): 股票代码
        start_date (str): 开始日期，格式：YYYY-MM-DD
        end_date (str): 结束日期，格式：YYYY-MM-DD
        
        返回:
        DataFrame: 包含OHLCV数据的DataFrame
        """
        try:
            logger.info(f"获取 {stock_code} 从 {start_date} 到 {end_date} 的历史数据")
            
            # 导入baostock库
            import baostock as bs
            import pandas as pd
            from datetime import datetime
            
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
        """
        计算技术指标
        
        参数:
        df (DataFrame): 包含OHLCV数据的DataFrame
        
        返回:
        DataFrame: 添加了技术指标的DataFrame
        """
        try:
            # 计算移动平均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            
            # 计算成交量均线
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma10'] = df['volume'].rolling(window=10).mean()
            
            # 计算MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
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
            
            return df
            
        except Exception as e:
            logger.error(f"计算技术指标出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df

    def check_buy_signal(self, df, i):
        """检查买入信号"""
        # 获取当前和前一个交易日的数据
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 检查"一阳穿三线"条件
        is_yang = current['close'] > current['open']  # 是否为阳线
        
        # 昨日收盘价低于三条均线
        below_three_lines_yesterday = (
            prev['close'] < prev['MA5'] and
            prev['close'] < prev['MA10'] and
            prev['close'] < prev['MA20']
        )
        
        # 今日收盘价高于三条均线
        above_three_lines_today = (
            current['close'] > current['MA5'] and
            current['close'] > current['MA10'] and
            current['close'] > current['MA20']
        )
        
        # 一阳穿三线
        three_line_breakthrough = is_yang and below_three_lines_yesterday and above_three_lines_today
        
        # 均线金叉
        golden_cross = (prev['MA5'] <= prev['MA10']) and (current['MA5'] > current['MA10'])
        
        # 成交量放大
        volume_increase = current['volume'] > current['volume_ma5'] * 1.2
        
        # 综合买入信号
        return three_line_breakthrough or (golden_cross and volume_increase)

    def check_sell_signal(self, df, i, buy_price):
        """检查卖出信号"""
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 均线死叉
        death_cross = (prev['MA5'] >= prev['MA10']) and (current['MA5'] < current['MA10'])
        
        # 价格跌破20日线
        below_ma20 = current['close'] < current['MA20']
        
        # 止损（亏损超过5%）
        stop_loss = current['close'] <= buy_price * 0.95
        
        # 止盈（盈利超过20%）
        take_profit = current['close'] >= buy_price * 1.2
        
        # 综合卖出信号
        return death_cross or (below_ma20 and death_cross) or stop_loss or take_profit

    def print_backtest_results(self, result):
        """打印回测结果"""
        logger.info("=" * 50)
        logger.info("回测结果:")
        logger.info(f"总收益率: {result['total_return']:.2f}%")
        logger.info(f"年化收益率: {result['annual_return']:.2f}%")
        logger.info(f"最大回撤: {result['max_drawdown']:.2f}%")
        logger.info(f"夏普比率: {result['sharpe_ratio']:.2f}")
        logger.info(f"胜率: {result['win_rate']:.2f}%")
        logger.info(f"盈亏比: {result['profit_factor']:.2f}")
        logger.info(f"交易次数: {result['trades_count']}")
        logger.info("=" * 50)

    def plot_backtest_results(self, df, trades, result):
        """绘制回测结果图表"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
            
            # 绘制价格和均线
            ax1.plot(df.index, df['close'], label='价格')
            ax1.plot(df.index, df['MA5'], label='MA5')
            ax1.plot(df.index, df['MA10'], label='MA10')
            ax1.plot(df.index, df['MA20'], label='MA20')
            
            # 标记买入和卖出点
            buy_dates = [t['date'] for t in trades if t['action'] == 'buy']
            buy_prices = [t['price'] for t in trades if t['action'] == 'buy']
            sell_dates = [t['date'] for t in trades if t['action'] == 'sell']
            sell_prices = [t['price'] for t in trades if t['action'] == 'sell']
            
            ax1.scatter(buy_dates, buy_prices, marker='^', color='red', s=100, label='买入')
            ax1.scatter(sell_dates, sell_prices, marker='v', color='green', s=100, label='卖出')
            
            # 设置图表格式
            ax1.set_title('回测结果 - 价格和交易点')
            ax1.set_ylabel('价格')
            ax1.legend()
            ax1.grid(True)
            
            # 绘制资金曲线
            ax2.plot(result['equity_curve'].index, result['equity_curve'], label='资金曲线')
            ax2.set_title('资金曲线')
            ax2.set_xlabel('日期')
            ax2.set_ylabel('资金')
            ax2.legend()
            ax2.grid(True)
            
            # 格式化日期
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            # 旋转日期标签
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表
            plt.savefig('backtest_result.png')
            logger.info("回测结果图表已保存为 backtest_result.png")
            
            # 显示图表
            plt.show()
            
        except Exception as e:
            logger.error(f"绘制回测结果图表失败: {str(e)}")

def main():
    """主函数"""
    try:
        logger.info("银河证券自动交易系统启动...")
        
        trader = YHAutoTrader()
        
        # 运行回测
        stock_code = "sh.600000"  # 浦发银行
        start_date = "2022-01-01"
        end_date = "2022-12-31"
        trader.backtest(stock_code, start_date, end_date)
        
        # 运行演示
        # trader.run_demo()
        
        logger.info("银河证券自动交易系统退出")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
if __name__ == "__main__":
    main() 