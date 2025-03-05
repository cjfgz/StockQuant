import baostock as bs
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from stockquant.message import DingTalk
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import math
import time

class ValueFactorStrategy:
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 读取配置文件
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                # 设置tushare token
                ts.set_token(self.config.get('tushare_token'))
                self.pro = ts.pro_api()
        except FileNotFoundError:
            self.logger.error("未找到config.json文件")
            raise
            
        # 连接baostock
        result = bs.login()
        if result.error_code != '0':
            self.logger.error(f"登录BaoStock失败: {result.error_msg}")
            raise Exception("BaoStock登录失败")
        else:
            self.logger.info("BaoStock登录成功")
            
        # 初始化钉钉
        try:
            self.ding = DingTalk()
            # 测试钉钉连接
            if self.config.get('dingtalk_webhook'):
                test_message = "钉钉机器人连接测试"
                self.send_dingtalk_message(test_message)
                self.logger.info("钉钉机器人连接测试成功")
            else:
                self.logger.warning("未配置钉钉webhook，将不会发送通知")
        except Exception as e:
            self.logger.error(f"钉钉初始化失败: {str(e)}")
        
        # 设置选股参数
        self.pe_range = (0, 30)  # PE范围
        self.pb_range = (0, 3)   # PB范围
        self.min_roe = 8         # 最小ROE
        self.market_cap_range = (50, 2000)  # 市值范围（亿）
        
        # 多线程相关
        self.max_workers = 10  # 最大线程数
        self.progress_lock = Lock()  # 用于进度更新的锁
        self.progress = 0  # 处理进度
        self.total_stocks = 0  # 股票总数
        
        # 添加重试机制
        self.max_retries = 3
        self.retry_delay = 1  # 秒
        
    def __del__(self):
        """析构函数，确保退出时登出"""
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
                logging.FileHandler('value_factor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
    def get_stock_list(self):
        """获取股票列表"""
        try:
            # 首先尝试使用tushare获取
            for retry in range(self.max_retries):
                try:
                    df = self.pro.stock_basic(
                        exchange='',
                        list_status='L',
                        fields='ts_code,symbol,name,industry'
                    )
                    if not df.empty:
                        # 转换tushare代码为baostock格式
                        df['code'] = df.apply(lambda row: 
                            f"sh.{row['ts_code'].split('.')[0]}" if row['ts_code'].endswith('SH') 
                            else f"sz.{row['ts_code'].split('.')[0]}", axis=1)
                        df['name'] = df['name'].astype(str)  # 确保name列为字符串类型
                        df['industry'] = df['industry'].astype(str)  # 确保industry列为字符串类型
                        return df[['code', 'name', 'industry']]  # 只保留需要的列
                except Exception as e:
                    self.logger.warning(f"Tushare获取股票列表失败，尝试使用BaoStock: {str(e)}")
                    time.sleep(self.retry_delay)
            
            # 如果tushare失败，使用baostock作为备选
            rs = bs.query_stock_basic()
            if rs.error_code != '0':
                self.logger.error(f"获取股票列表失败: {rs.error_msg}")
                return None
                
            data_list = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                # 只选择A股
                if row[0].startswith('sh.6') or row[0].startswith('sz.0') or row[0].startswith('sz.3'):
                    data_list.append({
                        'code': row[0],
                        'name': row[1],
                        'industry': row[16] if len(row) > 16 else ''
                    })
                
            df = pd.DataFrame(data_list)
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return None
            
    def get_fundamental_data_batch(self, stock_codes):
        """批量获取基本面数据"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')  # 获取昨天的日期作为备选
            results = []
            
            # 使用tushare批量获取数据
            ts_codes = []
            for code in stock_codes:
                if code.startswith('sh.'):
                    ts_codes.append(code.replace('sh.', '') + '.SH')
                elif code.startswith('sz.'):
                    ts_codes.append(code.replace('sz.', '') + '.SZ')
            
            if not ts_codes:
                return []
                
            try:
                # 获取基本面数据（先尝试今天的数据，如果没有则尝试昨天的）
                df_basic = self.pro.daily_basic(
                    ts_code=','.join(ts_codes),
                    trade_date=today,
                    fields='ts_code,pe_ttm,pb,total_mv'
                )
                
                if df_basic.empty:
                    df_basic = self.pro.daily_basic(
                        ts_code=','.join(ts_codes),
                        trade_date=yesterday,
                        fields='ts_code,pe_ttm,pb,total_mv'
                    )
                
                # 获取最新的财务指标数据
                df_finance = self.pro.fina_indicator(
                    ts_code=','.join(ts_codes),
                    period=today[:6],
                    fields='ts_code,roe_yoy'
                )
                
                if not df_basic.empty:
                    df = pd.merge(df_basic, df_finance, on='ts_code', how='left')
                    
                    for _, row in df.iterrows():
                        try:
                            # 转换代码格式
                            stock_code = f"sh.{row['ts_code'].split('.')[0]}" if row['ts_code'].endswith('SH') else f"sz.{row['ts_code'].split('.')[0]}"
                            
                            # 确保所有数值都是有效的
                            pe = float(row['pe_ttm']) if not pd.isna(row['pe_ttm']) else 0
                            pb = float(row['pb']) if not pd.isna(row['pb']) else 0
                            roe = float(row['roe_yoy']) if not pd.isna(row['roe_yoy']) else 0
                            market_cap = float(row['total_mv'])/10000 if not pd.isna(row['total_mv']) else 0
                            
                            # 只添加有效数据
                            if pe > 0 and pb > 0:
                                results.append({
                                    'code': stock_code,
                                    'pe': pe,
                                    'pb': pb,
                                    'roe': roe,
                                    'market_cap': market_cap
                                })
                        except Exception as e:
                            self.logger.warning(f"处理股票{stock_code}数据时出错: {str(e)}")
                            continue
                    
                    return results
                    
            except Exception as e:
                self.logger.warning(f"Tushare获取数据失败，尝试使用BaoStock: {str(e)}")
            
            # 如果tushare失败，使用baostock作为备选
            for stock_code in stock_codes:
                for retry in range(self.max_retries):
                    try:
                        rs = bs.query_history_k_data_plus(
                            stock_code,
                            "date,code,close,peTTM,pbMRQ,volume",
                            start_date=today,
                            end_date=today,
                            frequency="d",
                            adjustflag="3"
                        )
                        
                        if rs.error_code == '0':
                            data = []
                            while (rs.error_code == '0') & rs.next():
                                data.append(rs.get_row_data())
                            if data:
                                df = pd.DataFrame(data, columns=rs.fields)
                                
                                # 获取ROE数据
                                rs_profit = bs.query_profit_data(code=stock_code, year=datetime.now().year, quarter=4)
                                profit_data = []
                                while (rs_profit.error_code == '0') & rs_profit.next():
                                    profit_data.append(rs_profit.get_row_data())
                                    
                                if profit_data:
                                    df_profit = pd.DataFrame(profit_data, columns=rs_profit.fields)
                                    
                                    try:
                                        # 计算市值
                                        close = float(df['close'].iloc[0])
                                        volume = float(df['volume'].iloc[0])
                                        pe = float(df['peTTM'].iloc[0])
                                        pb = float(df['pbMRQ'].iloc[0])
                                        roe = float(df_profit['roeAvg'].iloc[0]) if len(df_profit) > 0 else 0
                                        market_cap = close * volume / 100000000
                                        
                                        # 只添加有效数据
                                        if pe > 0 and pb > 0:
                                            results.append({
                                                'code': stock_code,
                                                'pe': pe,
                                                'pb': pb,
                                                'roe': roe,
                                                'market_cap': market_cap
                                            })
                                    except (ValueError, IndexError) as e:
                                        self.logger.warning(f"处理股票{stock_code}数据转换时出错: {str(e)}")
                                        continue
                                    break
                        
                        if retry < self.max_retries - 1:
                            time.sleep(self.retry_delay)
                            
                    except Exception as e:
                        if retry == self.max_retries - 1:
                            self.logger.error(f"获取{stock_code}数据失败: {str(e)}")
                        else:
                            time.sleep(self.retry_delay)
                            
            return results
            
        except Exception as e:
            self.logger.error(f"批量获取基本面数据失败: {str(e)}")
            return []
            
    def process_stock_batch(self, stock_batch):
        """处理一批股票"""
        try:
            selected = []
            # 将DataFrame的一批数据转换为list
            stock_codes = stock_batch['code'].tolist()
            fundamental_data_list = self.get_fundamental_data_batch(stock_codes)
            
            # 创建代码到基本面数据的映射
            fundamental_data_dict = {data['code']: data for data in fundamental_data_list}
            
            for _, stock in stock_batch.iterrows():
                try:
                    fundamental_data = fundamental_data_dict.get(stock['code'])
                    if fundamental_data and self.check_stock_condition(fundamental_data):
                        selected.append({
                            'code': stock['code'],
                            'name': str(stock['name']),  # 确保是字符串
                            'industry': str(stock['industry']),  # 确保是字符串
                            'pe': fundamental_data['pe'],
                            'pb': fundamental_data['pb'],
                            'roe': fundamental_data['roe'],
                            'market_cap': fundamental_data['market_cap']
                        })
                except Exception as e:
                    self.logger.warning(f"处理股票{stock['code']}时出错: {str(e)}")
                    continue
                    
            # 更新进度
            with self.progress_lock:
                self.progress += len(stock_batch)
                progress_percent = (self.progress / self.total_stocks) * 100
                if self.progress % 50 == 0:  # 每处理50只股票输出一次进度
                    self.logger.info(f"处理进度: {progress_percent:.2f}% ({self.progress}/{self.total_stocks})")
                    
            return selected
            
        except Exception as e:
            self.logger.error(f"处理股票批次时出错: {str(e)}")
            return []
            
    def check_stock_condition(self, data):
        """检查股票是否满足条件"""
        if data is None:
            return False
            
        try:
            pe = data['pe']
            pb = data['pb']
            roe = data['roe']
            market_cap = data['market_cap']
            
            # 检查条件
            pe_ok = self.pe_range[0] <= pe <= self.pe_range[1]
            pb_ok = self.pb_range[0] <= pb <= self.pb_range[1]
            roe_ok = roe >= self.min_roe
            cap_ok = self.market_cap_range[0] <= market_cap <= self.market_cap_range[1]
            
            return pe_ok and pb_ok and roe_ok and cap_ok
            
        except Exception as e:
            self.logger.error(f"检查股票条件失败: {str(e)}")
            return False
            
    def send_dingtalk_message(self, message):
        """发送钉钉消息"""
        try:
            webhook = self.config.get('dingtalk_webhook')
            if not webhook:
                self.logger.error("未配置钉钉webhook")
                return
                
            # 确保webhook是有效的URL
            if not webhook.startswith('http'):
                self.logger.error("无效的钉钉webhook URL")
                return
                
            headers = {'Content-Type': 'application/json'}
            data = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            response = requests.post(webhook, headers=headers, json=data)
            if response.status_code == 200:
                self.logger.info("钉钉消息发送成功")
            else:
                self.logger.error(f"钉钉消息发送失败: {response.text}")
                
        except Exception as e:
            self.logger.error(f"发送钉钉消息失败: {str(e)}")
            
    def run(self):
        """运行选股策略"""
        self.logger.info("开始执行价值+因子选股...")
        
        # 获取股票列表
        stock_list = self.get_stock_list()
        if stock_list is None:
            return
            
        self.total_stocks = len(stock_list)
        self.logger.info(f"共获取到 {self.total_stocks} 只股票")
        
        # 将股票列表分成批次
        batch_size = 5  # 每批处理的股票数量
        stock_batches = [stock_list.iloc[i:i + batch_size] for i in range(0, len(stock_list), batch_size)]
        
        selected_stocks = []
        
        # 使用线程池处理股票批次
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_batch = {executor.submit(self.process_stock_batch, batch): batch for batch in stock_batches}
            
            # 获取结果
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    selected_stocks.extend(batch_results)
                except Exception as e:
                    self.logger.error(f"处理股票批次时出错: {str(e)}")
                    
        # 输出结果
        if selected_stocks:
            message = f"选股结果 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n\n"
            message += "筛选条件：\n"
            message += f"PE范围: {self.pe_range}\n"
            message += f"PB范围: {self.pb_range}\n"
            message += f"最小ROE: {self.min_roe}%\n"
            message += f"市值范围: {self.market_cap_range}亿\n\n"
            message += "符合条件的股票：\n"
            
            for stock in selected_stocks:
                message += f"{stock['name']}({stock['code']}) - {stock['industry']}\n"
                message += f"PE: {stock['pe']:.2f}, PB: {stock['pb']:.2f}, ROE: {stock['roe']:.2f}%, 市值: {stock['market_cap']:.2f}亿\n\n"
                
            self.logger.info(message)
            self.send_dingtalk_message(message)
        else:
            message = "未找到符合条件的股票"
            self.logger.info(message)
            self.send_dingtalk_message(message)
            
if __name__ == "__main__":
    strategy = ValueFactorStrategy()
    strategy.run() 