import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from stockquant.message import DingTalk
import json

class TechnicalStrategy:
    def __init__(self):
        """初始化策略"""
        self.setup_logging()
        self.connect_apis()
        self.setup_params()
        self.ding = DingTalk()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('technical_strategy.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def connect_apis(self):
        """连接APIs"""
        try:
            # 连接BaoStock
            bs_result = bs.login()
            if bs_result.error_code != '0':
                self.logger.error(f"BaoStock连接失败: {bs_result.error_msg}")
                raise Exception("BaoStock连接失败")
            self.logger.info("BaoStock连接成功")
        except Exception as e:
            self.logger.error(f"连接失败: {str(e)}")
            raise
            
    def setup_params(self):
        """设置策略参数"""
        self.pe_range = (0, 50)           # PE范围
        self.volume_days = 10             # 成交量统计天数
        self.ma_short = 5                 # 短期均线
        self.ma_long = 10                 # 长期均线
        self.volume_ratio = 1.5           # 成交量放大倍数
        
    def get_stock_list(self):
        """获取股票列表"""
        try:
            # 获取沪深300成分股
            rs = bs.query_hs300_stocks()
            if rs.error_code != '0':
                self.logger.error(f"获取沪深300成分股失败: {rs.error_msg}")
                return []
                
            stocks = []
            while (rs.error_code == '0') & rs.next():
                stocks.append(rs.get_row_data()[1])
            return stocks
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return []
            
    def get_stock_data(self, stock_code):
        """获取股票数据"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                stock_code,
                "date,code,close,volume,amount,peTTM",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                if all(field.strip() for field in row):
                    data_list.append(row)
                    
            if not data_list:
                return None
                
            df = pd.DataFrame(data_list, columns=['date', 'code', 'close', 'volume', 'amount', 'peTTM'])
            for col in ['close', 'volume', 'amount', 'peTTM']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            df = df.dropna()
            return df if not df.empty else None
            
        except Exception as e:
            self.logger.error(f"获取股票{stock_code}数据失败: {str(e)}")
            return None

    def check_stock_conditions(self, stock_code, df):
        """检查股票是否满足所有条件"""
        try:
            if df is None or len(df) < 20:  # 确保有足够的数据计算指标
                return False, {}
                
            # 计算技术指标
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 1. 检查均线金叉
            golden_cross = (prev['MA5'] <= prev['MA10']) and (latest['MA5'] > latest['MA10'])
            
            # 2. 检查成交量放大
            volume_increase = latest['volume'] > latest['volume_ma5'] * self.volume_ratio
            
            # 3. 检查PE是否在合理范围内
            pe_reasonable = self.pe_range[0] <= float(latest['peTTM']) <= self.pe_range[1]
            
            if golden_cross and volume_increase and pe_reasonable:
                return True, {
                    'code': stock_code,
                    'price': latest['close'],
                    'volume': latest['volume'],
                    'volume_ma5': latest['volume_ma5'],
                    'pe': latest['peTTM'],
                    'ma5': latest['MA5'],
                    'ma10': latest['MA10']
                }
            return False, {}
            
        except Exception as e:
            self.logger.error(f"检查股票{stock_code}条件时出错: {str(e)}")
            return False, {}

    def run(self):
        """运行策略"""
        try:
            self.logger.info("开始运行技术面选股策略...")
            
            # 获取股票列表
            stocks = self.get_stock_list()
            if not stocks:
                self.logger.error("获取股票列表失败")
                return
                
            # 分析每只股票
            selected_stocks = []
            for stock in stocks:
                try:
                    df = self.get_stock_data(stock)
                    passed, stock_info = self.check_stock_conditions(stock, df)
                    if passed:
                        selected_stocks.append(stock_info)
                except Exception as e:
                    self.logger.error(f"处理股票{stock}时出错: {str(e)}")
                    continue
                    
            # 发送结果
            if selected_stocks:
                message = f"""股票交易提醒 - 技术面选股策略
--------------------------------
⏰ 选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 选股条件：
1. 沪深300成分股
2. PE在{self.pe_range[0]}-{self.pe_range[1]}之间
3. 5日均线上穿10日均线（金叉）
4. 成交量大于5日均量{self.volume_ratio}倍

✅ 选股结果（共{len(selected_stocks)}只）：
"""
                for stock in selected_stocks:
                    message += f"""\n📌 {stock['code']}
   价格: {stock['price']:.2f}
   成交量: {stock['volume']/10000:.2f}万
   5日均量: {stock['volume_ma5']/10000:.2f}万
   PE: {stock['pe']:.2f}
   MA5: {stock['ma5']:.2f}
   MA10: {stock['ma10']:.2f}"""
                    
                message += "\n--------------------------------"
                self.ding.send_message(message)
                self.logger.info("选股结果已推送到钉钉")
            else:
                self.logger.warning("没有找到符合条件的股票")
                
        except Exception as e:
            self.logger.error(f"策略运行失败: {str(e)}")
        finally:
            bs.logout()

if __name__ == "__main__":
    strategy = TechnicalStrategy()
    strategy.run()