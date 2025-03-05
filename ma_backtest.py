import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import os

class MABacktest:
    def __init__(self):
        # 从环境变量获取token，如果没有则使用默认值
        self.token = "b097f86043c6f0860d20de8978e988db375113f4250c6f263886d1a3"
        if not self.token:
            print("\n请设置Tushare token！")
            print("方法1 - 设置环境变量：")
            print("Windows命令行：set TUSHARE_TOKEN=你的token")
            print("PowerShell：$env:TUSHARE_TOKEN='你的token'")
            print("\n方法2 - 直接在代码中设置：")
            print("找到 self.token = os.getenv('TUSHARE_TOKEN') 这行")
            print("改为 self.token = '你的token'")
            self.token = 'b097f86043c6f0860d20de8978e988db375113f4250c6f263886d1a3'  # 请替换为您的实际token
            
        # 设置tushare token
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        
        # 回测参数
        self.start_date = '20220101'
        self.end_date = '20231231'
        self.initial_capital = 10000  # 初始资金
        self.security = '601318.SH'   # 中国平安
        
        self.setup_logging()
        
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
        
    def get_history_data(self):
        """获取历史数据"""
        try:
            # 获取日线数据
            df = self.pro.daily(ts_code=self.security, 
                              start_date=self.start_date,
                              end_date=self.end_date)
            
            # 按照日期正序排列
            df = df.sort_values('trade_date')
            
            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            
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
            cash = self.initial_capital  # 现金
            position = 0                 # 持仓数量
            trades = []                 # 交易记录
            
            # 遍历历史数据
            for i in range(20, len(df)):  # 从第20天开始，确保有足够数据计算均线
                date = df.iloc[i]['trade_date']
                current_price = df.iloc[i]['close']
                
                # 获取当前和前一天的均线数据
                current_ma5 = df.iloc[i]['MA5']
                current_ma10 = df.iloc[i]['MA10']
                current_ma20 = df.iloc[i]['MA20']
                prev_ma5 = df.iloc[i-1]['MA5']
                prev_ma10 = df.iloc[i-1]['MA10']
                
                # 检查买入信号：5日线上穿10日线，且20日线高于当前价格
                if prev_ma5 <= prev_ma10 and current_ma5 > current_ma10 and current_ma20 > current_price:
                    if cash > 0:
                        # 计算可买数量（向下取整到100的倍数）
                        shares = int(cash / current_price / 100) * 100
                        if shares >= 100:
                            cost = shares * current_price
                            cash -= cost
                            position += shares
                            trades.append({
                                'date': date,
                                'action': 'buy',
                                'price': current_price,
                                'shares': shares,
                                'cost': cost,
                                'cash': cash
                            })
                            self.logger.info(f"买入 - 日期: {date}, 价格: {current_price:.2f}, 数量: {shares}, 剩余现金: {cash:.2f}")
                
                # 检查卖出信号：5日线下穿10日线
                elif prev_ma5 >= prev_ma10 and current_ma5 < current_ma10:
                    if position > 0:
                        revenue = position * current_price
                        cash += revenue
                        trades.append({
                            'date': date,
                            'action': 'sell',
                            'price': current_price,
                            'shares': position,
                            'revenue': revenue,
                            'cash': cash
                        })
                        self.logger.info(f"卖出 - 日期: {date}, 价格: {current_price:.2f}, 数量: {position}, 现金: {cash:.2f}")
                        position = 0
            
            # 计算回测结果
            final_value = cash + (position * df.iloc[-1]['close'])
            total_return = (final_value - self.initial_capital) / self.initial_capital * 100
            
            # 输出回测结果
            self.logger.info("\n=== 回测结果 ===")
            self.logger.info(f"初始资金: {self.initial_capital:.2f}")
            self.logger.info(f"最终资金: {final_value:.2f}")
            self.logger.info(f"总收益率: {total_return:.2f}%")
            self.logger.info(f"总交易次数: {len(trades)}")
            
            # 记录每笔交易
            self.logger.info("\n=== 交易记录 ===")
            for trade in trades:
                if trade['action'] == 'buy':
                    self.logger.info(f"买入 - 日期: {trade['date']}, 价格: {trade['price']:.2f}, 数量: {trade['shares']}, 成本: {trade['cost']:.2f}")
                else:
                    self.logger.info(f"卖出 - 日期: {trade['date']}, 价格: {trade['price']:.2f}, 数量: {trade['shares']}, 收入: {trade['revenue']:.2f}")
            
            return trades, total_return
            
        except Exception as e:
            self.logger.error(f"回测执行出错: {str(e)}")
            return None, None

if __name__ == "__main__":
    backtest = MABacktest()
    backtest.run_backtest() 