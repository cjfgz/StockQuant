import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from stockquant.message import DingTalk
import matplotlib.pyplot as plt
import mplfinance as mpf

class MAStrategy:
    def __init__(self):
        self.setup_logging()
        
        # 设置交易标的
        self.security = 'sh.601318'  # 中国平安
        self.start_date = '2021-01-01'
        self.end_date = '2022-12-31'
        
        # 资金管理
        self.initial_capital = 1000000  # 初始资金100万
        self.position = 0   # 持仓数量
        self.cash = self.initial_capital  # 当前现金
        
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
                logging.FileHandler('ma_backtest.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_history_data(self):
        """获取历史数据"""
        try:
            # 获取日K线数据
            rs = bs.query_history_k_data_plus(
                self.security,
                "date,code,open,high,low,close,volume,amount",
                start_date=self.start_date,
                end_date=self.end_date,
                frequency="d",
                adjustflag="3"  # 后复权
            )
            
            if rs.error_code != '0':
                self.logger.error(f"获取历史数据失败: {rs.error_msg}")
                return None
                
            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df['close'] = df['close'].astype(float)
            
            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取历史数据出错: {str(e)}")
            return None
            
    def run_backtest(self):
        """执行回测"""
        try:
            # 获取历史数据
            df = self.get_history_data()
            if df is None:
                return
                
            # 初始化回测变量
            trades = []  # 交易记录
            
            # 遍历历史数据
            for i in range(10, len(df)):  # 从第10天开始，确保有足够数据计算均线
                date = df.iloc[i]['date']
                current_price = float(df.iloc[i]['close'])
                
                # 计算当前和前一天的均线值
                ma5 = df.iloc[i]['MA5']
                ma5_prev = df.iloc[i-1]['MA5']
                ma10 = df.iloc[i]['MA10']
                ma10_prev = df.iloc[i-1]['MA10']
                
                # 买入信号：5日线上穿10日线
                if ma5 > ma10 and ma5_prev <= ma10_prev and self.cash > 0:
                    # 计算可买数量
                    shares = int(self.cash / current_price / 100) * 100
                    if shares >= 100:
                        cost = shares * current_price
                        self.cash -= cost
                        self.position += shares
                        trades.append({
                            'date': date,
                            'type': 'buy',
                            'price': current_price,
                            'shares': shares,
                            'cost': cost
                        })
                        self.logger.info(f"买入 {shares} 股，价格 {current_price:.2f}，花费 {cost:.2f}")
                
                # 卖出信号：5日线下穿10日线
                elif ma5 < ma10 and ma5_prev >= ma10_prev and self.position > 0:
                    revenue = self.position * current_price
                    self.cash += revenue
                    trades.append({
                        'date': date,
                        'type': 'sell',
                        'price': current_price,
                        'shares': self.position,
                        'revenue': revenue
                    })
                    self.logger.info(f"卖出 {self.position} 股，价格 {current_price:.2f}，收入 {revenue:.2f}")
                    self.position = 0
            
            # 计算回测结果
            final_value = self.cash + (self.position * current_price if self.position > 0 else 0)
            total_return = (final_value - self.initial_capital) / self.initial_capital * 100
            
            self.logger.info(f"""
回测结果：
初始资金：{self.initial_capital:,.2f}
最终价值：{final_value:,.2f}
总收益率：{total_return:.2f}%
交易次数：{len(trades)}
""")
            
            # 绘制交易图表
            self.plot_trades(df, trades)
            
        except Exception as e:
            self.logger.error(f"回测执行出错: {str(e)}")
            
    def plot_trades(self, df, trades):
        """绘制交易图表"""
        try:
            # 创建图表
            plt.figure(figsize=(15, 8))
            
            # 绘制收盘价和均线
            plt.plot(df.index, df['close'], label='Close Price', alpha=0.6)
            plt.plot(df.index, df['MA5'], label='MA5', alpha=0.7)
            plt.plot(df.index, df['MA10'], label='MA10', alpha=0.7)
            
            # 标记买入点
            buy_points = [i for i, trade in enumerate(trades) if trade['type'] == 'buy']
            buy_prices = [trade['price'] for trade in trades if trade['type'] == 'buy']
            plt.scatter(buy_points, buy_prices, marker='^', color='red', s=100, label='Buy')
            
            # 标记卖出点
            sell_points = [i for i, trade in enumerate(trades) if trade['type'] == 'sell']
            sell_prices = [trade['price'] for trade in trades if trade['type'] == 'sell']
            plt.scatter(sell_points, sell_prices, marker='v', color='green', s=100, label='Sell')
            
            # 设置图表
            plt.title('双均线策略回测结果')
            plt.xlabel('交易日')
            plt.ylabel('价格')
            plt.legend()
            plt.grid(True)
            
            # 保存图表
            plt.savefig('backtest_result.png')
            plt.close()
            
            self.logger.info("交易图表已保存为 backtest_result.png")
            
        except Exception as e:
            self.logger.error(f"绘制图表出错: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"回测执行出错: {str(e)}")

if __name__ == '__main__':
    strategy = MAStrategy()
    strategy.run_backtest()

