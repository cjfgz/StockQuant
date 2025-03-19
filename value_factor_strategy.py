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
import sys
import random

# 处理Windows平台控制台中文显示问题
try:
    if sys.platform.startswith('win'):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)        # 设置控制台输入代码页为UTF-8
        kernel32.SetConsoleOutputCP(65001)  # 设置控制台输出代码页为UTF-8
        print("已设置控制台编码为UTF-8")
except Exception as e:
    print(f"设置控制台编码失败: {str(e)}")

class ValueFactorStrategy:
    def __init__(self):
        # 设置日志
        self.setup_logging()
        
        # 读取配置文件
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                # 不再设置tushare token
        except FileNotFoundError:
            self.logger.error("未找到config.json文件")
            raise
            
        # 添加更多的重试和延迟设置
        # 读取配置或设置默认值
        strategy_config = self.config.get('STRATEGY', {})
        self.max_retries = strategy_config.get('retry_count', 5)  # 增加默认重试次数
        self.retry_delay = strategy_config.get('retry_delay', 2)  # 增加默认延迟时间
        
        # 连接baostock
        self.connect_baostock()
            
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
        self.pe_range = strategy_config.get('pe_range', (0, 30))  # PE范围
        self.pb_range = strategy_config.get('pb_range', (0, 3))   # PB范围
        self.min_roe = strategy_config.get('roe_min', 8)         # 最小ROE
        self.market_cap_range = strategy_config.get('market_cap_range', (50, 2000))  # 市值范围（亿）
        
        # 多线程相关
        self.max_workers = strategy_config.get('parallel_workers', 5)  # 降低默认线程数
        self.progress_lock = Lock()  # 用于进度更新的锁
        self.progress = 0  # 处理进度
        self.total_stocks = 0  # 股票总数
        
    def connect_baostock(self):
        """连接BaoStock，带重试逻辑"""
        for retry in range(self.max_retries):
            try:
                # 先尝试登出，确保没有残留的连接
                try:
                    bs.logout()
                    time.sleep(1)  # 等待登出完成
                except:
                    pass
                    
                # 重新登录前先等待
                time.sleep(2)
                
                # 重新登录
                result = bs.login()
                if result.error_code != '0':
                    self.logger.warning(f"登录BaoStock失败: {result.error_msg}, 重试次数: {retry + 1}")
                    time.sleep(self.retry_delay * (retry + 1))  # 递增等待时间
                    continue
                    
                self.logger.info("BaoStock登录成功")
                return True
                
            except Exception as e:
                self.logger.error(f"BaoStock登录异常: {str(e)}, 重试次数: {retry + 1}")
                if retry < self.max_retries - 1:
                    time.sleep(self.retry_delay * (retry + 1))
                else:
                    raise Exception(f"BaoStock登录失败，已达到最大重试次数: {str(e)}")
                    
        raise Exception("BaoStock登录失败，已达到最大重试次数")
        
    def __del__(self):
        """析构函数，确保退出时登出"""
        try:
            bs.logout()
            self.logger.info("BaoStock已登出")
        except:
            pass
            
    def setup_logging(self):
        """设置日志"""
        try:
            # 确保使用UTF-8编码写入日志文件
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('value_factor.log', encoding='utf-8', mode='w'),  # 使用模式'w'覆盖之前的日志
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info("日志系统初始化成功，使用UTF-8编码")
        except Exception as e:
            print(f"设置日志系统失败: {str(e)}")
            raise
        
    def get_stock_list(self):
        """获取股票列表"""
        try:
            # 获取沪深300成分股
            rs = bs.query_hs300_stocks()
            if rs.error_code != '0':
                self.logger.error(f"获取沪深300成分股失败: {rs.error_msg}")
                return None
                
            data_list = []
            while (rs.error_code == '0') & rs.next():
                try:
                    row = rs.get_row_data()
                    # 安全获取股票代码和名称
                    stock_code = row[1] if len(row) > 1 else ""
                    stock_name = row[2] if len(row) > 2 else "未知"
                    
                    # 确保股票代码有效
                    if not stock_code or not (stock_code.startswith('sh.') or stock_code.startswith('sz.')):
                        self.logger.warning(f"无效的股票代码: {stock_code}")
                        continue
                        
                    data_list.append({
                        'code': stock_code,
                        'name': stock_name,
                        'industry': ''
                    })
                except Exception as e:
                    self.logger.warning(f"处理单只股票数据失败: {str(e)}")
                    continue
                
            df = pd.DataFrame(data_list)
            self.logger.info(f"获取到 {len(df)} 只沪深300成分股")
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return None
            
    def get_fundamental_data_batch(self, stock_codes):
        """批量获取基本面数据"""
        try:
            # 获取最近的交易日期（使用过去30天的数据范围）
            end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')  # 使用昨天的日期
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 获取近30天的数据
            results = []
            
            # 使用baostock获取数据
            for stock_code in stock_codes:
                self.logger.info(f"正在获取股票 {stock_code} 的数据...")
                
                # 每次获取数据前都重新连接
                try:
                    self.connect_baostock()
                except Exception as e:
                    self.logger.error(f"重新连接BaoStock失败: {str(e)}")
                    continue
                    
                try:
                    # 获取K线数据
                    for retry in range(self.max_retries):
                        try:
                            time.sleep(1)  # 每次请求前等待1秒
                            rs = bs.query_history_k_data_plus(
                                stock_code,
                                "date,code,close,peTTM,pbMRQ,volume",
                                start_date=start_date,
                                end_date=end_date,
                                frequency="d",
                                adjustflag="3"
                            )
                            
                            if rs.error_code != '0':
                                self.logger.warning(f"获取K线数据失败: {rs.error_msg}, 重试次数: {retry + 1}")
                                time.sleep(self.retry_delay * (retry + 1))
                                continue
                                
                            data = []
                            while True:
                                try:
                                    if not rs.next():
                                        break
                                        
                                    row = rs.get_row_data()
                                    if len(row) < 6:
                                        continue
                                        
                                    # 数据转换
                                    try:
                                        close = float(row[2]) if row[2] and row[2] != '' else 0
                                        pe = float(row[3]) if row[3] and row[3] != '' else 0
                                        pb = float(row[4]) if row[4] and row[4] != '' else 0
                                        volume = float(row[5]) if row[5] and row[5] != '' else 0
                                        
                                        if all(x > 0 for x in [close, volume]):
                                            data.append([
                                                row[0],  # date
                                                row[1],  # code
                                                close,
                                                pe,
                                                pb,
                                                volume
                                            ])
                                    except (ValueError, TypeError) as e:
                                        continue
                                        
                                except Exception as e:
                                    self.logger.warning(f"处理K线数据行异常: {str(e)}")
                                    break
                                    
                            if data:
                                break  # 成功获取数据，跳出重试循环
                                
                        except Exception as e:
                            self.logger.error(f"获取K线数据异常: {str(e)}")
                            if retry < self.max_retries - 1:
                                time.sleep(self.retry_delay * (retry + 1))
                            else:
                                break
                                
                    if not data:
                        self.logger.warning(f"股票 {stock_code} 无法获取K线数据")
                        continue
                        
                    # 创建DataFrame
                    columns = ['date', 'code', 'close', 'peTTM', 'pbMRQ', 'volume']
                    df = pd.DataFrame(data, columns=columns)
                    df = df.sort_values('date', ascending=False)
                    
                    # 获取最新数据
                    latest_data = df.iloc[0]
                    
                    # 获取ROE数据
                    current_year = datetime.now().year
                    roe_value = 0
                    got_roe = False
                    
                    # 尝试获取ROE数据
                    for year in range(current_year-1, current_year-3, -1):
                        if got_roe:
                            break
                            
                        for retry in range(self.max_retries):
                            try:
                                time.sleep(1)  # 每次请求前等待1秒
                                rs_profit = bs.query_profit_data(code=stock_code, year=year, quarter=4)
                                
                                if rs_profit.error_code != '0':
                                    self.logger.warning(f"获取{year}年利润数据失败: {rs_profit.error_msg}")
                                    time.sleep(self.retry_delay)
                                    continue
                                    
                                while rs_profit.next():
                                    try:
                                        row = rs_profit.get_row_data()
                                        if len(row) > 3 and row[3]:
                                            try:
                                                roe_value = float(row[3])
                                                if roe_value != 0:
                                                    got_roe = True
                                                    self.logger.info(f"获取到股票 {stock_code} {year}年ROE: {roe_value}")
                                                    break
                                            except (ValueError, TypeError):
                                                continue
                                    except Exception as e:
                                        self.logger.warning(f"处理ROE数据异常: {str(e)}")
                                        continue
                                        
                                if got_roe:
                                    break
                                    
                            except Exception as e:
                                self.logger.warning(f"获取{year}年ROE数据异常: {str(e)}")
                                time.sleep(self.retry_delay)
                                
                    # 处理最终数据
                    try:
                        close = float(latest_data['close'])
                        volume = float(latest_data['volume'])
                        pe = float(latest_data['peTTM'])
                        pb = float(latest_data['pbMRQ'])
                        
                        # 验证数据有效性
                        if pe <= 0 or pb <= 0 or math.isnan(pe) or math.isinf(pe) or math.isnan(pb) or math.isinf(pb):
                            self.logger.warning(f"股票 {stock_code} PE或PB无效: PE={pe}, PB={pb}")
                            continue
                            
                        market_cap = close * volume / 100000000  # 换算为亿元
                        
                        result = {
                            'code': stock_code,
                            'pe': pe,
                            'pb': pb,
                            'roe': roe_value,
                            'market_cap': market_cap
                        }
                        self.logger.info(f"成功获取股票 {stock_code} 数据: {result}")
                        results.append(result)
                        
                    except Exception as e:
                        self.logger.error(f"处理股票 {stock_code} 最终数据时出错: {str(e)}")
                        continue
                        
                except Exception as e:
                    self.logger.error(f"处理股票 {stock_code} 整体流程异常: {str(e)}")
                    continue
                    
                # 处理完一只股票后等待一下
                time.sleep(1)
                
            self.logger.info(f"本批次共处理 {len(stock_codes)} 只股票，成功获取 {len(results)} 只股票的数据")
            return results
            
        except Exception as e:
            self.logger.error(f"批量获取基本面数据失败: {str(e)}")
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
            pe_ok = self.pe_range[0] <= pe <= self.pe_range[1] if not math.isnan(pe) else False
            pb_ok = self.pb_range[0] <= pb <= self.pb_range[1] if not math.isnan(pb) else False
            roe_ok = roe >= self.min_roe if not math.isnan(roe) else False
            cap_ok = self.market_cap_range[0] <= market_cap <= self.market_cap_range[1] if not math.isnan(market_cap) else False
            
            # 输出条件检查结果
            if not (pe_ok and pb_ok and roe_ok and cap_ok):
                condition_msg = f"PE条件: {pe_ok}({pe}), PB条件: {pb_ok}({pb}), ROE条件: {roe_ok}({roe}), 市值条件: {cap_ok}({market_cap})"
                self.logger.info(f"股票 {data['code']} 不满足条件: {condition_msg}")
                
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
        batch_size = 3  # 减小每批处理的股票数量
        stock_batches = [stock_list.iloc[i:i + batch_size] for i in range(0, len(stock_list), batch_size)]
        
        selected_stocks = []
        
        # 使用线程池处理股票批次，减少并发线程数
        with ThreadPoolExecutor(max_workers=min(3, self.max_workers)) as executor:
            # 提交所有任务
            future_to_batch = {}
            
            # 分批提交任务，避免同时提交太多任务
            for i, batch in enumerate(stock_batches):
                future = executor.submit(self.process_stock_batch, batch)
                future_to_batch[future] = batch
                
                # 每提交5个批次休息一下
                if i > 0 and i % 5 == 0:
                    self.logger.info(f"已提交 {i} 个批次，休息 {self.retry_delay} 秒")
                    time.sleep(self.retry_delay)
            
            # 获取结果
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    # 添加超时控制
                    batch_results = future.result(timeout=60)  # 60秒超时
                    selected_stocks.extend(batch_results)
                except TimeoutError:
                    self.logger.error("处理批次超时")
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
            
    def process_stock_batch(self, stock_batch):
        """处理一批股票"""
        try:
            selected = []
            # 将DataFrame的一批数据转换为list
            stock_codes = stock_batch['code'].tolist()
            fundamental_data_list = self.get_fundamental_data_batch(stock_codes)
            
            if not fundamental_data_list:
                self.logger.warning("未获取到任何基本面数据")
                return []
                
            # 创建代码到基本面数据的映射
            fundamental_data_dict = {data['code']: data for data in fundamental_data_list}
            
            for _, stock in stock_batch.iterrows():
                try:
                    stock_code = stock['code']
                    stock_name = str(stock['name'])
                    fundamental_data = fundamental_data_dict.get(stock_code)
                    
                    if fundamental_data and self.check_stock_condition(fundamental_data):
                        selected.append({
                            'code': stock_code,
                            'name': stock_name,
                            'industry': str(stock['industry']),
                            'pe': fundamental_data['pe'],
                            'pb': fundamental_data['pb'],
                            'roe': fundamental_data['roe'],
                            'market_cap': fundamental_data['market_cap']
                        })
                        self.logger.info(f"股票 {stock_name}({stock_code}) 符合选择条件")
                except Exception as e:
                    self.logger.warning(f"处理股票 {stock.get('code', '未知')} 时出错: {str(e)}")
                    continue
                    
            # 更新进度
            with self.progress_lock:
                self.progress += len(stock_batch)
                progress_percent = (self.progress / self.total_stocks) * 100
                if self.progress % 10 == 0:  # 每处理10只股票输出一次进度
                    self.logger.info(f"处理进度: {progress_percent:.2f}% ({self.progress}/{self.total_stocks})")
                    
            return selected
            
        except Exception as e:
            self.logger.error(f"处理股票批次时出错: {str(e)}")
            return []
            
if __name__ == "__main__":
    strategy = ValueFactorStrategy()
    strategy.run()