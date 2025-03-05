import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tushare as ts
import seaborn as sns
from datetime import datetime

class MAStrategyBacktest:
    def __init__(self, stock_code, start_date='20210101', end_date='20220101',
                 short_ma=5, long_ma=20, initial_capital=1000000):
        """
        初始化回测参数

        参数:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        short_ma: 短期均线周期
        long_ma: 长期均线周期
        initial_capital: 初始资金
        """
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.initial_capital = initial_capital
        self.data = None
        self.positions = None
        self.portfolio = None

        # 交易成本设置
        self.commission_rate = 0.0003  # 手续费率
        self.slippage = 0.002  # 滑点

    def get_data(self):
        """获取股票数据并进行预处理"""
        try:
            # 设置token
            ts.set_token('b097f86043c6f0860d20de8978e988db375113f4250c6f263886d1a3')
            pro = ts.pro_api()

            # 获取日线数据
            df = pro.daily(ts_code=self.stock_code,
                         start_date=self.start_date,
                         end_date=self.end_date)

            if df is None or len(df) == 0:
                print(f"获取股票{self.stock_code}数据失败")
                return False

            # 按日期升序排序
            df = df.sort_values('trade_date')

            # 确保数据类型正确
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df = df.dropna(subset=['close'])

            if len(df) < max(self.short_ma, self.long_ma):
                print(f"数据量不足，至少需要{max(self.short_ma, self.long_ma)}个交易日")
                return False

            # 计算移动平均线
            df['short_ma'] = df['close'].rolling(window=self.short_ma).mean()
            df['long_ma'] = df['close'].rolling(window=self.long_ma).mean()

            # 计算日收益率
            df['returns'] = df['close'].pct_change()

            # 删除包含NaN的行
            df = df.dropna()

            if len(df) == 0:
                print("处理后的数据为空")
                return False

            self.data = df
            return True

        except Exception as e:
            print(f"获取数据失败: {str(e)}")
            return False

    def generate_signals(self):
        """生成交易信号"""
        try:
            # 计算金叉死叉信号
            self.data['signal'] = 0
            self.data.loc[self.data['short_ma'] > self.data['long_ma'], 'signal'] = 1
            self.data.loc[self.data['short_ma'] <= self.data['long_ma'], 'signal'] = 0

            # 计算仓位变化
            self.data['position_change'] = self.data['signal'].diff()

            return True

        except Exception as e:
            print(f"生成信号失败: {str(e)}")
            return False

    def calculate_portfolio(self):
        """计算投资组合表现"""
        try:
            # 创建投资组合DataFrame
            portfolio = pd.DataFrame(index=self.data.index)
            
            # 初始化持仓和现金
            portfolio['holdings'] = 0.0
            portfolio['cash'] = self.initial_capital
            portfolio['shares'] = 0  # 添加股票持有数量列
            
            # 遍历每个交易日
            for i, (idx, row) in enumerate(self.data.iterrows()):
                # 第一天特殊处理
                if i == 0:
                    # 如果第一天信号为1，买入
                    if row['signal'] == 1:
                        # 计算可买入的股票数量（假设整数股）
                        shares = int(portfolio.loc[idx, 'cash'] / row['close'])
                        cost = shares * row['close']
                        # 更新持仓和现金
                        portfolio.loc[idx, 'shares'] = shares
                        portfolio.loc[idx, 'holdings'] = shares * row['close']
                        portfolio.loc[idx, 'cash'] -= cost
                        # 减去交易成本
                        portfolio.loc[idx, 'cash'] -= cost * self.commission_rate
                else:
                    prev_idx = self.data.index[i-1]
                    # 默认继承前一天的持仓状态
                    portfolio.loc[idx, 'shares'] = portfolio.loc[prev_idx, 'shares']
                    portfolio.loc[idx, 'cash'] = portfolio.loc[prev_idx, 'cash']
                    
                    # 处理仓位变化
                    if row['position_change'] == 1:  # 买入信号
                        # 计算可买入的股票数量
                        shares = int(portfolio.loc[idx, 'cash'] / row['close'])
                        if shares > 0:
                            cost = shares * row['close']
                            # 更新持仓和现金
                            portfolio.loc[idx, 'shares'] += shares
                            portfolio.loc[idx, 'cash'] -= cost
                            # 减去交易成本
                            portfolio.loc[idx, 'cash'] -= cost * self.commission_rate
                    
                    elif row['position_change'] == -1:  # 卖出信号
                        if portfolio.loc[idx, 'shares'] > 0:
                            # 计算卖出收入
                            revenue = portfolio.loc[idx, 'shares'] * row['close']
                            # 更新持仓和现金
                            portfolio.loc[idx, 'shares'] = 0
                            portfolio.loc[idx, 'cash'] += revenue
                            # 减去交易成本
                            portfolio.loc[idx, 'cash'] -= revenue * self.commission_rate
                    
                    # 更新当日持仓市值
                    portfolio.loc[idx, 'holdings'] = portfolio.loc[idx, 'shares'] * row['close']
            
            # 计算总资产
            portfolio['total'] = portfolio['holdings'] + portfolio['cash']
            
            # 计算收益指标
            portfolio['returns'] = portfolio['total'].pct_change()
            portfolio['cum_returns'] = (1 + portfolio['returns']).fillna(1).cumprod()
            
            self.portfolio = portfolio
            return True
            
        except Exception as e:
            print(f"计算组合失败: {str(e)}")
            return False

        except Exception as e:
            print(f"计算组合失败: {str(e)}")
            return False

    def analyze_performance(self):
        """分析策略表现"""
        try:
            # 计算年化收益率
            days = len(self.portfolio)
            annual_return = (self.portfolio['cum_returns'].iloc[-1] - 1) * 252 / days

            # 计算夏普比率
            risk_free_rate = 0.03  # 假设无风险利率为3%
            excess_returns = self.portfolio['returns'] - risk_free_rate/252
            sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std()

            # 计算最大回撤
            cum_returns = self.portfolio['cum_returns']
            running_max = cum_returns.cummax()
            drawdown = (cum_returns - running_max) / running_max
            max_drawdown = drawdown.min()

            # 计算胜率
            winning_days = (self.portfolio['returns'] > 0).sum()
            win_rate = winning_days / len(self.portfolio)

            # 统计交易次数
            trades = len(self.data[self.data['position_change'] != 0])

            return {
                '初始资金': self.initial_capital,
                '结束资金': self.portfolio['total'].iloc[-1],
                '总收益率': (self.portfolio['total'].iloc[-1] / self.initial_capital - 1) * 100,
                '年化收益率': annual_return * 100,
                '夏普比率': sharpe_ratio,
                '最大回撤': max_drawdown * 100,
                '胜率': win_rate * 100,
                '交易次数': trades
            }

        except Exception as e:
            print(f"分析表现失败: {str(e)}")
            return None

    def plot_results(self):
        """绘制回测结果图表"""
        try:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 15))

            # 绘制价格和均线
            ax1.plot(self.data['trade_date'], self.data['close'], label='Price')
            ax1.plot(self.data['trade_date'], self.data['short_ma'], label=f'{self.short_ma}MA')
            ax1.plot(self.data['trade_date'], self.data['long_ma'], label=f'{self.long_ma}MA')

            # 标记买卖点
            buy_signals = self.data[self.data['position_change'] == 1]
            sell_signals = self.data[self.data['position_change'] == -1]

            ax1.scatter(buy_signals['trade_date'], buy_signals['close'],
                       marker='^', color='g', label='Buy', s=100)
            ax1.scatter(sell_signals['trade_date'], sell_signals['close'],
                       marker='v', color='r', label='Sell', s=100)

            ax1.set_title('股价走势与交易信号')
            ax1.legend()

            # 绘制资产变化
            ax2.plot(self.portfolio.index, self.portfolio['total'], label='总资产')
            ax2.plot(self.portfolio.index, self.portfolio['cash'], label='现金')
            ax2.set_title('资产变化')
            ax2.legend()

            # 绘制回撤
            cum_returns = self.portfolio['cum_returns']
            running_max = cum_returns.cummax()
            drawdown = (cum_returns - running_max) / running_max

            ax3.fill_between(self.portfolio.index, drawdown, 0, color='red', alpha=0.3)
            ax3.set_title('回撤')

            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"绘制图表失败: {str(e)}")

    def run_backtest(self):
        """运行回测"""
        print("开始回测...")

        if not self.get_data():
            return False

        if not self.generate_signals():
            return False

        if not self.calculate_portfolio():
            return False

        # 输出回测结果
        performance = self.analyze_performance()
        if performance:
            print("\n=== 回测结果 ===")
            for metric, value in performance.items():
                print(f"{metric}: {value:.2f}")

        # 绘制图表
        self.plot_results()

        return True

# 运行回测
if __name__ == "__main__":
    backtest = MAStrategyBacktest(
        stock_code='000001.SZ',  # 平安银行
        start_date='20210101',
        end_date='20220101',
        short_ma=5,
        long_ma=20,
        initial_capital=1000000  # 100万初始资金
    )

    backtest.run_backtest()
