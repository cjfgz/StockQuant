from stockquant.market import Market
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

class MAScreener:
    def __init__(self):
        self.market = Market()
        self.setup_logging()
        
        # 选股参数设置
        self.price_limit = 100     # 股价上限
        self.volume_limit = 100    # 最小成交量(万)
        self.test_stocks = [
            'sz300616',  # 尚品宅配
            'sh600000',  # 浦发银行
            'sh601318',  # 中国平安
            'sz000001',  # 平安银行
            'sh600519',  # 贵州茅台
            'sz000858',  # 五粮液
            'sh601888',  # 中国中免
            'sz002594',  # 比亚迪
            'sz300750',  # 宁德时代
            'sh600036'   # 招商银行
        ]
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('stock_screen.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_stock_data(self, stock_code):
        """获取单个股票数据"""
        try:
            # 获取实时数据
            price_info = self.market.sina.get_realtime_data(stock_code)
            if not price_info:
                return None
                
            # 获取历史数据（这里使用模拟数据，实际应该获取真实历史数据）
            hist_prices = []
            current_price = float(price_info['price'])
            
            # 模拟21天的历史数据（用于计算20日均线）
            for i in range(21):
                # 模拟每天的价格在当前价格基础上有小幅波动
                price = current_price * (1 + np.random.normal(0, 0.01))
                hist_prices.append(price)
            
            # 转换为DataFrame
            df = pd.DataFrame({
                'close': hist_prices
            })
            
            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            # 获取最新数据
            latest_data = {
                'code': stock_code,
                'name': price_info['name'],
                'price': current_price,
                'volume': float(price_info['volume']),
                'amount': float(price_info['amount']),
                'MA5': df['MA5'].iloc[-1],
                'MA10': df['MA10'].iloc[-1],
                'MA20': df['MA20'].iloc[-1],
                'prev_MA5': df['MA5'].iloc[-2],
                'prev_MA10': df['MA10'].iloc[-2]
            }
            
            return latest_data
            
        except Exception as e:
            self.logger.error(f"获取股票{stock_code}数据失败: {str(e)}")
            return None

    def check_ma_signal(self, data):
        """检查均线金叉信号"""
        try:
            if not data:
                return False
                
            # 计算指标
            golden_cross = (data['prev_MA5'] <= data['prev_MA10'] and 
                          data['MA5'] > data['MA10'])
            price_above_ma20 = data['price'] > data['MA20']
            
            # 打印调试信息
            self.logger.info(f"\n检查股票 {data['name']}({data['code']}) 的均线信号：")
            self.logger.info(f"当前价格: {data['price']:.2f}")
            self.logger.info(f"5日均线: {data['MA5']:.2f}")
            self.logger.info(f"10日均线: {data['MA10']:.2f}")
            self.logger.info(f"20日均线: {data['MA20']:.2f}")
            self.logger.info(f"是否金叉: {'是' if golden_cross else '否'}")
            self.logger.info(f"是否在20日线上方: {'是' if price_above_ma20 else '否'}")
            
            return golden_cross and price_above_ma20
            
        except Exception as e:
            self.logger.error(f"检查均线信号出错: {str(e)}")
            return False

    def screen_stocks(self):
        """执行选股"""
        try:
            self.logger.info("开始执行均线选股...")
            matched_stocks = []
            
            for stock_code in self.test_stocks:
                try:
                    # 获取股票数据
                    stock_data = self.get_stock_data(stock_code)
                    if not stock_data:
                        continue
                        
                    # 检查均线信号
                    if self.check_ma_signal(stock_data):
                        matched_stocks.append({
                            'code': stock_data['code'],
                            'name': stock_data['name'],
                            'price': stock_data['price'],
                            'volume': stock_data['volume'],
                            'MA5': stock_data['MA5'],
                            'MA10': stock_data['MA10'],
                            'MA20': stock_data['MA20']
                        })
                        self.logger.info(f"发现符合条件的股票：{stock_data['name']}({stock_code})")
                        
                except Exception as e:
                    self.logger.error(f"处理股票 {stock_code} 时出错: {str(e)}")
                    continue
            
            # 输出选股结果
            if matched_stocks:
                self.logger.info("\n=== 选股结果 ===")
                self.logger.info(f"共找到 {len(matched_stocks)} 只符合条件的股票：")
                for stock in matched_stocks:
                    self.logger.info(f"""
股票：{stock['name']}({stock['code']})
当前价格：{stock['price']:.2f}
5日均线：{stock['MA5']:.2f}
10日均线：{stock['MA10']:.2f}
20日均线：{stock['MA20']:.2f}
成交量：{stock['volume']/10000:.2f}万
--------------------------------""")
            else:
                self.logger.info("没有找到符合条件的股票")
                
            return matched_stocks
            
        except Exception as e:
            self.logger.error(f"选股程序运行出错: {str(e)}")
            return []

if __name__ == "__main__":
    screener = MAScreener()
    screener.screen_stocks() 