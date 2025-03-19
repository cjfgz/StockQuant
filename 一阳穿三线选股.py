import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from stockquant.market import Market
from stockquant.message import DingTalk
import logging
import os
import time

class StockScreener:
    def __init__(self):
        """初始化选股器"""
        self.market = Market()
        self.ding = DingTalk()
        self.setup_logging()
        
        # 连接BaoStock
        self.connect_baostock()
        
        # 初始化无效股票列表缓存
        self.invalid_stocks = set()
        self.cache_file = 'cache/invalid_stocks.txt'
        self.load_invalid_stocks()
        
        # 目标行业
        self.target_industries = ['银行', '证券', '电力设备', '计算机', '电子', '医药生物']
        
        # 选股参数
        self.volume_ratio = 1.8  # 成交量是15日平均成交量的1.8倍
        self.volume_ma_days = 10  # 缩短成交量均线天数
        self.high_period = 30  # 缩短计算新高的周期
        self.min_volume = 20000  # 最小成交量降低到2万手
        self.break_threshold = 1.005  # 突破幅度要求降低到0.5%
        self.min_yang_ratio = 0.005  # 最小阳线涨幅要求降低到0.5%
        self.price_range = (2, 300)  # 进一步扩大股价范围
        self.max_volatility = 0.2  # 提高波动率容忍度到20%
        self.min_liquidity = 300000  # 进一步降低流动性要求
        
        # 过滤条件
        self.exclude_patterns = ['sh.688', 'sz.688','st''*ST'] 
         
        # 创建缓存目录
        if not os.path.exists('cache'):
            os.makedirs('cache')
            
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('stock_screener.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def connect_baostock(self):
        """连接BaoStock并检查连接状态"""
        try:
            result = bs.login()
            if result.error_code != '0':
                self.logger.error(f"BaoStock登录失败: {result.error_msg}")
                return False
            self.logger.info("BaoStock连接成功")
            return True
        except Exception as e:
            self.logger.error(f"BaoStock连接出错: {str(e)}")
            return False
            
    def check_baostock_connection(self):
        """检查BaoStock连接状态，如果断开则重连"""
        try:
            # 尝试进行一个简单的查询来测试连接
            test_query = bs.query_history_k_data_plus("sh.000001", "date", start_date='2024-03-12', end_date='2024-03-12')
            if test_query.error_code == '0':
                return True
                
            self.logger.warning("BaoStock连接已断开，尝试重新连接...")
            bs.logout()  # 先登出
            return self.connect_baostock()  # 重新连接
            
        except Exception as e:
            self.logger.error(f"检查BaoStock连接时出错: {str(e)}")
            return self.connect_baostock()  # 出错时尝试重新连接
        
    def load_invalid_stocks(self):
        """从缓存文件加载无效股票列表"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.invalid_stocks = set(line.strip() for line in f)
                self.logger.info(f"已加载 {len(self.invalid_stocks)} 个无效股票代码")
        except Exception as e:
            self.logger.error(f"加载无效股票列表失败: {str(e)}")
            
    def save_invalid_stocks(self):
        """保存无效股票列表到缓存文件"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                for stock in self.invalid_stocks:
                    f.write(f"{stock}\n")
            self.logger.info(f"已保存 {len(self.invalid_stocks)} 个无效股票代码")
        except Exception as e:
            self.logger.error(f"保存无效股票列表失败: {str(e)}")
            
    def is_valid_stock(self, stock_code, stock_name=''):
        """检查股票是否有效"""
        # 检查缓存的无效股票列表
        if stock_code in self.invalid_stocks:
            return False
            
        # 检查排除模式
        for pattern in self.exclude_patterns:
            if pattern in stock_code or (stock_name and pattern in stock_name):
                self.invalid_stocks.add(stock_code)
                return False
                
        # 检查是否是特殊股票
        if stock_name and ('ST' in stock_name or '*' in stock_name):
            self.invalid_stocks.add(stock_code)
            return False
            
        return True
        
    def get_stock_data(self, stock_code, max_retries=3):
        """获取股票数据"""
        # 检查股票是否有效
        if not self.is_valid_stock(stock_code):
            self.logger.info(f"跳过无效股票: {stock_code}")
            return None
            
        for retry in range(max_retries):
            try:
                # 检查并确保BaoStock连接
                if not self.check_baostock_connection():
                    if retry < max_retries - 1:
                        self.logger.warning(f"BaoStock连接失败，等待重试 ({retry+1}/{max_retries})")
                        time.sleep(2)  # 等待2秒后重试
                        continue
                    else:
                        self.logger.error("BaoStock连接失败，无法获取数据")
                        return None
                
                # 标准化股票代码格式
                if not stock_code.startswith(('sh.', 'sz.')):
                    if stock_code.startswith('sh') or stock_code.startswith('sz'):
                        stock_code = f"{stock_code[:2]}.{stock_code[2:]}"
                    elif stock_code.startswith('6'):
                        stock_code = f'sh.{stock_code}'
                    elif stock_code.startswith(('0', '3')):
                        stock_code = f'sz.{stock_code}'
                self.logger.info(f"处理股票: {stock_code}")
                
                # 获取历史数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
                
                rs = bs.query_history_k_data_plus(stock_code,
                    "date,code,open,high,low,close,volume,amount",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"
                )
                
                if rs.error_code != '0':
                    if retry < max_retries - 1:
                        self.logger.warning(f"获取股票 {stock_code} 历史数据失败 (尝试 {retry+1}/{max_retries}): {rs.error_msg}")
                        time.sleep(1)  # 等待1秒后重试
                        continue
                    else:
                        self.logger.error(f"获取股票 {stock_code} 历史数据失败，已重试{max_retries}次: {rs.error_msg}")
                        return None
                    
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                    
                if not data_list:
                    if retry < max_retries - 1:
                        self.logger.warning(f"股票 {stock_code} 没有历史数据 (尝试 {retry+1}/{max_retries})")
                        time.sleep(1)
                        continue
                    else:
                        self.logger.warning(f"股票 {stock_code} 没有历史数据，已重试{max_retries}次")
                        return None
                    
                df = pd.DataFrame(data_list, columns=rs.fields)
                
                # 转换数据类型
                numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 删除包含NaN的行
                df = df.dropna(subset=['close', 'volume'])
                
                # 确保数据按日期排序
                df = df.sort_values('date')
                
                if len(df) < 20:  # 检查数据是否足够
                    if retry < max_retries - 1:
                        self.logger.warning(f"股票 {stock_code} 的有效数据不足20天 (尝试 {retry+1}/{max_retries})")
                        time.sleep(1)
                        continue
                    else:
                        self.logger.warning(f"股票 {stock_code} 的有效数据不足20天，已重试{max_retries}次")
                        return None
                
                # 计算技术指标
                df = self.calculate_indicators(df)
                
                return df
                
            except Exception as e:
                if retry < max_retries - 1:
                    self.logger.error(f"处理股票 {stock_code} 数据时出错 (尝试 {retry+1}/{max_retries}): {str(e)}")
                    time.sleep(1)
                    continue
                else:
                    self.logger.error(f"处理股票 {stock_code} 数据时出错，已重试{max_retries}次: {str(e)}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return None
        
        # 如果连续多次获取不到数据，将其加入无效股票列表
        if max_retries == 3:
            self.logger.warning(f"股票 {stock_code} 无法获取数据，已加入无效股票列表")
            self.invalid_stocks.add(stock_code)
            self.save_invalid_stocks()
        
        return None
            
    def calculate_indicators(self, df):
        """计算更多技术指标"""
        try:
            # 基础均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA30'] = df['close'].rolling(window=30).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            
            # 成交量均线
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma10'] = df['volume'].rolling(window=10).mean()
            df['volume_ma15'] = df['volume'].rolling(window=self.volume_ma_days).mean()
            
            # 计算涨跌幅
            df['pct_change'] = df['close'].pct_change() * 100
            
            # 计算前期新高和新低
            df['prev_high'] = df['high'].rolling(window=self.high_period).max().shift(1)
            df['prev_low'] = df['low'].rolling(window=self.high_period).min().shift(1)
            
            # 计算MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_hist'] = df['MACD'] - df['Signal']
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            return df
            
        except Exception as e:
            self.logger.error(f"计算技术指标时出错: {str(e)}")
            return df
            
    def check_stock_signal(self, df):
        """检查股票信号-更严格的条件"""
        try:
            if len(df) < self.high_period:
                return False
                
            # 获取最新数据和前一天数据
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 1. 均线系统检查 (简化为三线)
            ma_trend = (
                latest['MA5'] > latest['MA10'] > latest['MA20'] and
                latest['close'] > latest['MA5'] and
                latest['close'] > latest['MA10'] and
                latest['close'] > latest['MA20']
            )
            
            # 2. 阳线要求
            yang_line = (
                latest['close'] > latest['open'] and
                (latest['close'] - latest['open']) / latest['open'] > 0.02 and  # 涨幅大于2%
                (latest['close'] - latest['open']) / latest['open'] < 0.07 and  # 涨幅小于7%
                latest['pct_change'] > 2 and latest['pct_change'] < 7  # 确认涨幅范围
            )
            
            # 3. 突破前期高点检查（新增）
            break_high = (
                latest['high'] > df['high'].iloc[:-1].max() and  # 突破前期最高点
                latest['close'] > df['high'].iloc[:-1].max() * 1.002  # 收盘价确认突破，至少高于前高0.2%
            )
            
            # 4. 成交量要求
            volume_check = (
                latest['volume'] > latest['volume_ma15'] * 2.0 and  # 量能是15日均量的2倍以上
                latest['volume'] < latest['volume_ma15'] * 4.0 and  # 但不超过4倍，防止过度放量
                latest['volume'] > latest['volume_ma5'] and  # 确保当前成交量活跃
                latest['volume_ma5'] > latest['volume_ma10']  # 确保短期成交量趋势向上
            )
            
            # 5. MACD指标确认
            macd_check = (
                latest['MACD'] > latest['Signal'] and  # MACD金叉或在零轴上方
                latest['MACD_hist'] > prev['MACD_hist'] and  # MACD柱状图向上
                latest['MACD'] > 0  # MACD在零轴以上
            )
            
            # 6. RSI指标确认
            rsi_check = (
                40 < latest['RSI'] < 70 and  # RSI在合理区间
                latest['RSI'] > prev['RSI']  # RSI向上
            )
            
            # 7. 量价配合
            volume_price_check = (
                latest['volume'] > prev['volume'] and  # 成交量放大
                latest['close'] > prev['close'] and  # 价格上涨
                latest['close'] > latest['open']  # 收盘价高于开盘价
            )
            
            # 所有条件都满足
            return (ma_trend and yang_line and volume_check and 
                    macd_check and rsi_check and volume_price_check and
                    break_high)  # 加入突破前高条件
            
        except Exception as e:
            self.logger.error(f"检查股票信号时出错: {str(e)}")
            return False

    def get_industry_stocks(self, industry):
        """获取行业股票"""
        try:
            # 获取行业股票
            rs = bs.query_stock_industry()
            if rs.error_code != '0':
                self.logger.error(f"获取行业股票失败: {rs.error_msg}")
                return []
                
            # 收集行业股票
            stocks = []
            while (rs.error_code == '0') & rs.next():
                if rs.get_row_data()[3] == industry:
                    stock_code = rs.get_row_data()[1]
                    stocks.append(stock_code)
                    
            return stocks
            
        except Exception as e:
            self.logger.error(f"获取行业股票时出错: {str(e)}")
            return []
            
    def screen_stocks(self):
        """执行选股"""
        try:
            self.logger.info("开始执行选股...")
            
            # 检查市场环境
            if not self.check_market_condition():
                self.logger.info("当前市场环境不适合交易")
                return []
                
            selected_stocks = []
            
            # 遍历目标行业
            for industry in self.target_industries:
                try:
                    # 获取行业股票
                    stocks = self.get_industry_stocks(industry)
                    if not stocks:
                        self.logger.warning(f"未找到{industry}行业的股票")
                        continue
                        
                    # 分析行业趋势
                    industry_score = self.analyze_industry_trend(industry)
                    if industry_score < 50:  # 降低行业趋势要求
                        self.logger.info(f"行业 {industry} 趋势较弱，得分：{industry_score}")
                        continue
                        
                    self.logger.info(f"开始扫描 {industry} 行业的股票...")
                    
                    # 遍历行业股票
                    for stock_code in stocks:
                        try:
                            # 获取股票数据
                            df = self.get_stock_data(stock_code)
                            if df is None or len(df) < 10:  # 降低数据要求
                                continue
                                
                            # 检查股票信号
                            if self.check_stock_signal(df):
                                latest = df.iloc[-1]
                                selected_stocks.append({
                                    'code': stock_code,
                                    'name': latest['name'] if 'name' in latest else '',
                                    'price': latest['close'],
                                    'pct_change': latest['pct_change'],
                                    'volume_ratio': latest['volume'] / latest['volume_ma15'],
                                    'technical_score': self.calculate_technical_score(df, latest),
                                    'trend_score': self.calculate_trend_score(df.iloc[-10:]),
                                    'industry': industry
                                })
                                self.logger.info(f"发现符合条件的股票：{stock_code}")
                                
                        except Exception as e:
                            self.logger.error(f"处理股票 {stock_code} 时出错: {str(e)}")
                            continue
                            
                except Exception as e:
                    self.logger.error(f"处理行业 {industry} 时出错: {str(e)}")
                    continue
                    
            # 发送选股结果
            if selected_stocks:
                self.send_result(selected_stocks)
            else:
                self.logger.info("未找到符合条件的股票")
                
            return selected_stocks
            
        except Exception as e:
            self.logger.error(f"选股过程出错: {str(e)}")
            return []
            
    def send_result(self, selected_stocks):
        """发送选股结果"""
        try:
            if not selected_stocks:
                message = f"""【股票推送】A股每日精选
--------------------------------
⏰ 选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

❌ 今日没有符合条件的股票

#股票推送 #股票交易 #交易"""
                self.ding.send_message(message)
                return
                
            # 按行业分组
            industry_stocks = {}
            for stock in selected_stocks:
                industry = stock['industry']
                if industry not in industry_stocks:
                    industry_stocks[industry] = []
                industry_stocks[industry].append(stock)
                
            # 构建消息
            message = f"""【股票推送】A股每日精选
--------------------------------
⏰ 选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【股票交易】选股条件：
1. 今日形成阳线，涨幅2%-7%
2. 均线系统多头排列（5日、10日、20日均线）
3. 突破前期高点，且收盘价确认突破
4. 成交量是15日均量的2-4倍
5. MACD金叉且在零轴上方
6. RSI在40-70之间且向上
7. 量价配合，成交量和价格同步放大

✅ 选股结果（共{len(selected_stocks)}只）：
"""
            
            # 按行业显示选中的股票
            for industry, stocks in industry_stocks.items():
                message += f"""
�� {industry}（{len(stocks)}只）：
"""
                for stock in stocks:
                    price_change = stock.get('pct_change', 0)
                    message += f"""
• {stock['code']}
  - 价格: {stock['price']:.2f}
  - 涨幅: {price_change:.2f}%
  - 量比: {stock.get('volume_ratio', 0):.2f}
  - 技术评分: {stock.get('technical_score', 0)}
  - 趋势评分: {stock.get('trend_score', 0)}
"""
            
            message += """
--------------------------------
💡 风险提示：
1. 本选股结果仅供参考，不构成投资建议
2. 投资者须自行承担投资风险和损失
3. 建议结合其他分析方法和个人判断进行投资决策
--------------------------------

#股票推送 #股票交易 #交易"""
            
            # 发送消息
            self.ding.send_message(message)
            self.logger.info("选股结果已发送")
            
        except Exception as e:
            self.logger.error(f"发送选股结果时出错: {str(e)}")

    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        except Exception as e:
            self.logger.error(f"计算RSI指标时出错: {str(e)}")
            return None

    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        try:
            exp1 = prices.ewm(span=fast, adjust=False).mean()
            exp2 = prices.ewm(span=slow, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=signal, adjust=False).mean()
            histogram = macd - signal_line
            return macd, signal_line, histogram
        except Exception as e:
            self.logger.error(f"计算MACD指标时出错: {str(e)}")
            return None, None, None

    def calculate_bollinger_bands(self, prices, period=20, num_std=2):
        """计算布林带"""
        try:
            middle = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = middle + (std * num_std)
            lower = middle - (std * num_std)
            return upper, middle, lower
        except Exception as e:
            self.logger.error(f"计算布林带时出错: {str(e)}")
            return None, None, None

    def calculate_volatility(self, prices, period=20):
        """计算波动率"""
        try:
            returns = np.log(prices / prices.shift(1))
            return returns.std() * np.sqrt(252)  # 年化波动率
        except Exception as e:
            self.logger.error(f"计算波动率时出错: {str(e)}")
            return None

    def calculate_liquidity(self, volume, amount):
        """计算流动性"""
        try:
            return amount.mean()  # 使用平均成交额作为流动性指标
        except Exception as e:
            self.logger.error(f"计算流动性时出错: {str(e)}")
            return None

    def calculate_volume_score(self, stock_data):
        """计算量能得分"""
        try:
            volume_ratio = stock_data['volume'] / stock_data['volume_ma15']
            if volume_ratio >= 2:
                return 100
            elif volume_ratio >= 1.8:
                return 90
            elif volume_ratio >= 1.5:
                return 80
            elif volume_ratio >= 1.2:
                return 70
            else:
                return 60
        except Exception as e:
            self.logger.error(f"计算量能得分时出错: {str(e)}")
            return 0

    def calculate_trend_score(self, df):
        """计算趋势得分"""
        try:
            if len(df) < 3:  # 降低数据要求
                return 0
                
            # 计算简单的趋势指标
            latest_close = df['close'].iloc[-1]
            ma3 = df['close'].rolling(window=3).mean().iloc[-1]
            ma5 = df['close'].rolling(window=5).mean().iloc[-1]
            
            score = 0
            
            # 1. 价格位置得分（40分）
            if latest_close > ma3:
                score += 20
            if latest_close > ma5:
                score += 20
                
            # 2. 均线趋势得分（30分）
            if ma3 > ma5:
                score += 30
                
            # 3. 基本分（30分）
            score += 30
            
            return score
            
        except Exception as e:
            self.logger.error(f"计算趋势得分时出错: {str(e)}")
            return 0

    def calculate_technical_score(self, df, latest):
        """计算技术指标得分"""
        try:
            score = 60
            
            # RSI指标评分
            rsi = self.calculate_rsi(df['close'])
            if rsi is not None and 40 <= rsi.iloc[-1] <= 70:
                score += 10
                
            # MACD指标评分
            macd, signal, hist = self.calculate_macd(df['close'])
            if macd is not None and signal is not None:
                if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                    score += 10
                    
            # 布林带评分
            upper, middle, lower = self.calculate_bollinger_bands(df['close'])
            if upper is not None and middle is not None and lower is not None:
                if lower.iloc[-1] <= latest['close'] <= middle.iloc[-1]:
                    score += 10
                    
            return score
        except Exception as e:
            self.logger.error(f"计算技术指标得分时出错: {str(e)}")
            return 0

    def check_market_condition(self):
        """检查市场环境是否适合交易"""
        try:
            # 获取上证指数数据
            rs = bs.query_history_k_data_plus("sh.000001",
                "date,close,volume",
                start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d'),
                frequency="d")
                
            if rs.error_code != '0':
                self.logger.error(f"获取市场数据失败: {rs.error_msg}")
                return True  # 如果获取数据失败，默认允许交易
                
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            if not data_list:
                self.logger.warning("未获取到市场数据")
                return True  # 如果没有数据，默认允许交易
                
            # 转换为DataFrame
            df = pd.DataFrame(data_list, columns=rs.fields)
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # 计算3日均线
            df['MA3'] = df['close'].rolling(window=3).mean()
            df['volume_ma3'] = df['volume'].rolling(window=3).mean()
            
            latest = df.iloc[-1]
            
            # 检查大盘趋势：收盘价在3日均线上下2%范围内即可
            trend_ok = abs(latest['close'] - latest['MA3']) / latest['MA3'] <= 0.02
            self.logger.info(f"大盘趋势检查: 收盘价={latest['close']}, 3日均线={latest['MA3']:.2f}, 结果={'通过' if trend_ok else '不通过'}")
            
            # 检查成交量：当日成交量不低于3日均量的70%即可
            volume_ok = latest['volume'] >= latest['volume_ma3'] * 0.7
            self.logger.info(f"成交量检查: 当日成交量={latest['volume']}, 3日均量={latest['volume_ma3']:.0f}, 结果={'通过' if volume_ok else '不通过'}")
            
            # 只要满足其中一个条件即可
            market_ok = trend_ok or volume_ok
            self.logger.info(f"市场环境检查结果: {'适合' if market_ok else '不适合'}交易")
            
            return market_ok
            
        except Exception as e:
            self.logger.error(f"检查市场环境时出错: {str(e)}")
            return True  # 出错时默认允许交易

    def analyze_industry_trend(self, industry):
        """分析行业趋势"""
        try:
            # 获取行业股票列表
            stocks = self.get_industry_stocks(industry)
            if not stocks:
                self.logger.warning(f"未找到{industry}行业的股票")
                return 0
                
            # 计算行业整体趋势得分
            total_score = 0
            valid_stocks = 0
            
            for stock in stocks[:30]:  # 只取前30只股票计算趋势
                try:
                    # 获取股票数据
                    df = self.get_stock_data(stock)
                    if df is None or len(df) < 10:  # 降低数据要求
                        continue
                        
                    # 计算趋势得分
                    score = self.calculate_trend_score(df.iloc[-10:])  # 缩短趋势计算周期
                    if score > 0:
                        total_score += score
                        valid_stocks += 1
                        
                except Exception as e:
                    self.logger.error(f"计算股票{stock}趋势时出错: {str(e)}")
                    continue
                    
            # 计算平均分
            if valid_stocks > 0:
                avg_score = total_score / valid_stocks
                self.logger.info(f"行业 {industry} 趋势得分：{avg_score}")
                return avg_score
            else:
                self.logger.warning(f"行业 {industry} 没有有效的股票数据")
                return 50  # 如果没有有效数据，给一个中等分数
                
        except Exception as e:
            self.logger.error(f"分析行业{industry}趋势时出错: {str(e)}")
            return 50  # 出错时返回中等分数

    def is_valid_price(self, price):
        """检查价格是否在合理区间"""
        return self.price_range[0] <= price <= self.price_range[1]

    def check_risk_factors(self, df):
        """检查风险因素"""
        try:
            # 计算波动率
            volatility = self.calculate_volatility(df['close'])
            if volatility is not None and volatility > self.max_volatility:
                return False
                
            # 计算流动性
            liquidity = self.calculate_liquidity(df['volume'], df['amount'])
            if liquidity is not None and liquidity < self.min_liquidity:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"检查风险因素时出错: {str(e)}")
            return False

    def __del__(self):
        """析构函数，确保退出时保存缓存并登出BaoStock"""
        try:
            self.save_invalid_stocks()
            bs.logout()
            self.logger.info("BaoStock已登出")
        except:
            pass

def main():
    screener = StockScreener()
    screener.screen_stocks()

if __name__ == "__main__":
    main() 