# -*- coding: utf-8 -*-
import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from stockquant.message import DingTalk
import json
import os
import time
from functools import lru_cache
import traceback

class ValueFactorStrategy:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        self.connect_baostock()
        self.init_dingding()
        self.setup_params()
        
        # 获取最近的交易日
        today = datetime.now()
        if today.weekday() >= 5:  # 如果是周末
            days_to_subtract = today.weekday() - 4  # 获取上周五的日期
            today = today - timedelta(days=days_to_subtract)
        
        # 再往前推一个交易日，确保数据已更新
        self.today = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        self.logger.info(f"使用交易日期: {self.today}")
        self.logger.info("正在设置选股参数...")
        
        # 选股参数
        self.pe_range = (0, 100)          # PE范围
        self.pb_range = (0, 10)           # PB范围
        self.roe_min = 0                  # ROE最小值
        self.market_cap_range = (10, 5000) # 市值范围（亿）
        self.max_stocks = 100             # 最大选股数量
        
        # 性能参数
        self.max_workers = 5              # 线程数
        self.batch_size = 50             # 批处理大小
        self.max_retries = 3             # 重试次数
        self.retry_delay = 1             # 基础重试延迟
        self.max_retry_delay = 5         # 最大重试延迟
        self.timeout = 15                # 超时时间
        
        # 缓存已获取的数据
        self.data_cache = {}
        
        self.logger.info(f"""选股参数设置完成：
- PE范围: {self.pe_range}
- PB范围: {self.pb_range}
- ROE最小值: {self.roe_min}%
- 市值范围: {self.market_cap_range}亿
- 最大选股数量: {self.max_stocks}
- 线程数: {self.max_workers}
- 批处理大小: {self.batch_size}
- 最大重试次数: {self.max_retries}
- 重试延迟: {self.retry_delay}-{self.max_retry_delay}秒""")

    def connect_baostock(self):
        """连接BaoStock"""
        self.logger.info("正在连接BaoStock...")
        retry_count = 0
        while retry_count < 3:
            try:
                bs.login()
                self.is_connected = True
                self.logger.info("BaoStock连接成功")
                return True
            except Exception as e:
                retry_count += 1
                self.logger.error(f"BaoStock连接失败(第{retry_count}次): {str(e)}")
                time.sleep(1)
        return False

    def init_dingding(self):
        """初始化钉钉"""
        try:
            self.logger.info("正在初始化钉钉机器人...")
            self.ding = DingTalk()
            test_message = """A股每日精选【选股策略】
--------------------------------
选股助手已成功连接！
当前时间：{}
--------------------------------""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            self.ding.send_message(test_message)
            self.logger.info("钉钉机器人连接测试成功！")
        except Exception as e:
            self.logger.error(f"钉钉机器人初始化失败：{str(e)}")
            self.ding = None

    def setup_params(self):
        """设置选股参数"""
        # 选股参数
        self.pe_range = (0, 100)          # PE范围
        self.pb_range = (0, 10)           # PB范围
        self.roe_min = 0                  # ROE最小值
        self.market_cap_range = (10, 5000) # 市值范围（亿）
        self.max_stocks = 100             # 最大选股数量
        
        # 性能参数
        self.max_workers = 5              # 线程数
        self.batch_size = 50             # 批处理大小
        self.max_retries = 3             # 重试次数
        self.retry_delay = 1             # 基础重试延迟
        self.max_retry_delay = 5         # 最大重试延迟
        self.timeout = 15                # 超时时间
        
        # 缓存已获取的数据
        self.data_cache = {}
        
        self.logger.info(f"""选股参数设置完成：
