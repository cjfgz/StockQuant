import time
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import traceback
from stockquant.market import Market
import baostock as bs

class AutoTrader:
    def __init__(self):
        self.market = Market()
        # 测试多个股票
        self.stock_codes = [
            "sz.300616",  # 尚品宅配
            "sh.600519",  # 贵州茅台
            "sz.000001",  # 平安银行
            "sh.601318"   # 中国平安
        ]
        self.current_stock_index = 0
        self.stock_code = self.stock_codes[self.current_stock_index]
        
        self.min_volume = 100  # 最小交易数量
        self.holding = False  # 是否持仓
        self.max_price = 0  # 持仓期间最高价
        self.buy_price = 0  # 买入价格
        self.setup_logging()
        
        # 交易参数
        self.stop_loss = 0.04  # 止损比例
        self.trailing_stop = 0.06  # 追踪止损
        self.profit_target_1 = 0.03  # 第一档止盈
        self.profit_target_2 = 0.06  # 第二档止盈
        self.profit_target_3 = 0.09  # 第三档止盈
        
        # 连接BaoStock
        bs_result = bs.login()
        if bs_result.error_code != '0':
            self.logger.error(f"BaoStock连接失败: {bs_result.error_msg}")
        else:
            self.logger.info(f"BaoStock登录成功: {bs_result.error_code} {bs_result.error_msg}")
        
    def __del__(self):
        """析构函数，确保退出时登出BaoStock"""
        try:
            bs.logout()
            self.logger.info("BaoStock登出成功")
        except:
            pass
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def switch_stock(self):
        """切换到下一个股票"""
        self.current_stock_index = (self.current_stock_index + 1) % len(self.stock_codes)
        self.stock_code = self.stock_codes[self.current_stock_index]
        self.logger.info(f"切换到股票: {self.stock_code}")
        return self.stock_code

    def get_stock_data(self):
        """获取股票数据"""
        try:
            # 获取实时数据
            # 转换股票代码格式为新浪格式 (sz.300616 -> sz300616)
            sina_code = self.stock_code.replace('.', '')
            self.logger.info(f"获取实时数据，股票代码: {sina_code}")
            
            price_info = self.market.sina.get_realtime_data(sina_code)
            if not price_info:
                self.logger.error("获取股票实时数据失败")
                return None, None
                
            current_price = float(price_info['price'])
            self.logger.info(f"当前价格: {current_price}")
            
            # 获取历史数据
            try:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
                
                self.logger.info(f"获取历史数据，股票代码: {self.stock_code}, 开始日期: {start_date}, 结束日期: {end_date}")
                
                # 使用baostock直接获取数据
                rs = bs.query_history_k_data_plus(
                    self.stock_code,
                    "date,code,open,high,low,close,volume",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"  # 复权类型，3表示不复权
                )
                
                if rs.error_code != '0':
                    self.logger.error(f"获取历史数据失败: {rs.error_msg}")
                    return None, None
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                self.logger.info(f"成功获取到 {len(data_list)} 条历史数据")
                
                if not data_list or len(data_list) < 20:
                    self.logger.warning(f"历史数据不足，使用模拟数据。获取到 {len(data_list)} 条数据")
                    # 使用模拟数据
                    hist_data = pd.DataFrame({
                        'close': [current_price] * 30,
                        'high': [current_price * 1.02] * 30,
                        'low': [current_price * 0.98] * 30,
                        'volume': [1000000] * 30
                    })
                else:
                    # 转换为DataFrame
                    hist_data = pd.DataFrame(data_list, columns=['date', 'code', 'open', 'high', 'low', 'close', 'volume'])
                    # 转换数据类型
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        hist_data[col] = pd.to_numeric(hist_data[col])
                    
                    # 打印数据示例
                    self.logger.info(f"数据示例: {hist_data.iloc[0].to_dict()}")
            except Exception as e:
                self.logger.error(f"获取历史数据出错: {str(e)}")
                self.logger.error(traceback.format_exc())
                # 使用模拟数据
                hist_data = pd.DataFrame({
                    'close': [current_price] * 30,
                    'high': [current_price * 1.02] * 30,
                    'low': [current_price * 0.98] * 30,
                    'volume': [1000000] * 30
                })
            
            # 计算技术指标
            # 移动平均线
            hist_data['price_ma5'] = hist_data['close'].rolling(window=5).mean()
            hist_data['price_ma10'] = hist_data['close'].rolling(window=10).mean()
            hist_data['price_ma20'] = hist_data['close'].rolling(window=20).mean()
            
            # 计算布林带
            hist_data['std20'] = hist_data['close'].rolling(window=20).std()
            hist_data['upper_band'] = hist_data['price_ma20'] + 2 * hist_data['std20']
            hist_data['lower_band'] = hist_data['price_ma20'] - 2 * hist_data['std20']
            
            # 计算MACD
            exp1 = hist_data['close'].ewm(span=8, adjust=False).mean()
            exp2 = hist_data['close'].ewm(span=17, adjust=False).mean()
            hist_data['macd'] = exp1 - exp2
            hist_data['signal'] = hist_data['macd'].ewm(span=9, adjust=False).mean()
            hist_data['hist'] = hist_data['macd'] - hist_data['signal']
            
            # 计算RSI
            delta = hist_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            hist_data['rsi'] = 100 - (100 / (1 + rs))
            
            # 计算KDJ
            low_9 = hist_data['low'].rolling(window=9).min()
            high_9 = hist_data['high'].rolling(window=9).max()
            rsv = 100 * (hist_data['close'] - low_9) / (high_9 - low_9)
            hist_data['k'] = rsv.ewm(com=2).mean()
            hist_data['d'] = hist_data['k'].ewm(com=2).mean()
            hist_data['j'] = 3 * hist_data['k'] - 2 * hist_data['d']
            
            # 计算成交量指标
            hist_data['volume_ma10'] = hist_data['volume'].rolling(window=10).mean()
            hist_data['volume_ratio_10'] = hist_data['volume'] / hist_data['volume_ma10']
            
            # 计算波动率
            hist_data['volatility'] = hist_data['close'].pct_change().rolling(window=20).std() * np.sqrt(252)
            
            # 获取最新和前一天的数据
            if len(hist_data) >= 2:
                current_data = hist_data.iloc[-1].to_dict()
                prev_data = hist_data.iloc[-2].to_dict()
                
                # 添加当前价格
                current_data['current_price'] = current_price
                
                # 更新最高价
                if self.holding and current_price > self.max_price:
                    self.max_price = current_price
                
                return current_data, prev_data
            else:
                self.logger.error("历史数据不足，无法计算指标")
                return None, None
            
        except Exception as e:
            self.logger.error(f"获取股票数据出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None, None

    def check_buy_signal(self, current_data, prev_data):
        """检查买入信号"""
        try:
            signals = []
            
            # 1. 趋势确认
            if current_data['current_price'] > current_data['price_ma5']:
                signals.append(True)
            
            # 2. KDJ金叉或低位
            if (current_data['k'] > current_data['d'] and prev_data['k'] <= prev_data['d']) or current_data['k'] < 30:
                signals.append(True)
            
            # 3. MACD条件
            if (current_data['macd'] > current_data['signal']) or (current_data['hist'] > 0 and current_data['hist'] > prev_data['hist']):
                signals.append(True)
            
            # 4. 量价配合
            if current_data['volume_ratio_10'] > 1.0:
                signals.append(True)
            
            # 5. RSI条件
            if 20 <= current_data['rsi'] <= 80:
                signals.append(True)
                
            # 6. 布林带条件
            if current_data['current_price'] < current_data['lower_band'] * 1.05:
                signals.append(True)
                
            # 7. 反弹确认
            if current_data['current_price'] > prev_data['close'] and prev_data['close'] < prev_data['price_ma5']:
                signals.append(True)
            
            # 需要至少2个条件满足
            return len(signals) >= 2
            
        except Exception as e:
            self.logger.error(f"检查买入信号出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def check_sell_signal(self, current_data, prev_data):
        """检查卖出信号"""
        try:
            if not self.holding:
                return False
                
            current_price = current_data['current_price']
            current_return = (current_price - self.buy_price) / self.buy_price
            
            # 1. 止损
            if current_price < self.buy_price * (1 - self.stop_loss):
                self.logger.info(f"触发止损: 当前价格 {current_price}, 买入价格 {self.buy_price}")
                return True
            
            # 2. 追踪止损
            trailing_stop = self.trailing_stop
            if current_return > 0.08:
                trailing_stop = self.trailing_stop * 0.8
            elif current_return > 0.05:
                trailing_stop = self.trailing_stop * 0.9
            if current_price < self.max_price * (1 - trailing_stop):
                self.logger.info(f"触发追踪止损: 当前价格 {current_price}, 最高价格 {self.max_price}")
                return True
            
            # 3. 技术指标反转
            if ((current_data['k'] < current_data['d'] and prev_data['k'] >= prev_data['d']) or
                (current_data['macd'] < current_data['signal'] and prev_data['macd'] >= prev_data['signal'])):
                if current_return > 0.02:
                    self.logger.info(f"触发技术指标反转: 当前收益率 {current_return:.2%}")
                    return True
            
            # 4. 布林带超买
            if current_price > current_data['upper_band'] * 0.98 and current_return > 0.03:
                self.logger.info(f"触发布林带超买: 当前价格 {current_price}, 上轨 {current_data['upper_band']}")
                return True
            
            # 5. 分批止盈
            if current_return >= self.profit_target_3:
                self.logger.info(f"触发第三档止盈: 当前收益率 {current_return:.2%}")
                return True
            elif current_return >= self.profit_target_2:
                self.logger.info(f"触发第二档止盈: 当前收益率 {current_return:.2%}")
                return True
            elif current_return >= self.profit_target_1:
                if current_data['volume_ratio_10'] < 1.0 or current_data['macd'] < current_data['signal']:
                    self.logger.info(f"触发第一档止盈: 当前收益率 {current_return:.2%}")
                    return True
                    
            # 6. 高波动性股票的特殊处理
            if current_data['volatility'] > 0.5 and current_return > 0.04:
                self.logger.info(f"触发高波动性止盈: 当前收益率 {current_return:.2%}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查卖出信号出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def execute_trade(self, action, price):
        """执行交易（模拟）"""
        try:
            if action == "buy":
                self.holding = True
                self.buy_price = price
                self.max_price = price
                self.logger.info(f"模拟买入: {self.stock_code}, 数量: {self.min_volume}, 价格: {price}")
            else:
                self.holding = False
                self.max_price = 0
                self.buy_price = 0
                self.logger.info(f"模拟卖出: {self.stock_code}, 数量: {self.min_volume}, 价格: {price}")
            return True
            
        except Exception as e:
            self.logger.error(f"执行{action}交易出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def run(self):
        """运行交易程序"""
        self.logger.info("开始运行自动交易程序（模拟模式）...")
        
        # 测试每个股票
        for i in range(len(self.stock_codes)):
            self.stock_code = self.stock_codes[i]
            self.logger.info(f"测试股票 {i+1}/{len(self.stock_codes)}: {self.stock_code}")
            
            # 获取股票数据
            current_data, prev_data = self.get_stock_data()
            if current_data is None or prev_data is None:
                self.logger.error(f"无法获取股票 {self.stock_code} 的数据，跳过")
                continue
            
            # 检查买入信号
            buy_signal = self.check_buy_signal(current_data, prev_data)
            self.logger.info(f"买入信号: {'是' if buy_signal else '否'}")
            
            # 模拟买入
            if buy_signal:
                self.execute_trade("buy", current_data['current_price'])
                
                # 检查卖出信号
                sell_signal = self.check_sell_signal(current_data, prev_data)
                self.logger.info(f"卖出信号: {'是' if sell_signal else '否'}")
                
                if sell_signal:
                    self.execute_trade("sell", current_data['current_price'])
            
            # 等待一秒再测试下一个股票
            time.sleep(1)
        
        self.logger.info("所有股票测试完成")

if __name__ == "__main__":
    trader = AutoTrader()
    trader.run() 