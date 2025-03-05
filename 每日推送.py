import pandas as pd
import numpy as np
import schedule
import time
from datetime import datetime, timedelta
import requests
import json
from chinese_calendar import is_workday
import logging
from stockquant.market import Market
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from stockquant.message import DingTalk
import signal
import sys

class StockSignalMonitor:
    def __init__(self):
        # 设置日志
        self.setup_logging()
        
        # 初始化Market实例
        self.market = Market()
        self.logger.info("成功初始化Market实例")
        
        # 配置请求重试
        self.setup_request_retry()

        # 企业微信机器人webhook地址
        self.webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=576e97c9acda5aa7d328e762334b8aebaf56cf5977dd6216d4a61572e10f9885"

        self.running = True  # 添加运行状态标志
        self.setup_signal_handlers()  # 设置信号处理

    def get_stock_data(self, stock_code):
        """获取股票数据（优先使用BaoStock，失败后尝试新浪数据源）"""
        try:
            # 设置重试次数和超时
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 获取实时数据
                    price_info = self.market.sina.get_realtime_data(stock_code)
                    if not price_info:
                        retry_count += 1
                        self.logger.warning(f"第{retry_count}次尝试获取股票 {stock_code} 数据失败，将重试...")
                        time.sleep(2)  # 等待2秒后重试
                        continue

                    # 获取历史数据（使用BaoStock）
                    hist_data = self.market.baostock.get_history_k_data_plus(
                        stock_code,
                        timeframe="d",
                        start_date=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
                        end_date=datetime.now().strftime('%Y-%m-%d'),
                        adjustflag="3"  # 使用后复权数据
                    )
                    
                    if not hist_data or len(hist_data) < 20:
                        retry_count += 1
                        self.logger.warning(f"第{retry_count}次尝试获取股票 {stock_code} 历史数据不足，将重试...")
                        time.sleep(2)
                        continue

                    # 计算均线
                    df = pd.DataFrame(hist_data)
                    df['close'] = df['close'].astype(float)
                    df['volume'] = df['volume'].astype(float)
                    
                    # 确保数据按日期排序
                    df = df.sort_values('date')
                    
                    # 计算均线
                    df['MA5'] = df['close'].rolling(window=5).mean()
                    df['MA10'] = df['close'].rolling(window=10).mean()
                    df['MA20'] = df['close'].rolling(window=20).mean()

                    # 计算成交量均线
                    df['Volume_MA5'] = df['volume'].rolling(window=5).mean()

                    # 整合数据
                    data = {
                        'code': stock_code,
                        'name': price_info['name'],
                        'price': float(price_info['price']),
                        'volume': float(price_info['volume']),
                        'amount': float(price_info['amount']),
                        'MA5': df['MA5'].iloc[-1],
                        'MA10': df['MA10'].iloc[-1],
                        'MA20': df['MA20'].iloc[-1],
                        'prev_MA5': df['MA5'].iloc[-2],
                        'prev_MA10': df['MA10'].iloc[-2],
                        'volume_ma5': df['Volume_MA5'].iloc[-1],
                        'prev_volume_ma5': df['Volume_MA5'].iloc[-2]
                    }

                    self.logger.info(f"成功获取股票 {data['name']}({stock_code}) 的数据")
                    return data

                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    self.logger.warning(f"网络请求错误，第{retry_count}次重试: {str(e)}")
                    time.sleep(2)
                    continue
                    
                except Exception as e:
                    retry_count += 1
                    self.logger.warning(f"获取数据出错，第{retry_count}次重试: {str(e)}")
                    time.sleep(2)
                    continue

            self.logger.error(f"获取股票 {stock_code} 数据失败，已重试{max_retries}次")
            return None

        except Exception as e:
            self.logger.error(f"获取股票 {stock_code} 数据时发生严重错误: {str(e)}")
            return None

    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('stock_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_request_retry(self):
        """配置请求重试机制"""
        retry_strategy = Retry(
            total=3,  # 最多重试3次
            backoff_factor=1,  # 重试间隔
            status_forcelist=[500, 502, 503, 504]  # 需要重试的HTTP状态码
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def check_stock_filters(self, data):
        """检查股票是否满足筛选条件"""
        try:
            if not data or not isinstance(data, dict):
                return False
                
            # 检查必要字段
            required_fields = ['price', 'volume', 'name']
            if not all(field in data for field in required_fields):
                return False
                
            # 价格条件：5-200元
            price = float(data['price'])
            if not (5 <= price <= 200):
                return False
                
            # 成交量条件：大于500万手
            volume = float(data['volume']) / 10000  # 转换为万手
            if volume < 500:
                return False
                
            self.logger.info(f"\n开始筛选股票 {data['name']}:\n"
                           f"价格: {price:.2f} (目标范围: 5-200)\n"
                           f"成交量: {volume:.2f}万手 (最小要求: 500万手)\n")
            
            self.logger.info(f"股票 {data['name']} 通过所有筛选条件")
            return True
            
        except Exception as e:
            self.logger.error(f"筛选股票时发生错误: {str(e)}")
            return False

    def update_stock_list(self):
        """获取主要A股列表并更新到文件"""
        try:
            self.logger.info("开始验证股票代码，共500个待验证...")
            
            # 生成股票代码列表
            stock_codes = []
            
            # 沪市主板 (600000-601999, 603000-603999, 605000-605999)
            stock_codes.extend([f'sh{code}' for code in range(600000, 602000)])
            stock_codes.extend([f'sh{code}' for code in range(603000, 604000)])
            stock_codes.extend([f'sh{code}' for code in range(605000, 606000)])
            
            # 深市主板 (000001-000999, 001000-001999)
            stock_codes.extend([f'sz{str(code).zfill(6)}' for code in range(1, 1000)])
            stock_codes.extend([f'sz{str(code).zfill(6)}' for code in range(1000, 2000)])
            
            # 创业板 (300000-300999, 301000-301999)
            stock_codes.extend([f'sz{code}' for code in range(300000, 301000)])
            stock_codes.extend([f'sz{code}' for code in range(301000, 302000)])
            
            # 科创板 (688000-688999, 689000-689999)
            stock_codes.extend([f'sh{code}' for code in range(688000, 689000)])
            stock_codes.extend([f'sh{code}' for code in range(689000, 690000)])
            
            matched_stocks = []
            
            for i, stock_code in enumerate(stock_codes, 1):
                try:
                    # 获取实时数据
                    data = self.get_stock_data(stock_code)
                    
                    # 验证数据有效性
                    if data and isinstance(data, dict) and data.get('name'):
                        # 检查基本条件
                        if self.check_stock_filters(data):
                            # 转换为标准格式的代码
                            ts_code = stock_code[2:] + ('.SH' if stock_code.startswith('sh') else '.SZ')
                            
                            # 添加到有效股票列表
                            matched_stocks.append({
                                'code': ts_code,
                                'name': data['name'],
                                'price': float(data['price']),
                                'volume': float(data['volume'])
                            })
                            
                            if len(matched_stocks) % 10 == 0:
                                self.logger.info(f"已找到{len(matched_stocks)}只符合条件的股票")
                                
                except Exception as e:
                    self.logger.debug(f"处理股票{stock_code}时出错: {str(e)}")
                    continue
                
                # 每处理50个股票休息1秒
                if i % 50 == 0:
                    time.sleep(1)
            
            # 保存结果
            if matched_stocks:
                self.save_to_csv(matched_stocks)
                return matched_stocks
            else:
                self.logger.warning("未找到符合条件的股票，将使用默认列表")
                return self.get_default_stock_list()
                
        except Exception as e:
            self.logger.error(f"更新股票列表失败: {str(e)}")
            return self.get_default_stock_list()

    def save_to_csv(self, stocks):
        df = pd.DataFrame(stocks)
        df.to_csv('stock_list.csv', index=False, encoding='utf-8')
        self.logger.info('股票列表已保存到 stock_list.csv')

    def get_default_stock_list(self):
        """获取默认股票列表"""
        default_stocks = [
            '300616.SZ',  # 尚品宅配
            '600000.SH',  # 浦发银行
            '601318.SH',  # 中国平安
            '000001.SZ',  # 平安银行
            '600519.SH',  # 贵州茅台
            '000858.SZ',  # 五粮液
            '601888.SH',  # 中国中免
            '002594.SZ',  # 比亚迪
            '300750.SZ',  # 宁德时代
            '600036.SH'   # 招商银行
        ]
        self.logger.info(f"使用默认股票列表，共{len(default_stocks)}只股票")
        return default_stocks

    def get_stock_list(self):
        """从本地文件读取股票列表，如果失败则使用默认列表"""
        try:
            df = pd.read_csv('stock_list.csv')
            stock_list = df['code'].tolist()
            self.logger.info(f"从文件加载了{len(stock_list)}只股票")
            return stock_list
        except Exception as e:
            self.logger.warning(f"读取股票列表文件失败: {str(e)}，将使用默认股票列表")
            return self.get_default_stock_list()

    def get_history_data(self, stock_code):
        """获取历史数据（使用BaoStock）"""
        try:
            # 获取最近30个交易日的数据
            hist_data = self.market.baostock.get_history_k_data_plus(
                stock_code,
                timeframe="d",
                start_date=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d')
            )
            
            if not hist_data or len(hist_data) < 20:
                self.logger.warning(f"股票 {stock_code} 历史数据不足")
                return None

            # 转换数据格式
            df = pd.DataFrame(hist_data, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            return df

        except Exception as e:
            self.logger.error(f"获取历史数据失败: {str(e)}")
            return None

    def check_trading_signals(self, stock_code):
        """检查交易信号"""
        try:
            # 获取历史数据
            df = self.get_history_data(stock_code)
            if df is None:
                return None

            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()

            # 获取最新数据
            current_price = df['close'].iloc[-1]
            current_ma5 = df['MA5'].iloc[-1]
            current_ma10 = df['MA10'].iloc[-1]
            current_ma20 = df['MA20'].iloc[-1]
            prev_ma5 = df['MA5'].iloc[-2]
            prev_ma10 = df['MA10'].iloc[-2]

            # 计算成交量趋势
            volume_ma5 = df['volume'].rolling(window=5).mean()
            volume_trend = volume_ma5.iloc[-1] > volume_ma5.iloc[-5]  # 5日成交量上升

            signals = []
            
            # 金叉信号：5日线上穿10日线，且20日线在当前价格下方
            if prev_ma5 <= prev_ma10 and current_ma5 > current_ma10 and current_price > current_ma20:
                if volume_trend:  # 确认成交量配合
                    signals.append({
                        'type': 'golden_cross',
                        'price': current_price,
                        'MA5': current_ma5,
                        'MA10': current_ma10,
                        'MA20': current_ma20,
                        'volume': df['volume'].iloc[-1]
                    })
                    self.logger.info(f"发现金叉信号: {stock_code}")

            return signals if signals else None

        except Exception as e:
            self.logger.error(f"检查交易信号时发生错误: {str(e)}")
            return None

    def generate_signal_message(self, signals):
        """生成信号提示消息"""
        try:
            if not signals:
                return None

            message = "【股票提醒】均线金叉信号\n"
            message += "--------------------------------\n"
            message += f"发现时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += "符合条件：\n"
            message += "1. 5日均线上穿10日均线（金叉）\n"
            message += "2. 股价站上20日均线\n"
            message += "3. 成交量呈上升趋势\n"
            message += "--------------------------------\n"

            for signal in signals:
                stock_data = self.get_stock_data(signal['code'])
                if not stock_data:
                    continue

                message += f"\n股票：{stock_data['name']}({signal['code']})\n"
                message += f"当前价格：{signal['price']:.2f}\n"
                message += f"5日均线：{signal['MA5']:.2f}\n"
                message += f"10日均线：{signal['MA10']:.2f}\n"
                message += f"20日均线：{signal['MA20']:.2f}\n"
                message += f"成交量：{signal['volume']/10000:.2f}万手\n"
                message += "--------------------------------"

            return message

        except Exception as e:
            self.logger.error(f"生成信号消息时发生错误: {str(e)}")
            return None

    def send_wechat_message(self, content):
        """发送企业微信消息"""
        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
            response = requests.post(
                self.webhook_url,
                headers=headers,
                data=json.dumps(data)
            )
            if response.status_code != 200:
                print(f"发送消息失败: {response.text}")
        except Exception as e:
            print(f"发送消息出错: {e}")

    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """处理关闭信号"""
        self.logger.info("接收到关闭信号，正在安全退出...")
        self.running = False

    def run_monitor(self):
        """运行监控程序"""
        self.logger.info("股票信号监控已启动...")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)  # 缩短检查间隔以便更快响应退出信号
            except Exception as e:
                self.logger.error(f"运行出错: {str(e)}")
                break

        self.logger.info("监控程序已安全退出")

    def check_all_stocks(self):
        """检查所有股票的信号"""
        if not is_workday(datetime.now()):
            self.logger.info("今天是非交易日，不执行检查。")
            return

        self.logger.info(f"开始检查股票信号 - {datetime.now()}")
        signals = []

        for stock_code in self.stock_list:
            signal = self.check_trading_signals(stock_code)
            if signal:
                signals.append(signal)

        if signals:
            message = self.generate_signal_message(signals)
            self.send_wechat_message(message)
            self.logger.info(f"发现 {len(signals)} 个信号并已推送")
        else:
            self.logger.info("没有发现符合条件的信号")

def run_monitor():
    """运行监控程序"""
    monitor = StockSignalMonitor()

    # 设置每个工作日下午4点运行
    schedule.every().day.at("16:00").do(monitor.check_all_stocks)

    print("股票信号监控已启动...")
    print("按 Ctrl+C 可以安全退出程序")
    
    monitor.run_monitor()

if __name__ == "__main__":
    run_monitor()
