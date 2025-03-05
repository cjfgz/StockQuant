import time
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import traceback
from stockquant.market import Market

# 尝试导入pywinauto，如果失败则提供错误信息
try:
    from pywinauto.application import Application
    PYWINAUTO_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入pywinauto: {e}")
    print("自动交易功能将不可用，但数据分析和信号检测仍然可以工作")
    PYWINAUTO_AVAILABLE = False
except Exception as e:
    print(f"警告: 导入pywinauto时出现未知错误: {e}")
    print(traceback.format_exc())
    PYWINAUTO_AVAILABLE = False

class AutoTrader:
    def __init__(self):
        self.market = Market()
        self.stock_code = "sz300616"  # 尚品宅配
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

    def get_stock_data(self):
        """获取股票数据"""
        try:
            # 获取实时数据
            price_info = self.market.sina.get_realtime_data(self.stock_code)
            if not price_info:
                self.logger.error("获取股票数据失败")
                return None, None
                
            current_price = float(price_info['price'])
            
            # 获取历史数据（这里使用baostock获取真实历史数据）
            try:
                hist_data = self.market.baostock.get_history_k_data(
                    self.stock_code, 
                    start_date=(datetime.now() - pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d')
                )
                
                if hist_data is None or len(hist_data) < 20:
                    self.logger.warning("获取历史数据失败或数据不足，使用模拟数据")
                    # 使用模拟数据
                    hist_data = pd.DataFrame({
                        'close': [current_price] * 30,
                        'high': [current_price * 1.02] * 30,
                        'low': [current_price * 0.98] * 30,
                        'volume': [1000000] * 30
                    })
            except Exception as e:
                self.logger.error(f"获取历史数据出错: {str(e)}")
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
            current_data = hist_data.iloc[-1].to_dict()
            prev_data = hist_data.iloc[-2].to_dict()
            
            # 添加当前价格
            current_data['current_price'] = current_price
            
            # 更新最高价
            if self.holding and current_price > self.max_price:
                self.max_price = current_price
            
            return current_data, prev_data
            
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
        """执行交易"""
        if not PYWINAUTO_AVAILABLE:
            self.logger.warning("pywinauto不可用，无法执行自动交易")
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
            
        try:
            # 连接同花顺程序
            app = Application().connect(title="网上股票交易系统5.0")
            main_window = app.window(title="网上股票交易系统5.0")
            
            # 切换到交易界面
            main_window.type_keys("%t")  # Alt+T，切换到交易标签
            
            # 输入股票代码
            main_window["股票代码"].type_keys(self.stock_code[2:])  # 去掉sz前缀
            
            # 输入数量
            main_window["数量"].type_keys(str(self.min_volume))
            
            if action == "buy":
                # 点击买入按钮
                main_window["买入"].click()
                self.holding = True
                self.buy_price = price
                self.max_price = price
                self.logger.info(f"买入委托: {self.stock_code}, 数量: {self.min_volume}, 价格: {price}")
            else:
                # 点击卖出按钮
                main_window["卖出"].click()
                self.holding = False
                self.max_price = 0
                self.buy_price = 0
                self.logger.info(f"卖出委托: {self.stock_code}, 数量: {self.min_volume}, 价格: {price}")
            
            # 确认交易
            confirm_window = app.window(title="确认")
            confirm_window["确定"].click()
            
            return True
        except Exception as e:
            self.logger.error(f"执行{action}交易出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def run(self):
        """运行交易程序"""
        self.logger.info("开始运行自动交易程序...")
        self.logger.info(f"pywinauto可用状态: {PYWINAUTO_AVAILABLE}")
        
        while True:
            try:
                # 获取股票数据
                current_data, prev_data = self.get_stock_data()
                if current_data is None or prev_data is None:
                    time.sleep(60)
                    continue
                
                current_time = datetime.now().time()
                # 检查是否在交易时间内
                if (current_time < datetime.strptime("09:30:00", "%H:%M:%S").time() or 
                    current_time > datetime.strptime("15:00:00", "%H:%M:%S").time()):
                    self.logger.info("非交易时间，等待下一个交易日")
                    time.sleep(300)  # 非交易时间休眠5分钟
                    continue
                
                # 检查交易信号
                if not self.holding:
                    # 检查买入信号
                    if self.check_buy_signal(current_data, prev_data):
                        if self.execute_trade("buy", current_data['current_price']):
                            self.logger.info("买入信号触发成功")
                else:
                    # 检查卖出信号
                    if self.check_sell_signal(current_data, prev_data):
                        if self.execute_trade("sell", current_data['current_price']):
                            self.logger.info("卖出信号触发成功")
                
                # 每分钟检查一次
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"程序运行出错: {str(e)}")
                self.logger.error(traceback.format_exc())
                time.sleep(60)

if __name__ == "__main__":
    trader = AutoTrader()
    trader.run() 