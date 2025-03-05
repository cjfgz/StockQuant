import tushare as ts
import pandas as pd
import datetime
import json
import time


class 双双策略:
    def __init__(self):
        try:
            with open('docs/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.token = config.get('TUSHARE', {}).get('token')
                if not self.token:
                    raise ValueError("配置文件中未找到token")
        except Exception as e:
            print(f"读取配置文件失败: {str(e)}")
            raise

        # 初始化tushare
        ts.set_token(self.token)
        self.api = ts.pro_api()

        # 验证token
        if not self.verify_token():
            raise ValueError("Token验证失败，请检查token是否正确")

        # 策略参数
        self.initial_capital = 100000  # 初始资金10万
        self.position = 0  # 当前持仓
        self.cash = self.initial_capital  # 当前现金
        self.start_date = '20220101'
        self.end_date = '20231231'

    def verify_token(self):
        """验证token是否有效"""
        try:
            print("正在验证token...")
            # 尝试获取一个简单的数据来验证token
            test_data = self.api.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,name',
                limit=1
            )
            if not test_data.empty:
                print("Token验证成功！")
                return True
            else:
                print("Token验证失败：未能获取数据")
                return False
        except Exception as e:
            print(f"Token验证失败：{str(e)}")
            return False

    def get_stock_list(self):
        """获取股票列表（使用基础接口）"""
        try:
            # 获取所有A股列表
            stocks = self.api.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry'
            )
            return stocks
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_daily_data(self, ts_code, start_date, end_date):
        """获取日线数据（使用基础接口）"""
        try:
            # 使用基础接口获取日线数据
            df = ts.pro_bar(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                adj='qfq'  # 前复权
            )
            time.sleep(0.5)  # 添加延时避免频率限制
            return df
        except Exception as e:
            print(f"获取日线数据失败 {ts_code}: {e}")
            return pd.DataFrame()

    def check_double_condition(self, df):
        """检查双双条件"""
        if len(df) < 2:
            return False

        # 检查连续两天上涨
        if df.iloc[0]['pct_chg'] > 0 and df.iloc[1]['pct_chg'] > 0:
            # 检查成交量是否翻倍
            if df.iloc[0]['vol'] > df.iloc[1]['vol'] * 2:
                return True
        return False

    def run_backtest(self):
        """运行回测"""
        print("开始回测...")
        trades = []
        portfolio_values = []

        # 获取股票列表
        stocks = self.get_stock_list()
        if stocks.empty:
            print("获取股票列表失败")
            return

        print(f"共获取到 {len(stocks)} 只股票")

        # 按月遍历时间段
        current_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)

        while current_date <= end_date:
            month_start = current_date.strftime('%Y%m%d')
            current_date = current_date + pd.DateOffset(months=1)
            month_end = (current_date - pd.DateOffset(days=1)).strftime('%Y%m%d')

            print(f"正在处理 {month_start} 到 {month_end} 的数据...")

            # 遍历股票
            for _, stock in stocks.iterrows():
                if self.position > 0:  # 已有持仓则跳过
                    continue

                ts_code = stock['ts_code']
                df = self.get_daily_data(ts_code, month_start, month_end)

                if df.empty:
                    continue

                if self.check_double_condition(df):
                    # 获取最新价格
                    price = df.iloc[0]['close']
                    # 计算可买数量（使用50%资金）
                    shares = int((self.cash * 0.5) / (price * 100)) * 100
                    if shares > 0:
                        cost = shares * price
                        self.cash -= cost
                        self.position = shares
                        trades.append({
                            'date': df.iloc[0]['trade_date'],
                            'type': 'buy',
                            'ts_code': ts_code,
                            'price': price,
                            'shares': shares,
                            'cost': cost
                        })
                        print(f"买入: {ts_code} 价格: {price} 数量: {shares}")

                        # 5天后卖出
                        sell_date = df[df['trade_date'] > trades[-1]['date']].iloc[4:5]
                        if not sell_date.empty:
                            sell_price = sell_date.iloc[0]['close']
                            revenue = self.position * sell_price
                            self.cash += revenue
                            trades.append({
                                'date': sell_date.iloc[0]['trade_date'],
                                'type': 'sell',
                                'ts_code': ts_code,
                                'price': sell_price,
                                'shares': self.position,
                                'revenue': revenue
                            })
                            print(f"卖出: {ts_code} 价格: {sell_price} 数量: {self.position}")
                            self.position = 0

            # 记录每月底的组合价值
            portfolio_values.append({
                'date': month_end,
                'value': self.cash + (self.position * price if self.position > 0 else 0)
            })

        # 输出回测结果
        final_value = portfolio_values[-1]['value']
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100

        print("\n回测结果:")
        print(f"初始资金: {self.initial_capital:,.2f}")
        print(f"最终价值: {final_value:,.2f}")
        print(f"总收益率: {total_return:.2f}%")

        print("\n交易记录:")
        for trade in trades:
            if trade['type'] == 'buy':
                print(f"买入 - 日期:{trade['date']}, 代码:{trade['ts_code']}, "
                      f"价格:{trade['price']:.2f}, 数量:{trade['shares']}, "
                      f"成本:{trade['cost']:.2f}")
            else:
                print(f"卖出 - 日期:{trade['date']}, 代码:{trade['ts_code']}, "
                      f"价格:{trade['price']:.2f}, 数量:{trade['shares']}, "
                      f"收入:{trade['revenue']:.2f}")


if __name__ == "__main__":
    strategy = 双双策略()
    strategy.run_backtest()


