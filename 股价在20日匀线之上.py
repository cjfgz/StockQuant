import pandas as pd
import numpy as np
from stockquant.market import Market
import logging
from datetime import datetime, timedelta
import baostock as bs
import talib

class MA20Strategy:
    def __init__(self):
        self.market = Market()
        self.setup_logging()
        self.bs = None
        
        # 选股参数
        self.volume_threshold = 30000   # 最小成交量（3万手）
        self.price_min = 3.0           # 最小股价
        self.price_max = 50.0          # 最大股价
        self.rsi_upper = 75            # RSI上限
        self.rsi_lower = 25            # RSI下限
        self.macd_threshold = 0        # MACD阈值
        self.volume_ratio_threshold = 1.2  # 量比阈值
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ma20_strategy.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect_baostock(self):
        """连接BaoStock"""
        if self.bs is None:
            self.bs = bs.login()
            if self.bs.error_code != '0':
                self.logger.error(f"BaoStock登录失败: {self.bs.error_msg}")
                return False
            return True
        return True

    def disconnect_baostock(self):
        """断开BaoStock连接"""
        if self.bs is not None:
            bs.logout()
            self.bs = None

    def get_stock_data(self, stock_code, start_date, end_date):
        """获取股票数据"""
        try:
            # 确保BaoStock已连接
            if not self.connect_baostock():
                return None

            # 转换股票代码格式
            bs_code = f"{stock_code[2:]}.{stock_code[:2].upper()}"
            
            # 获取历史数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != '0':
                self.logger.error(f"获取股票数据失败: {rs.error_msg}")
                return None

            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if not data_list or len(data_list) < 20:
                self.logger.warning(f"股票 {stock_code} 历史数据不足")
                return None

            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 确保数值列为浮点数类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 删除任何包含NaN的行
            df = df.dropna(subset=['close', 'volume'])
            
            # 确保数据按日期排序
            df = df.sort_values('date')
            
            if len(df) < 20:  # 再次检查清理后的数据是否足够
                self.logger.warning(f"股票 {stock_code} 清理后的数据不足")
                return None
                
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票 {stock_code} 数据失败: {str(e)}")
            return None

    def calculate_technical_indicators(self, df):
        """计算技术指标"""
        try:
            # 移动平均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()

            # MACD
            df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['EMA12'] - df['EMA26']
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']

            # RSI
            close_delta = df['close'].diff()
            up = close_delta.clip(lower=0)
            down = -1 * close_delta.clip(upper=0)
            ma_up = up.rolling(window=14).mean()
            ma_down = down.rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + ma_up / ma_down))

            # 布林带
            df['BB_middle'] = df['close'].rolling(window=20).mean()
            df['BB_upper'] = df['BB_middle'] + 2 * df['close'].rolling(window=20).std()
            df['BB_lower'] = df['BB_middle'] - 2 * df['close'].rolling(window=20).std()

            # 成交量变化
            df['Volume_MA5'] = df['volume'].rolling(window=5).mean()
            df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['volume'] / df['Volume_MA5']

            return df

        except Exception as e:
            self.logger.error(f"计算技术指标时出错: {str(e)}")
            return None

    def check_stock_conditions(self, df, last_row):
        """检查选股条件"""
        try:
            # 基本条件检查
            price_ok = self.price_min <= last_row['close'] <= self.price_max
            volume_ok = last_row['volume'] >= self.volume_threshold
            
            if not (price_ok and volume_ok):
                return False, "基本条件不满足"

            # 均线多头排列
            ma_trend = (last_row['MA5'] > last_row['MA10'] > last_row['MA20'] > last_row['MA60'])
            
            # 5日与10日均线金叉（当日5日线在10日线上方，前一日5日线在10日线下方）
            prev_row = df.iloc[-2]  # 获取前一天的数据
            golden_cross = (last_row['MA5'] > last_row['MA10']) and (prev_row['MA5'] <= prev_row['MA10'])
            
            # MACD金叉或在零轴以上
            macd_ok = last_row['MACD'] > last_row['Signal'] and last_row['MACD'] > self.macd_threshold
            
            # RSI不过热不过冷
            rsi_ok = self.rsi_lower <= last_row['RSI'] <= self.rsi_upper
            
            # 量价配合
            volume_ok = last_row['Volume_Ratio'] > self.volume_ratio_threshold  # 成交量放大
            
            # 布林带位置
            price_position = (last_row['close'] > last_row['BB_middle']) and (last_row['close'] < last_row['BB_upper'])

            # 综合判断
            all_conditions = [
                ma_trend,
                golden_cross,  # 添加金叉条件
                macd_ok,
                rsi_ok,
                volume_ok,
                price_position
            ]

            # 记录不满足的条件
            failed_conditions = []
            if not price_ok:
                failed_conditions.append(f"股价不在{self.price_min}-{self.price_max}元范围内")
            if not volume_ok:
                failed_conditions.append(f"成交量小于{self.volume_threshold/10000:.1f}万手")
            if not ma_trend:
                failed_conditions.append("均线多头排列不满足")
            if not golden_cross:
                failed_conditions.append("5日10日均线未金叉")
            if not macd_ok:
                failed_conditions.append("MACD条件不满足")
            if not rsi_ok:
                failed_conditions.append(f"RSI不在{self.rsi_lower}-{self.rsi_upper}区间")
            if not volume_ok:
                failed_conditions.append(f"量比小于{self.volume_ratio_threshold}")
            if not price_position:
                failed_conditions.append("布林带位置不合适")

            return all(all_conditions), "满足所有条件" if all(all_conditions) else f"不满足条件: {', '.join(failed_conditions)}"

        except Exception as e:
            self.logger.error(f"检查选股条件时出错: {str(e)}")
            return False, str(e)

    def analyze_stock(self, stock_code, start_date, end_date):
        """分析单个股票"""
        try:
            df = self.get_stock_data(stock_code, start_date, end_date)
            if df is None:
                return []

            # 计算技术指标
            df = self.calculate_technical_indicators(df)
            if df is None:
                return []

            # 获取最新一行数据
            last_row = df.iloc[-1]
            
            # 检查条件
            meets_conditions, reason = self.check_stock_conditions(df, last_row)
            
            if meets_conditions:
                signal_data = {
                    'date': last_row['date'],
                    'close': last_row['close'],
                    'MA5': last_row['MA5'],
                    'MA10': last_row['MA10'],
                    'MA20': last_row['MA20'],
                    'MA60': last_row['MA60'],
                    'RSI': last_row['RSI'],
                    'MACD': last_row['MACD'],
                    'volume': last_row['volume'],
                    'volume_ratio': last_row['Volume_Ratio']
                }
                
                self.logger.info(f"\n股票 {stock_code} 满足条件:")
                self.logger.info(f"日期: {signal_data['date']}")
                self.logger.info(f"收盘价: {signal_data['close']:.2f}")
                self.logger.info(f"MA5/10/20/60: {signal_data['MA5']:.2f}/{signal_data['MA10']:.2f}/{signal_data['MA20']:.2f}/{signal_data['MA60']:.2f}")
                self.logger.info(f"RSI: {signal_data['RSI']:.2f}")
                self.logger.info(f"MACD: {signal_data['MACD']:.2f}")
                self.logger.info(f"成交量: {signal_data['volume']/10000:.2f}万手")
                self.logger.info(f"量比: {signal_data['volume_ratio']:.2f}")
                
                return [signal_data]
            
            return []

        except Exception as e:
            self.logger.error(f"分析股票 {stock_code} 时发生错误: {str(e)}")
            return []

    def get_chinext_stocks(self):
        """获取创业板股票列表"""
        try:
            # 生成创业板股票代码列表（300000-301000）
            stock_list = [f"sz{str(i).zfill(6)}" for i in range(300000, 301000)]
            self.logger.info(f"生成了 {len(stock_list)} 只创业板股票代码")
            
            # 验证股票是否存在
            valid_stocks = []
            for stock in stock_list:
                try:
                    # 尝试获取股票数据
                    price_info = self.market.sina.get_realtime_data(stock)
                    if price_info and price_info.get('name'):
                        valid_stocks.append(stock)
                        self.logger.info(f"验证股票: {stock} - {price_info['name']}")
                except:
                    continue
            
            self.logger.info(f"找到 {len(valid_stocks)} 只有效的创业板股票")
            return valid_stocks
            
        except Exception as e:
            self.logger.error(f"获取创业板股票列表失败: {str(e)}")
            return []

    def scan_market(self, stock_list):
        """扫描市场"""
        try:
            self.logger.info("开始扫描市场...")
            results = {}
            
            # 设置时间范围为最近60天
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

            for stock in stock_list:
                self.logger.info(f"\n分析股票 {stock}...")
                signals = self.analyze_stock(stock, start_date, end_date)

                if signals:
                    results[stock] = signals
                    self.logger.info(f"股票 {stock} 满足选股条件")
                else:
                    self.logger.info(f"股票 {stock} 不满足选股条件")

            self.analyze_results(results)
            return results
            
        finally:
            # 确保在扫描结束后断开连接
            self.disconnect_baostock()

    def analyze_results(self, results):
        """分析结果"""
        total_stocks = len(results)
        if total_stocks > 0:
            self.logger.info(f"\n=== 选股结果 ===")
            self.logger.info(f"共找到 {total_stocks} 只符合条件的股票")
            self.logger.info("\n详细结果:")
            for stock, signals in results.items():
                for signal in signals:
                    self.logger.info(f"""
股票代码: {stock}
选股时间: {signal['date']}
收盘价: {signal['close']:.2f}
均线系统:
- MA5: {signal['MA5']:.2f}
- MA10: {signal['MA10']:.2f}
- MA20: {signal['MA20']:.2f}
- MA60: {signal['MA60']:.2f}
技术指标:
- RSI(14): {signal['RSI']:.2f}
- MACD: {signal['MACD']:.2f}
成交量分析:
- 成交量: {signal['volume']/10000:.2f}万手
- 量比: {signal['volume_ratio']:.2f}
--------------------------------""")
        else:
            self.logger.info("\n没有找到符合条件的股票")

def main():
    strategy = MA20Strategy()
    
    # 获取创业板股票列表
    stock_list = strategy.get_chinext_stocks()
    if not stock_list:
        print("获取创业板股票列表失败")
        return
        
    # 执行扫描
    strategy.scan_market(stock_list)

if __name__ == "__main__":
    main()
