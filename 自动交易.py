import time
import pandas as pd
import numpy as np
# 移除pywinauto导入
# from pywinauto.application import Application
from stockquant.market import Market
import logging
from datetime import datetime, timedelta
import baostock as bs
import os
import sys
import talib

class AutoTrader:
    def __init__(self):
        self.market = Market()
        self.stock_code = "sz300677"  # 英科医疗
        self.min_volume = 100  # 最小交易数量
        self.holding = False  # 是否持仓
        self.max_price = 0  # 持仓期间的最高价格
        self.buy_price = 0  # 买入价格
        self.setup_logging()
        
        # 技术指标参数
        self.rsi_period = 14
        self.rsi_buy_threshold = 30  # RSI低于此值视为超卖
        self.rsi_sell_threshold = 70  # RSI高于此值视为超买
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.kdj_period = 9
        self.kdj_slow = 3
        self.kdj_smooth = 3
        self.bb_period = 20
        self.bb_std = 2
        
        # 测试模式设置
        self.test_mode = True  # 启用测试模式
        self.test_cycle = 0  # 测试周期计数
        self.test_cycle_limit = 3  # 每3个周期切换一次买卖信号
        
        # 连接BaoStock
        bs_result = bs.login()
        if bs_result.error_code != '0':
            self.logger.error(f"BaoStock登录失败: {bs_result.error_msg}")
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

    def get_stock_data(self, stock_code):
        """获取股票数据"""
        try:
            # 获取当前日期
            now = datetime.now()
            
            # 创建过去30天的日期序列
            date_list = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
            date_list.reverse()  # 按时间顺序排列
            
            # 获取实时价格
            current_price = self.get_real_time_price(stock_code)
            logging.info(f"当前价格: {current_price}")
            
            # 测试模式下，模拟数据
            if self.test_mode:
                if self.holding:
                    logging.info("模拟数据：创建明确的死叉信号")
                    # 模拟一个明确的死叉信号
                    if self.test_cycle <= 2:
                        # 前两个周期，创建金叉信号
                        base_price = current_price
                        prices = [base_price - 0.5 * i for i in range(10)]
                        prices.reverse()  # 价格上升
                    else:
                        # 后续周期，创建死叉信号
                        base_price = current_price - 2.5
                        prices = [base_price + 0.5 * i for i in range(10)]
                        prices.reverse()  # 价格下降
                else:
                    logging.info("模拟数据：创建明确的金叉信号")
                    # 模拟一个明确的金叉信号
                    if self.test_cycle <= 2:
                        # 前两个周期，创建金叉信号
                        base_price = current_price
                        prices = [base_price + 0.5 * i for i in range(10)]
                        prices.reverse()  # 价格下降
                    else:
                        # 后续周期，创建金叉信号
                        base_price = current_price - 2.5
                        prices = [base_price + 0.5 * i for i in range(10)]  # 价格上升
                
                # 确保价格序列长度为30
                full_prices = [current_price] * (30 - len(prices)) + prices
                
                # 打印模拟的价格序列（最后10天）
                logging.info(f"模拟价格序列（最后10天）: {prices}")
                
                # 创建模拟数据
                sim_data = {
                    'date': date_list,
                    'close': full_prices,
                    'volume': []  # 模拟成交量
                }
                
                # 生成模拟成交量数据，根据价格变化调整成交量
                base_volume = 100000
                for i in range(30):
                    if i > 0:
                        # 价格上涨时，成交量增加；价格下跌时，成交量减少
                        price_change = sim_data['close'][i] - sim_data['close'][i-1]
                        volume_factor = 1 + (price_change / sim_data['close'][i-1]) * 5  # 放大成交量变化
                        sim_data['volume'].append(int(base_volume * max(0.5, volume_factor)))
                    else:
                        sim_data['volume'].append(base_volume)
                
                df = pd.DataFrame(sim_data)
                
                # 计算成交量移动平均线
                df['Volume_MA5'] = df['volume'].rolling(window=5).mean()
                df['Volume_MA10'] = df['volume'].rolling(window=10).mean()
                
                # 计算移动平均线
                df['MA5'] = df['close'].rolling(window=5).mean()
                df['MA10'] = df['close'].rolling(window=10).mean()
                df['MA20'] = df['close'].rolling(window=20).mean()
                
                # 计算RSI
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # 计算MACD
                exp1 = df['close'].ewm(span=12, adjust=False).mean()
                exp2 = df['close'].ewm(span=26, adjust=False).mean()
                df['MACD'] = exp1 - exp2
                df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                df['Hist'] = df['MACD'] - df['Signal']
                
                # 计算KDJ
                low_min = df['close'].rolling(window=9).min()
                high_max = df['close'].rolling(window=9).max()
                df['RSV'] = (df['close'] - low_min) / (high_max - low_min) * 100
                df['K'] = df['RSV'].ewm(com=2).mean()
                df['D'] = df['K'].ewm(com=2).mean()
                df['J'] = 3 * df['K'] - 2 * df['D']
                
                # 计算布林带
                df['Middle'] = df['close'].rolling(window=20).mean()
                std = df['close'].rolling(window=20).std()
                df['Upper'] = df['Middle'] + 2 * std
                df['Lower'] = df['Middle'] - 2 * std
                
                # 记录当前和前一天的均线值
                logging.info(f"当前MA5: {df['MA5'].iloc[-1]:.2f}, 当前MA10: {df['MA10'].iloc[-1]:.2f}")
                logging.info(f"前一天MA5: {df['MA5'].iloc[-2]:.2f}, 前一天MA10: {df['MA10'].iloc[-2]:.2f}")
                logging.info(f"当前RSI: {df['RSI'].iloc[-1]:.2f}, 当前MACD: {df['MACD'].iloc[-1]:.2f}")
                logging.info(f"当前KDJ - K: {df['K'].iloc[-1]:.2f}, D: {df['D'].iloc[-1]:.2f}, J: {df['J'].iloc[-1]:.2f}")
                logging.info(f"当前成交量: {df['volume'].iloc[-1]}, 5日均量: {df['Volume_MA5'].iloc[-1]:.0f}, 10日均量: {df['Volume_MA10'].iloc[-1]:.0f}")
                
                return df
            
            # 实际模式下，获取真实数据
            # 这里需要实现从数据源获取历史数据的逻辑
            # ...
            
            # 临时返回空数据
            return pd.DataFrame()
            
        except Exception as e:
            logging.error(f"获取股票数据时发生错误: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return pd.DataFrame()

    def check_buy_signal(self, data):
        """检查买入信号"""
        try:
            if self.holding:
                return False
                
            # 获取当前价格和移动平均线
            current_price = data['close'].iloc[-1]
            ma5 = data['MA5'].iloc[-1]
            ma10 = data['MA10'].iloc[-1]
            ma20 = data['MA20'].iloc[-1]
            
            # 获取前一天的移动平均线
            prev_ma5 = data['MA5'].iloc[-2]
            prev_ma10 = data['MA10'].iloc[-2]
            
            # 获取RSI值
            rsi = data['RSI'].iloc[-1]
            prev_rsi = data['RSI'].iloc[-2]
            
            # 获取MACD值
            macd = data['MACD'].iloc[-1]
            signal = data['Signal'].iloc[-1]
            prev_macd = data['MACD'].iloc[-2]
            prev_signal = data['Signal'].iloc[-2]
            
            # 获取KDJ值
            k = data['K'].iloc[-1]
            d = data['D'].iloc[-1]
            j = data['J'].iloc[-1]
            prev_k = data['K'].iloc[-2]
            prev_d = data['D'].iloc[-2]
            
            # 获取布林带值
            upper = data['Upper'].iloc[-1]
            middle = data['Middle'].iloc[-1]
            lower = data['Lower'].iloc[-1]
            
            # 获取成交量数据
            volume = data['volume'].iloc[-1]
            volume_ma5 = data['Volume_MA5'].iloc[-1]
            volume_ma10 = data['Volume_MA10'].iloc[-1]
            prev_volume = data['volume'].iloc[-2]
            
            # 记录当前指标值
            logging.info(f"当前MA5: {ma5:.2f}, 当前MA10: {ma10:.2f}")
            logging.info(f"前一天MA5: {prev_ma5:.2f}, 前一天MA10: {prev_ma10:.2f}")
            logging.info(f"当前RSI: {rsi:.2f}, 前一天RSI: {prev_rsi:.2f}")
            logging.info(f"当前MACD: {macd:.2f}, 当前Signal: {signal:.2f}")
            logging.info(f"当前KDJ - K: {k:.2f}, D: {d:.2f}, J: {j:.2f}")
            logging.info(f"当前成交量: {volume}, 5日均量: {volume_ma5:.0f}, 10日均量: {volume_ma10:.0f}")
            
            # 检查是否在交易时间内
            now = datetime.now()
            is_trading_time = self.is_trading_time(now)
            
            if self.test_mode:
                logging.info("测试模式：忽略交易时间限制")
                is_trading_time = True
                
                # 测试模式下，在第3个周期强制触发买入信号
                if self.test_cycle == 3:
                    logging.info("测试模式：强制触发买入信号")
                    return True
            
            if not is_trading_time:
                logging.info("非交易时间，不生成买入信号")
                return False
            
            # 买入信号检查
            logging.info("买入信号检查:")
            
            # 1. 金叉信号：5日线上穿10日线
            golden_cross = prev_ma5 < prev_ma10 and ma5 > ma10
            logging.info(f"  - 5日线上穿10日线: {'是' if golden_cross else '否'}")
            
            # 2. 价格在20日线上方
            above_ma20 = current_price > ma20
            logging.info(f"  - 价格在20日线上方: {'是' if above_ma20 else '否'}")
            
            # 3. RSI超卖反弹
            rsi_oversold = prev_rsi < 30 and rsi > prev_rsi
            logging.info(f"  - RSI超卖反弹: {'是' if rsi_oversold else '否'}")
            
            # 4. MACD金叉
            macd_golden_cross = prev_macd < prev_signal and macd > signal
            logging.info(f"  - MACD金叉: {'是' if macd_golden_cross else '否'}")
            
            # 5. KDJ金叉
            kdj_golden_cross = prev_k < prev_d and k > d
            logging.info(f"  - KDJ金叉: {'是' if kdj_golden_cross else '否'}")
            
            # 6. 布林带下轨反弹
            bollinger_bottom_bounce = current_price < lower and prev_rsi < 30
            logging.info(f"  - 布林带下轨反弹: {'是' if bollinger_bottom_bounce else '否'}")
            
            # 7. 成交量放大
            volume_increase = volume > volume_ma5 * 1.2  # 成交量超过5日均量的1.2倍
            logging.info(f"  - 成交量放大: {'是' if volume_increase else '否'}")
            
            # 综合信号
            buy_signal = ((golden_cross and above_ma20) or rsi_oversold or macd_golden_cross or kdj_golden_cross or bollinger_bottom_bounce) and volume_increase
            
            logging.info(f"  - 最终买入信号: {'是' if buy_signal else '否'}")
            return buy_signal
            
        except Exception as e:
            logging.error(f"检查买入信号时发生错误: {str(e)}")
            return False

    def check_sell_signal(self, data):
        """检查卖出信号"""
        try:
            if not self.holding:
                return False
                
            # 获取当前价格和移动平均线
            current_price = data['close'].iloc[-1]
            ma5 = data['MA5'].iloc[-1]
            ma10 = data['MA10'].iloc[-1]
            ma20 = data['MA20'].iloc[-1]
            
            # 获取前一天的移动平均线
            prev_ma5 = data['MA5'].iloc[-2]
            prev_ma10 = data['MA10'].iloc[-2]
            
            # 获取RSI值
            rsi = data['RSI'].iloc[-1]
            prev_rsi = data['RSI'].iloc[-2]
            
            # 获取MACD值
            macd = data['MACD'].iloc[-1]
            signal = data['Signal'].iloc[-1]
            prev_macd = data['MACD'].iloc[-2]
            prev_signal = data['Signal'].iloc[-2]
            
            # 获取KDJ值
            k = data['K'].iloc[-1]
            d = data['D'].iloc[-1]
            j = data['J'].iloc[-1]
            prev_k = data['K'].iloc[-2]
            prev_d = data['D'].iloc[-2]
            
            # 获取布林带值
            upper = data['Upper'].iloc[-1]
            middle = data['Middle'].iloc[-1]
            lower = data['Lower'].iloc[-1]
            
            # 获取成交量数据
            volume = data['volume'].iloc[-1]
            volume_ma5 = data['Volume_MA5'].iloc[-1]
            volume_ma10 = data['Volume_MA10'].iloc[-1]
            prev_volume = data['volume'].iloc[-2]
            
            # 记录当前指标值
            logging.info(f"当前MA5: {ma5:.2f}, 当前MA10: {ma10:.2f}")
            logging.info(f"前一天MA5: {prev_ma5:.2f}, 前一天MA10: {prev_ma10:.2f}")
            logging.info(f"当前RSI: {rsi:.2f}, 前一天RSI: {prev_rsi:.2f}")
            logging.info(f"当前MACD: {macd:.2f}, 当前Signal: {signal:.2f}")
            logging.info(f"当前KDJ - K: {k:.2f}, D: {d:.2f}, J: {j:.2f}")
            logging.info(f"当前成交量: {volume}, 5日均量: {volume_ma5:.0f}, 10日均量: {volume_ma10:.0f}")
            
            # 检查是否在交易时间内
            now = datetime.now()
            is_trading_time = self.is_trading_time(now)
            
            if self.test_mode:
                logging.info("测试模式：忽略交易时间限制")
                is_trading_time = True
                
                # 测试模式下，在第6个周期强制触发卖出信号
                if self.test_cycle == 6:
                    logging.info("测试模式：强制触发卖出信号")
                    return True
            
            if not is_trading_time:
                logging.info("非交易时间，不生成卖出信号")
                return False
            
            # 卖出信号检查
            logging.info("卖出信号检查:")
            
            # 1. 死叉信号：5日线下穿10日线
            death_cross = prev_ma5 > prev_ma10 and ma5 < ma10
            logging.info(f"  - 5日线下穿10日线: {'是' if death_cross else '否'}")
            
            # 2. 价格跌破20日线
            below_ma20 = current_price < ma20
            logging.info(f"  - 价格跌破20日线: {'是' if below_ma20 else '否'}")
            
            # 3. RSI超买回落
            rsi_overbought = prev_rsi > 70 and rsi < prev_rsi
            logging.info(f"  - RSI超买回落: {'是' if rsi_overbought else '否'}")
            
            # 4. MACD死叉
            macd_death_cross = prev_macd > prev_signal and macd < signal
            logging.info(f"  - MACD死叉: {'是' if macd_death_cross else '否'}")
            
            # 5. KDJ死叉
            kdj_death_cross = prev_k > prev_d and k < d
            logging.info(f"  - KDJ死叉: {'是' if kdj_death_cross else '否'}")
            
            # 6. 布林带上轨回落
            bollinger_top_fall = current_price > upper and prev_rsi > 70
            logging.info(f"  - 布林带上轨回落: {'是' if bollinger_top_fall else '否'}")
            
            # 7. 成交量萎缩
            volume_decrease = volume < volume_ma5 * 0.8  # 成交量低于5日均量的0.8倍
            logging.info(f"  - 成交量萎缩: {'是' if volume_decrease else '否'}")
            
            # 8. 止损：价格下跌超过5%
            stop_loss = False
            if hasattr(self, 'buy_price') and self.buy_price > 0:
                stop_loss = current_price < self.buy_price * 0.95
                logging.info(f"  - 止损触发(5%): {'是' if stop_loss else '否'}")
            
            # 9. 止盈：价格上涨超过10%
            take_profit = False
            if hasattr(self, 'buy_price') and self.buy_price > 0:
                take_profit = current_price > self.buy_price * 1.10
                logging.info(f"  - 止盈触发(10%): {'是' if take_profit else '否'}")
            
            # 10. 放量下跌
            volume_price_drop = volume > volume_ma5 * 1.5 and current_price < data['close'].iloc[-2]
            logging.info(f"  - 放量下跌: {'是' if volume_price_drop else '否'}")
            
            # 综合信号
            sell_signal = (death_cross and below_ma20) or rsi_overbought or macd_death_cross or kdj_death_cross or bollinger_top_fall or stop_loss or take_profit or volume_price_drop or volume_decrease
            
            logging.info(f"  - 最终卖出信号: {'是' if sell_signal else '否'}")
            return sell_signal
            
        except Exception as e:
            logging.error(f"检查卖出信号时发生错误: {str(e)}")
            return False

    def execute_trade(self, action, stock_code, price, amount):
        """执行交易"""
        try:
            if action == "buy":
                logging.info(f"【模拟交易】买入: {stock_code}, 数量: {amount}, 价格: {price}")
                self.holding = True
                self.buy_price = price
                self.max_price = price
            elif action == "sell":
                logging.info(f"【模拟交易】卖出: {stock_code}, 数量: {amount}, 价格: {price}")
                self.holding = False
                self.buy_price = 0
                self.max_price = 0
            
            # 实际环境中，这里应该调用交易API执行实际交易
            
        except Exception as e:
            logging.error(f"执行交易时发生错误: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())

    def run(self):
        """运行自动交易程序"""
        logging.info("开始运行自动交易程序...")
        
        # 初始化测试周期计数器
        self.test_cycle = 0
        
        while True:
            try:
                # 测试模式下增加周期计数
                if self.test_mode:
                    self.test_cycle += 1
                    logging.info(f"测试模式：当前周期 {self.test_cycle}")
                
                # 获取股票数据
                data = self.get_stock_data(self.stock_code)
                if data is None or len(data) == 0:
                    logging.warning("未获取到有效数据，等待下一次尝试...")
                    time.sleep(10)
                    continue
                
                # 根据持仓状态检查买入或卖出信号
                if not self.holding:
                    # 检查买入信号
                    if self.check_buy_signal(data):
                        # 执行买入
                        current_price = data['close'].values[-1]
                        self.execute_trade("buy", self.stock_code, current_price, self.min_volume)
                        self.holding = True
                        self.buy_price = current_price
                        self.max_price = current_price
                else:
                    # 更新最高价格
                    current_price = data['close'].values[-1]
                    if current_price > self.max_price:
                        self.max_price = current_price
                    
                    # 检查卖出信号
                    if self.check_sell_signal(data):
                        # 执行卖出
                        self.execute_trade("sell", self.stock_code, current_price, self.min_volume)
                        self.holding = False
                        self.buy_price = 0
                        self.max_price = 0
                
                # 等待一段时间再次检查
                time.sleep(10)
                
                # 测试模式下，如果完成了8个周期，退出程序
                if self.test_mode and self.test_cycle >= 8:
                    logging.info("测试模式：完成8个周期，退出程序")
                    break
                
            except Exception as e:
                logging.error(f"运行过程中出错: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
                time.sleep(30)  # 出错后等待较长时间再重试

    def is_trading_time(self, now):
        """检查是否在交易时间内"""
        current_time = now.time()
        morning_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        morning_end = datetime.strptime("11:30:00", "%H:%M:%S").time()
        afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
        afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()
        
        return ((current_time >= morning_start and current_time <= morning_end) or 
                (current_time >= afternoon_start and current_time <= afternoon_end))
                
    def get_real_time_price(self, stock_code):
        """获取实时价格"""
        try:
            # 实际环境中，这里应该调用API获取实时价格
            # 测试模式下，返回模拟价格
            return 24.95
        except Exception as e:
            logging.error(f"获取实时价格时发生错误: {str(e)}")
            return 0.0

if __name__ == "__main__":
    trader = AutoTrader()
    trader.run()