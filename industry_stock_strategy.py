import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from stockquant.message import DingTalk
import logging

class IndustryStockStrategy:
    def __init__(self):
        # 初始化市场接口
        self.setup_logging()
        self.connect_baostock()
        self.ding = DingTalk()
        self.setup_params()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('industry_strategy.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def connect_baostock(self):
        """连接BaoStock"""
        self.logger.info("正在连接BaoStock...")
        retry_count = 0
        while retry_count < 3:
            try:
                bs.login()
                self.logger.info("BaoStock连接成功")
                return True
            except Exception as e:
                retry_count += 1
                self.logger.error(f"BaoStock连接失败(第{retry_count}次): {str(e)}")
                time.sleep(1)
        return False
        
    def setup_params(self):
        """设置策略参数"""
        # 行业选择参数
        self.industry_money_flow_days = 5  # 资金流向统计天数
        self.industry_min_stocks = 10      # 行业最小股票数
        self.top_industries = 5            # 选择前N个行业
        
        # 个股选择参数
        self.pe_range = (0, 50)           # PE范围
        self.pb_range = (0, 10)           # PB范围
        self.roe_min = 8                  # ROE最小值(%)
        self.market_cap_range = (50, 5000) # 市值范围（亿）
        self.max_stocks_per_industry = 3   # 每个行业最多选择的股票数
        
    def get_industry_list(self):
        """获取行业列表"""
        try:
            rs = bs.query_stock_industry()
            if rs.error_code != '0':
                self.logger.error(f"获取行业列表失败: {rs.error_msg}")
                return []
                
            industries = {}
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                industry_name = row[3]  # 使用证监会行业分类
                if industry_name and industry_name not in industries:
                    industries[industry_name] = {
                        'name': industry_name,
                        'code': industry_name  # 使用行业名称作为代码
                    }
            
            industry_list = list(industries.values())
            self.logger.info(f"成功获取{len(industry_list)}个行业")
            return industry_list
            
        except Exception as e:
            self.logger.error(f"获取行业列表失败: {str(e)}")
            return []
            
    def get_industry_stocks(self, industry_name):
        """获取行业成分股"""
        try:
            rs = bs.query_stock_industry()
            industry_stocks = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                if row[3] == industry_name:
                    code = row[1]
                    # 处理股票代码格式
                    if code.startswith('6'):
                        code = f'sh.{code}'
                    elif code.startswith(('0', '3')):
                        code = f'sz.{code}'
                    else:
                        continue
                    industry_stocks.append(code)
            return industry_stocks
        except Exception as e:
            self.logger.error(f"获取行业{industry_name}成分股失败: {str(e)}")
            return []
            
    def analyze_industry(self, industry):
        """分析行业数据"""
        try:
            stocks = self.get_industry_stocks(industry['name'])
            if len(stocks) < self.industry_min_stocks:
                self.logger.info(f"行业{industry['name']}股票数量{len(stocks)}小于最小要求{self.industry_min_stocks}")
                return None
                
            # 1. 计算行业资金流向
            total_amount = 0
            rising_count = 0
            total_pe = 0
            valid_stocks = 0
            
            for stock in stocks:
                try:
                    # 获取个股数据
                    rs = bs.query_history_k_data_plus(
                        stock,
                        "date,close,volume,amount,peTTM",
                        start_date=(datetime.now() - timedelta(days=self.industry_money_flow_days)).strftime('%Y-%m-%d'),
                        end_date=datetime.now().strftime('%Y-%m-%d'),
                        frequency="d",
                        adjustflag="3"  # 使用后复权
                    )
                    
                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())
                        
                    if data_list:
                        df = pd.DataFrame(data_list, columns=['date','close','volume','amount','peTTM'])
                        df['close'] = pd.to_numeric(df['close'])
                        df['amount'] = pd.to_numeric(df['amount'])
                        df['peTTM'] = pd.to_numeric(df['peTTM'])
                        
                        # 计算涨跌
                        if len(df) >= 2:
                            if df['close'].iloc[-1] > df['close'].iloc[0]:
                                rising_count += 1
                                
                        # 累计成交额
                        total_amount += df['amount'].sum()
                        
                        # 计算PE
                        latest_pe = df['peTTM'].iloc[-1]
                        if not pd.isna(latest_pe) and latest_pe > 0:
                            total_pe += latest_pe
                            valid_stocks += 1
                            
                except Exception as e:
                    self.logger.error(f"处理股票{stock}数据时出错: {str(e)}")
                    continue
                    
            if valid_stocks == 0:
                self.logger.info(f"行业{industry['name']}没有有效的PE数据")
                return None
                
            # 计算行业指标
            avg_pe = total_pe / valid_stocks
            rising_ratio = rising_count / len(stocks)
            
            # 行业评分（加权）
            score = (
                0.4 * total_amount +  # 资金流向权重40%
                0.3 * rising_ratio +  # 上涨家数权重30%
                0.2 * (1 / avg_pe if avg_pe > 0 else 0) +  # PE估值权重20%
                0.1 * len(stocks)     # 行业规模权重10%
            )
            
            return {
                'code': industry['code'],
                'name': industry['name'],
                'score': score,
                'stocks': stocks,
                'rising_ratio': rising_ratio,
                'avg_pe': avg_pe,
                'total_amount': total_amount
            }
            
        except Exception as e:
            self.logger.error(f"分析行业{industry['name']}时出错: {str(e)}")
            return None
            
    def select_industries(self):
        """选择优质行业"""
        try:
            self.logger.info("开始选择优质行业...")
            industries = self.get_industry_list()
            
            # 分析所有行业
            industry_scores = []
            for industry in industries:
                self.logger.info(f"正在分析行业：{industry['name']}")
                result = self.analyze_industry(industry)
                if result:
                    industry_scores.append(result)
                time.sleep(0.5)  # 避免请求过快
                
            # 按得分排序
            industry_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # 返回得分最高的N个行业
            return industry_scores[:self.top_industries]
            
        except Exception as e:
            self.logger.error(f"选择行业时出错: {str(e)}")
            return []
            
    def select_stocks(self, industry):
        """在行业中选择优质股票"""
        try:
            selected_stocks = []
            
            for stock in industry['stocks']:
                try:
                    # 获取个股数据
                    rs = bs.query_history_k_data_plus(
                        stock,
                        "date,code,close,volume,amount,turn,peTTM,pbMRQ",
                        start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        end_date=datetime.now().strftime('%Y-%m-%d'),
                        frequency="d"
                    )
                    
                    data_list = []
                    while (rs.error_code == '0') & rs.next():
                        data_list.append(rs.get_row_data())
                        
                    if not data_list:
                        continue
                        
                    df = pd.DataFrame(data_list, columns=['date','code','close','volume','amount','turn','peTTM','pbMRQ'])
                    for col in ['close','volume','amount','turn','peTTM','pbMRQ']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                    latest = df.iloc[-1]
                    
                    # 检查条件
                    pe_check = self.pe_range[0] <= float(latest['peTTM']) <= self.pe_range[1]
                    pb_check = self.pb_range[0] <= float(latest['pbMRQ']) <= self.pb_range[1]
                    
                    if pe_check and pb_check:
                        selected_stocks.append({
                            'code': stock,
                            'pe': latest['peTTM'],
                            'pb': latest['pbMRQ'],
                            'close': latest['close'],
                            'amount': latest['amount']
                        })
                        
                except Exception as e:
                    self.logger.error(f"分析股票{stock}时出错: {str(e)}")
                    continue
                    
            # 按成交额排序，选择前N只
            selected_stocks.sort(key=lambda x: x['amount'], reverse=True)
            return selected_stocks[:self.max_stocks_per_industry]
            
        except Exception as e:
            self.logger.error(f"选择行业{industry['name']}的股票时出错: {str(e)}")
            return []
            
    def format_result_message(self, industries, stocks_by_industry):
        """格式化结果消息"""
        message = f"""🔍 A股每日精选【行业优选+个股精选】
--------------------------------
选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 选股条件：
行业层面：
1. 政策导向看好
2. 资金流向强势
3. 技术面信号良好
4. 行业基本面健康

个股层面：
1. PE范围：{self.pe_range[0]}-{self.pe_range[1]}
2. PB范围：{self.pb_range[0]}-{self.pb_range[1]}
3. ROE不低于：{self.roe_min}%
4. 市值范围：{self.market_cap_range[0]}-{self.market_cap_range[1]}亿

🏆 选股结果：
"""
        for industry in industries:
            message += f"""
📌 {industry['name']}
上涨家数占比：{industry['rising_ratio']:.1%}
行业平均PE：{industry['avg_pe']:.2f}
5日成交额：{industry['total_amount']/100000000:.2f}亿

🔥 入选个股："""
            
            stocks = stocks_by_industry.get(industry['code'], [])
            for stock in stocks:
                message += f"""
   {stock['code']}
   当前价格：{stock['close']:.2f}
   市盈率：{stock['pe']:.2f}
   市净率：{stock['pb']:.2f}
"""
            message += "--------------------------------\n"
            
        return message
        
    def run(self):
        """运行策略"""
        try:
            self.logger.info("开始运行行业优选+个股精选策略...")
            
            # 1. 选择优质行业
            selected_industries = self.select_industries()
            if not selected_industries:
                self.logger.error("未能选出符合条件的行业")
                return
                
            # 2. 在每个行业中选择优质个股
            stocks_by_industry = {}
            for industry in selected_industries:
                stocks = self.select_stocks(industry)
                if stocks:
                    stocks_by_industry[industry['code']] = stocks
                    
            # 3. 发送结果
            if stocks_by_industry:
                message = self.format_result_message(selected_industries, stocks_by_industry)
                self.ding.send_message(message)
                self.logger.info("选股结果已推送到钉钉")
            else:
                self.logger.warning("未找到符合条件的股票")
                
        except Exception as e:
            self.logger.error(f"策略运行出错: {str(e)}")
            
    def __del__(self):
        """析构函数，确保退出时登出BaoStock"""
        try:
            bs.logout()
        except:
            pass

if __name__ == "__main__":
    strategy = IndustryStockStrategy()
    strategy.run() 