- PE范围: {self.pe_range}
- PB范围: {self.pb_range}
- ROE最小值: {self.roe_min}%
- 市值范围: {self.market_cap_range}亿
- 最大选股数量: {self.max_stocks}
- 线程数: {self.max_workers}
- 批处理大小: {self.batch_size}
- 最大重试次数: {self.max_retries}
- 重试延迟: {self.retry_delay}-{self.max_retry_delay}秒""")

    def get_stock_list(self):
        """获取股票列表"""
        try:
            self.logger.info("开始获取创业板和沪深300股票列表...")
            
            # 获取沪深300成分股
            rs_hs300 = bs.query_hs300_stocks()
            if rs_hs300.error_code != '0':
                self.logger.error(f"获取沪深300成分股失败: {rs_hs300.error_msg}")
                return []
            
            # 处理沪深300数据
            hs300_list = []
            while (rs_hs300.error_code == '0') & rs_hs300.next():
                stock = rs_hs300.get_row_data()
                if stock[1].startswith(('sh.6', 'sz.00')):  # 只保留沪深300中的主板股票
                    hs300_list.append(stock[1])
            
            # 获取创业板股票
            rs = bs.query_all_stock(self.today)
            if rs.error_code != '0':
                self.logger.error(f"获取创业板股票列表失败: {rs.error_msg}")
                return hs300_list  # 如果获取创业板失败，至少返回沪深300的股票
            
            # 处理创业板数据
            gem_list = []
            while (rs.error_code == '0') & rs.next():
                stock = rs.get_row_data()
                if stock[0].startswith('sz.30'):  # 只保留创业板股票
                    gem_list.append(stock[0])
            
            # 合并两个列表
            stock_list = hs300_list + gem_list
            
            self.logger.info(f"获取到 {len(hs300_list)} 只沪深300股票")
            self.logger.info(f"获取到 {len(gem_list)} 只创业板股票")
            self.logger.info(f"总共 {len(stock_list)} 只股票")
            self.logger.debug(f"股票列表示例: {stock_list[:10]}")
            
            return stock_list
            
        except Exception as e:
            self.logger.error(f"获取股票列表时发生错误: {str(e)}")
            return []

    def get_fundamental_data(self, stock_code, date):
        """获取股票基本面数据"""
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                # 计算当前重试的延迟时间（指数退避）
                if retry_count > 0:
                    delay = min(self.retry_delay * (2 ** (retry_count - 1)), self.max_retry_delay)
                    self.logger.debug(f"第{retry_count + 1}次重试 {stock_code}, 等待{delay}秒...")
                    time.sleep(delay)
                
                self.logger.debug(f"开始获取{stock_code}的基本面数据（第{retry_count + 1}次尝试）...")
                
                # 1. 获取行情数据
                data = self._get_market_data(stock_code, date)
                if data is None:
                    retry_count += 1
                    continue
                    
                # 2. 获取总股本数据
                total_share = self._get_total_shares(stock_code, data)
                if total_share is None:
                    retry_count += 1
                    continue
                    
                # 3. 计算市值（亿元）
                market_value = data['close'] * total_share / 100000000
                
                result = {
                    'code': stock_code,
                    'close': data['close'],
                    'pe': data['peTTM'],
                    'pb': data['pbMRQ'],
                    'market_value': market_value,
                    'total_share': total_share,
                    'volume': data['volume'],
                    'turn': data['turn']
                }
                
                self.logger.debug(f"成功获取{stock_code}的数据: PE={result['pe']:.2f}, PB={result['pb']:.2f}, 市值={result['market_value']:.2f}亿")
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"获取{stock_code}基本面数据时出错（第{retry_count + 1}次尝试）: {str(e)}")
                if retry_count < self.max_retries - 1:
                    self.logger.debug(f"错误详情: {traceback.format_exc()}")
                retry_count += 1
                
        self.logger.error(f"在{self.max_retries}次尝试后仍未能获取{stock_code}的数据")
        if last_error:
            self.logger.error(f"最后一次错误: {str(last_error)}")
        return None

    def _get_market_data(self, stock_code, date):
        """获取市场行情数据"""
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                if retry_count > 0:
                    delay = min(self.retry_delay * (2 ** (retry_count - 1)), self.max_retry_delay)
                    self.logger.debug(f"获取行情数据第{retry_count + 1}次重试 {stock_code}, 等待{delay}秒...")
                    time.sleep(delay)
                
                # 查询当日行情数据
                self.logger.debug(f"查询{stock_code}的行情数据: date,code,close,turn,volume,peTTM,pbMRQ,psTTM,pcfNcfTTM, 日期: {date}")
                rs = bs.query_history_k_data_plus(
                    code=stock_code,
                    fields="date,code,close,turn,volume,peTTM,pbMRQ,psTTM,pcfNcfTTM",
                    start_date=date,
                    end_date=date,
                    frequency="d",
                    adjustflag="3"
                )
                
                if rs.error_code != '0':
                    self.logger.warning(f"获取{stock_code}行情数据失败: {rs.error_msg}")
                    retry_count += 1
                    continue
                    
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                    
                # 如果当日数据为空，尝试获取最近10个交易日的数据
                if len(data_list) == 0:
                    for i in range(1, 11):  # 增加到往前查找10天
                        prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
                        self.logger.debug(f"未获取到{stock_code}的当日数据，尝试获取{prev_date}的数据")
                        
                        rs = bs.query_history_k_data_plus(
                            code=stock_code,
                            fields="date,code,close,turn,volume,peTTM,pbMRQ,psTTM,pcfNcfTTM",
                            start_date=prev_date,
                            end_date=prev_date,
                            frequency="d",
                            adjustflag="3"
                        )
                        
                        while (rs.error_code == '0') & rs.next():
                            data_list.append(rs.get_row_data())
                            
                        if len(data_list) > 0:
                            break
                            
                if len(data_list) == 0:
                    self.logger.warning(f"未能获取到{stock_code}最近10个交易日的行情数据")
                    retry_count += 1
                    continue
                    
                # 处理数据
                try:
                    return {
                        'date': data_list[0][0],
                        'code': data_list[0][1],
                        'close': float(data_list[0][2]) if data_list[0][2] != '' else 0,
                        'turn': float(data_list[0][3]) if data_list[0][3] != '' else 0,
                        'volume': float(data_list[0][4]) if data_list[0][4] != '' else 0,
                        'peTTM': float(data_list[0][5]) if data_list[0][5] != '' else float('inf'),
                        'pbMRQ': float(data_list[0][6]) if data_list[0][6] != '' else float('inf'),
                        'psTTM': float(data_list[0][7]) if data_list[0][7] != '' else float('inf'),
                        'pcfNcfTTM': float(data_list[0][8]) if data_list[0][8] != '' else float('inf')
                    }
                except (IndexError, ValueError) as e:
                    self.logger.warning(f"处理{stock_code}行情数据时出错: {str(e)}")
                    self.logger.debug(f"原始数据: {data_list}")
                    retry_count += 1
                    continue
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"获取{stock_code}行情数据时出错（第{retry_count + 1}次尝试）: {str(e)}")
                retry_count += 1
                continue
                
        if last_error:
            self.logger.error(f"获取{stock_code}行情数据最后一次错误: {str(last_error)}")
        return None

    def _get_total_shares(self, stock_code, market_data):
        """获取总股本数据"""
        try:
            # 1. 首先尝试从股票基本信息获取总股本
            rs_basic = bs.query_stock_basic(code=stock_code)
            if rs_basic.error_code == '0':
                while (rs_basic.error_code == '0') & rs_basic.next():
                    basic_data = rs_basic.get_row_data()
                    if len(basic_data) > 7 and basic_data[7] != '':
                        total_share = float(basic_data[7])
                        self.logger.debug(f"从基本信息获取到{stock_code}的总股本: {total_share}")
                        return total_share
            
            # 2. 如果基本信息获取失败，使用换手率计算
            if market_data['turn'] > 0 and market_data['volume'] > 0:
                total_share = market_data['volume'] / (market_data['turn'] / 100)
                self.logger.debug(f"使用换手率计算{stock_code}的总股本: {total_share}")
                return total_share
            
            # 3. 如果换手率计算失败，使用保守估计
            if market_data['volume'] > 0:
                total_share = market_data['volume'] * 100  # 假设当日换手率为1%
                self.logger.debug(f"使用保守估计{stock_code}的总股本: {total_share}")
                return total_share
            
            self.logger.error(f"无法获取{stock_code}的总股本数据")
            return None
            
        except Exception as e:
            self.logger.error(f"获取{stock_code}总股本数据时出错: {str(e)}")
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            return None

    def get_stock_data(self, stock_code, days=30):
        """获取股票历史数据用于计算均线"""
        try:
            end_date = self.today
            start_date = (datetime.strptime(self.today, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(
                code=stock_code,
                fields="date,code,close,volume",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != '0':
                self.logger.error(f"获取股票{stock_code}历史数据失败: {rs.error_msg}")
                return None
                
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            if len(data_list) < 20:  # 确保有足够的数据计算均线
                return None
                
            df = pd.DataFrame(data_list, columns=['date', 'code', 'close', 'volume'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票{stock_code}历史数据时出错: {str(e)}")
            return None

    def check_golden_cross(self, df):
        """检查是否出现金叉"""
        try:
            if len(df) < 2:  # 确保有足够的数据
                return False
                
            # 获取最新两天的数据
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 判断金叉：前一天5日线在10日线下方，当天5日线在10日线上方
            golden_cross = (prev['MA5'] <= prev['MA10']) and (latest['MA5'] > latest['MA10'])
            
            return golden_cross
            
        except Exception as e:
            self.logger.error(f"检查金叉信号时出错: {str(e)}")
            return False

    def process_stock_batch(self, stock_batch):
        """处理一批股票"""
        matched_stocks = []
        processed_count = 0
        
        try:
            for code in stock_batch:
                try:
                    self.logger.debug(f"开始处理股票: {code}")
                    
                    # 获取基本面数据
                    fundamental_data = self.get_fundamental_data(code, self.today)
                    if fundamental_data is None:
                        continue
                        
                    # 获取历史数据用于计算均线
                    hist_data = self.get_stock_data(code)
                    if hist_data is None:
                        continue
                        
                    # 检查金叉信号
                    golden_cross = self.check_golden_cross(hist_data)
                    
                    # 检查是否满足所有条件
                    if (self.pe_range[0] <= fundamental_data['pe'] <= self.pe_range[1] and 
                        self.pb_range[0] <= fundamental_data['pb'] <= self.pb_range[1] and 
                        fundamental_data['market_value'] >= self.market_cap_range[0] and 
                        fundamental_data['market_value'] <= self.market_cap_range[1] and
                        golden_cross):  # 添加金叉条件
                        
                        # 获取最新数据
                        latest_data = hist_data.iloc[-1]
                        matched_stocks.append({
                            'code': code,
                            'pe': fundamental_data['pe'],
                            'pb': fundamental_data['pb'],
                            'market_value': fundamental_data['market_value'],
                            'price': latest_data['close'],
                            'MA5': latest_data['MA5'],
                            'MA10': latest_data['MA10']
                        })
                        self.logger.info(f"股票{code}匹配条件: PE={fundamental_data['pe']:.2f}, PB={fundamental_data['pb']:.2f}, 市值={fundamental_data['market_value']:.2f}亿, 出现金叉")
                    else:
                        self.logger.debug(f"股票{code}不满足条件: PE={fundamental_data['pe']:.2f}, PB={fundamental_data['pb']:.2f}, 市值={fundamental_data['market_value']:.2f}亿, 金叉={golden_cross}")
                    
                    processed_count += 1
                    if processed_count % 10 == 0:
                        self.logger.info(f"已处理 {processed_count}/{len(stock_batch)} 只股票")
                        
                except Exception as e:
                    self.logger.error(f"处理股票{code}时发生错误: {str(e)}")
                    continue
                    
            return matched_stocks
            
        except Exception as e:
            self.logger.error(f"处理股票批次时发生错误: {str(e)}")
            return []

    def format_result_message(self, matched_stocks, total_time):
        """格式化结果消息"""
        message = f"""🔍 A股每日精选【价值+均线策略】
