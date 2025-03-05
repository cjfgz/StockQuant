# -*- coding: utf-8 -*-
import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from stockquant.message import DingTalk
import atexit

class NorthMoneyStrategy:
    def __init__(self):
        # 初始化baostock
        self.bs = bs
        self.is_logged_in = False
        try:
            self.login_result = self.bs.login()
            if self.login_result.error_code == '0':
                self.is_logged_in = True
                print(f'登录baostock成功，结果：{self.login_result.error_code} {self.login_result.error_msg}')
            else:
                print(f'登录baostock失败：{self.login_result.error_msg}')
        except Exception as e:
            print(f"登录baostock时发生错误: {str(e)}")
        
        # 注册退出时的清理函数
        atexit.register(self.cleanup)
        
        # 初始化钉钉
        self.ding = DingTalk()
        
        # 策略参数
        self.north_increase_days = 5     # 北向连续增持天数
        self.min_increase_pct = 0.05     # 北向持股增幅阈值
        self.earnings_growth = 0.50      # 业绩预增最低幅度
        self.max_stocks = 20             # 最大持仓数
        self.stop_loss = -0.08          # 个股止损阈值
        
    def cleanup(self):
        """清理资源"""
        if self.is_logged_in:
            try:
                self.bs.logout()
                self.is_logged_in = False
                print("已安全登出 baostock")
            except:
                pass

    def get_hs300_stocks(self):
        """获取沪深300成分股"""
        if not self.is_logged_in:
            print("baostock未登录")
            return []
            
        rs = self.bs.query_hs300_stocks()
        if rs.error_code != '0':
            print(f'获取沪深300成分股失败: {rs.error_msg}')
            return []
            
        stocks = []
        while (rs.error_code == '0') & rs.next():
            stocks.append(rs.get_row_data()[1])  # 获取股票代码
        return stocks

    def get_stock_data(self, stock_code, days=30):
        """获取个股历史数据"""
        if not self.is_logged_in:
            print("baostock未登录")
            return None
            
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        rs = self.bs.query_history_k_data_plus(stock_code,
            "date,code,close,volume,amount,turn,peTTM",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3"
        )
        
        if rs.error_code != '0':
            print(f'获取股票{stock_code}数据失败: {rs.error_msg}')
            return None
            
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
            
        if not data_list:
            return None
            
        df = pd.DataFrame(data_list, columns=['date','code','close','volume','amount','turn','peTTM'])
        for col in ['close','volume','amount','turn','peTTM']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def analyze_stock(self, stock_code):
        """分析个股数据"""
        try:
            # 获取股票数据
            df = self.get_stock_data(stock_code)
            if df is None or len(df) < 20:  # 确保有足够的数据计算均线
                return None
                
            # 计算均线
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            
            # 获取最新和前一天的数据
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 1. 检查金叉（5日线上穿10日线）
            golden_cross = (prev['ma5'] <= prev['ma10']) and (latest['ma5'] > latest['ma10'])
            
            # 2. 检查成交量是否大于5日平均
            volume_check = latest['volume'] > latest['volume_ma5']
            
            # 3. 检查市盈率
            pe_check = pd.to_numeric(latest['peTTM']) < 50
            
            # 所有条件都满足才返回数据
            if golden_cross and volume_check and pe_check:
                return {
                    'code': stock_code,
                    'close': latest['close'],
                    'volume': latest['volume'],
                    'volume_ma5': latest['volume_ma5'],
                    'ma5': latest['ma5'],
                    'ma10': latest['ma10'],
                    'pe': latest['peTTM']
                }
            return None
            
        except Exception as e:
            print(f"分析股票 {stock_code} 时发生错误: {str(e)}")
            return None

    def send_result_message(self, selected_stocks):
        """发送选股结果到钉钉"""
        try:
            if not selected_stocks:
                message = f"""🔍 A股每日精选【选股策略】
--------------------------------
选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 选股条件：
1. 5日均线上穿10日均线（金叉）
2. 成交量大于5日平均成交量
3. 市盈率小于50

❌ 今日没有符合条件的股票
--------------------------------"""
            else:
                message = f"""🔍 A股每日精选【选股策略】
--------------------------------
选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 选股条件：
1. 5日均线上穿10日均线（金叉）
2. 成交量大于5日平均成交量
3. 市盈率小于50

✅ 共筛选出{len(selected_stocks)}只股票：
"""
                for stock in selected_stocks:
                    message += f"""
📌 {stock['code']}
   当前价格: {stock['close']:.2f}
   市盈率: {stock['pe']:.2f}
   5日均线: {stock['ma5']:.2f}
   10日均线: {stock['ma10']:.2f}
   成交量: {stock['volume']/10000:.2f}万
   5日均量: {stock['volume_ma5']/10000:.2f}万
--------------------------------"""
                
            self.ding.send_message(message)
            print("选股结果已推送到钉钉")
            
        except Exception as e:
            print(f"发送钉钉消息失败: {str(e)}")

    def run_strategy(self):
        """运行策略"""
        if not self.is_logged_in:
            print("baostock未登录，无法执行策略")
            return []
            
        print("开始运行选股策略...")
        
        try:
            # 获取沪深300成分股
            stocks = self.get_hs300_stocks()
            if not stocks:
                print("未获取到股票列表")
                return []
                
            print(f"获取到{len(stocks)}只沪深300成分股")
            
            # 分析每只股票
            selected_stocks = []
            for i, stock in enumerate(stocks):
                if not self.is_logged_in:
                    print("baostock连接已断开")
                    break
                    
                print(f"正在分析第{i+1}/{len(stocks)}只股票: {stock}")
                result = self.analyze_stock(stock)
                if result:
                    selected_stocks.append(result)
                time.sleep(0.5)  # 避免请求过快
                
            # 输出结果并推送
            print("\n=== 策略选股结果 ===")
            print(f"共筛选出{len(selected_stocks)}只符合条件的股票：")
            for stock in selected_stocks:
                print(f"""
股票代码：{stock['code']}
当前价格：{stock['close']:.2f}
市盈率：{stock['pe']:.2f}
5日均线：{stock['ma5']:.2f}
10日均线：{stock['ma10']:.2f}
成交量：{stock['volume']/10000:.2f}万
5日均量：{stock['volume_ma5']/10000:.2f}万
------------------------""")
            
            # 发送钉钉消息
            if selected_stocks:
                self.send_result_message(selected_stocks)
            
            return selected_stocks
            
        except Exception as e:
            print(f"策略运行出错: {str(e)}")
            return []
        finally:
            # 策略运行完成后登出
            self.cleanup()

if __name__ == '__main__':
    strategy = NorthMoneyStrategy()
    strategy.run_strategy()