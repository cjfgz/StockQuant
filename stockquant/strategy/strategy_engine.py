import pandas as pd
import numpy as np
import logging
from datetime import datetime

class StrategyEngine:
    def __init__(self):
        """初始化策略引擎"""
        self.setup_logging()
        self.setup_params()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/strategy.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_params(self):
        """设置策略参数"""
        self.params = {
            'ma_periods': [5, 10, 20],
            'volume_ratio': 1.2,
            'price_range': [2, 300],
            'max_volatility': 0.2,
            'rsi_period': 14,
            'rsi_buy': 30,
            'rsi_sell': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'stop_loss': 0.05,
            'stop_profit': 0.15
        }
        
    def calculate_technical_indicators(self, df):
        """计算技术指标"""
        try:
            # 计算移动平均线
            for period in self.params['ma_periods']:
                df[f'MA{period}'] = df['close'].rolling(window=period).mean()
                
            # 计算成交量移动平均
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.params['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.params['rsi_period']).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 计算MACD
            exp1 = df['close'].ewm(span=self.params['macd_fast']).mean()
            exp2 = df['close'].ewm(span=self.params['macd_slow']).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=self.params['macd_signal']).mean()
            df['MACD_Hist'] = df['MACD'] - df['Signal']
            
            # 计算波动率
            df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
            
            return df
            
        except Exception as e:
            self.logger.error(f"计算技术指标时出错: {str(e)}")
            return None
            
    def check_buy_signals(self, df):
        """检查买入信号"""
        try:
            if len(df) < 20:  # 确保有足够的数据
                return False
                
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            signals = {
                'ma_cross': False,  # 均线金叉
                'volume_confirm': False,  # 成交量确认
                'rsi_buy': False,  # RSI超卖
                'macd_buy': False,  # MACD金叉
                'price_range': False  # 价格合理区间
            }
            
            # 检查均线金叉
            if (prev['MA5'] <= prev['MA10'] and 
                latest['MA5'] > latest['MA10'] and 
                latest['close'] > latest['MA20']):
                signals['ma_cross'] = True
                
            # 检查成交量放大
            if latest['volume'] > latest['volume_ma5'] * self.params['volume_ratio']:
                signals['volume_confirm'] = True
                
            # 检查RSI超卖反弹
            if prev['RSI'] < self.params['rsi_buy'] and latest['RSI'] > self.params['rsi_buy']:
                signals['rsi_buy'] = True
                
            # 检查MACD金叉
            if (prev['MACD'] <= prev['Signal'] and 
                latest['MACD'] > latest['Signal']):
                signals['macd_buy'] = True
                
            # 检查价格是否在合理区间
            if (self.params['price_range'][0] <= latest['close'] <= self.params['price_range'][1] and
                latest['volatility'] <= self.params['max_volatility']):
                signals['price_range'] = True
                
            # 综合信号判断（可以根据需要调整条件组合）
            buy_signal = (signals['ma_cross'] and signals['volume_confirm'] and 
                         signals['price_range'] and 
                         (signals['rsi_buy'] or signals['macd_buy']))
                         
            if buy_signal:
                self.logger.info(f"检测到买入信号，信号详情: {signals}")
                
            return buy_signal
            
        except Exception as e:
            self.logger.error(f"检查买入信号时出错: {str(e)}")
            return False
            
    def check_sell_signals(self, df, cost_price=None):
        """检查卖出信号"""
        try:
            if len(df) < 20:
                return False
                
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            signals = {
                'ma_cross': False,  # 均线死叉
                'volume_confirm': False,  # 放量下跌
                'rsi_sell': False,  # RSI超买
                'macd_sell': False,  # MACD死叉
                'stop_loss': False,  # 止损
                'stop_profit': False  # 止盈
            }
            
            # 检查均线死叉
            if (prev['MA5'] >= prev['MA10'] and 
                latest['MA5'] < latest['MA10']):
                signals['ma_cross'] = True
                
            # 检查放量下跌
            if (latest['volume'] > latest['volume_ma5'] * 1.5 and 
                latest['close'] < prev['close']):
                signals['volume_confirm'] = True
                
            # 检查RSI超买回落
            if prev['RSI'] > self.params['rsi_sell'] and latest['RSI'] < self.params['rsi_sell']:
                signals['rsi_sell'] = True
                
            # 检查MACD死叉
            if (prev['MACD'] >= prev['Signal'] and 
                latest['MACD'] < latest['Signal']):
                signals['macd_sell'] = True
                
            # 检查止损止盈
            if cost_price:
                current_return = (latest['close'] - cost_price) / cost_price
                if current_return <= -self.params['stop_loss']:
                    signals['stop_loss'] = True
                elif current_return >= self.params['stop_profit']:
                    signals['stop_profit'] = True
                    
            # 综合信号判断
            sell_signal = (
                signals['stop_loss'] or signals['stop_profit'] or
                (signals['ma_cross'] and signals['volume_confirm']) or
                (signals['rsi_sell'] and signals['macd_sell'])
            )
            
            if sell_signal:
                self.logger.info(f"检测到卖出信号，信号详情: {signals}")
                
            return sell_signal
            
        except Exception as e:
            self.logger.error(f"检查卖出信号时出错: {str(e)}")
            return False
            
    def update_params(self, new_params):
        """更新策略参数"""
        try:
            for key, value in new_params.items():
                if key in self.params:
                    self.params[key] = value
            self.logger.info("策略参数已更新")
        except Exception as e:
            self.logger.error(f"更新策略参数时出错: {str(e)}")
            
    def get_position_score(self, df):
        """计算持仓评分"""
        try:
            if len(df) < 20:
                return 0
                
            latest = df.iloc[-1]
            
            # 计算技术面得分（0-100分）
            technical_score = 0
            
            # 趋势得分（30分）
            if latest['close'] > latest['MA20']:
                technical_score += 15
            if latest['MA5'] > latest['MA10']:
                technical_score += 15
                
            # RSI得分（20分）
            if 40 <= latest['RSI'] <= 60:
                technical_score += 20
            elif 30 <= latest['RSI'] <= 70:
                technical_score += 10
                
            # MACD得分（20分）
            if latest['MACD'] > latest['Signal']:
                technical_score += 10
            if latest['MACD_Hist'] > 0:
                technical_score += 10
                
            # 成交量得分（20分）
            if latest['volume'] > latest['volume_ma5']:
                technical_score += 20
                
            # 波动率得分（10分）
            if latest['volatility'] <= self.params['max_volatility']:
                technical_score += 10
                
            return technical_score
            
        except Exception as e:
            self.logger.error(f"计算持仓评分时出错: {str(e)}")
            return 0 