--------------------------------
选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
耗时：{total_time:.1f}秒

🎯 选股条件：
1. PE范围：{self.pe_range[0]}-{self.pe_range[1]}
2. PB范围：{self.pb_range[0]}-{self.pb_range[1]}
3. 市值范围：{self.market_cap_range[0]}-{self.market_cap_range[1]}亿
4. 5日均线上穿10日均线（金叉）

"""
        if not matched_stocks:
            message += "❌ 今日没有符合条件的股票"
        else:
            message += f"✅ 共筛选出{len(matched_stocks)}只股票：\n"
            for stock in matched_stocks:
                message += f"""
📌 {stock['code']}
   当前价格: {stock['price']:.2f}
   市盈率: {stock['pe']:.2f}
   市净率: {stock['pb']:.2f}
   市值: {stock['market_value']:.2f}亿
   5日均线: {stock['MA5']:.2f}
   10日均线: {stock['MA10']:.2f}
--------------------------------"""
                
        return message

    def send_dingtalk_message(self, message):
        """发送钉钉消息"""
        try:
            if hasattr(self, 'ding') and self.ding:
                # 确保消息是有效的UTF-8编码
                safe_message = message.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                self.ding.send_message(safe_message)
                self.logger.info("选股结果已推送到钉钉")
            else:
                self.logger.warning("钉钉未初始化，无法发送消息")
        except Exception as e:
            self.logger.error(f"发送钉钉消息失败: {str(e)}")

    def run(self):
        """运行策略"""
        if not self.is_connected:
            self.logger.error("BaoStock未连接，无法执行策略")
            return
            
        try:
            start_time = time.time()
            self.logger.info("开始运行价值因子策略...")
            
            # 获取股票列表
            stock_list = self.get_stock_list()
            if not stock_list:
                return
            
            total_stocks = len(stock_list)
            self.logger.info(f"共获取到 {total_stocks} 只股票")
            
            # 将股票列表分成批次
            stock_batches = [stock_list[i:i + self.batch_size] 
                           for i in range(0, len(stock_list), self.batch_size)]
            
            # 创建线程池
            matched_stocks = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                futures = []
                for batch in stock_batches:
                    future = executor.submit(self.process_stock_batch, batch)
                    futures.append(future)
                
                # 处理结果
                completed = 0
                total_batches = len(futures)
                
                for future in as_completed(futures):
                    try:
                        batch_results = future.result(timeout=self.timeout)
                        if batch_results:
                            matched_stocks.extend(batch_results)
                        
                        # 更新进度
                        completed += 1
                        if completed % 1 == 0:  # 每完成一个批次就更新进度
                            progress = (completed / total_batches) * 100
                            elapsed = time.time() - start_time
                            remaining = (elapsed / completed) * (total_batches - completed) if completed > 0 else 0
                            
                            self.logger.info(
                                f"进度: {completed}/{total_batches} ({progress:.1f}%) "
                                f"已用时: {elapsed:.1f}秒 "
                                f"预计剩余: {remaining:.1f}秒"
                            )
                            
                    except Exception as e:
                        self.logger.error(f"处理批次失败: {str(e)}")
                        continue
            
            # 按市值排序并限制数量
            if matched_stocks:
                matched_stocks.sort(key=lambda x: x['market_value'])
                matched_stocks = matched_stocks[:self.max_stocks]
            
            # 计算总耗时
            total_time = time.time() - start_time
            
            # 发送结果
            message = self.format_result_message(matched_stocks, total_time)
            self.send_dingtalk_message(message)
            
        except Exception as e:
            self.logger.error(f"策略执行出错: {str(e)}")
            self.send_dingtalk_message(f"策略执行出错: {str(e)}")
            
        finally:
            # 清理缓存
            self.data_cache.clear()

    def check_connection(self):
        """检查连接状态，如果断开则尝试重连"""
        if not self.is_connected:
            return self.connect_baostock()
        return True

    def __del__(self):
        """析构函数，确保退出时登出"""
        if self.is_connected:
            try:
                bs.logout()
                self.is_connected = False
            except:
                pass
            
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.DEBUG,  # 改为DEBUG级别以显示更多信息
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('value_factor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

if __name__ == "__main__":
    strategy = ValueFactorStrategy()
    strategy.run()