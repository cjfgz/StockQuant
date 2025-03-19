import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from stockquant.market import Market
from stockquant.message import DingTalk

class AdvancedFactorStrategy:
    def __init__(self):
        """初始化策略"""
        self.market = Market()
        self.setup_logging()
        self.connect_baostock()
        self.setup_params()
        self.ding = DingTalk()
        self.data_cache = {}  # 添加数据缓存
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('advanced_factor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def connect_baostock(self):
        """连接BaoStock"""
        self.logger.info("正在连接BaoStock...")
        try:
            bs.login()
            self.logger.info("BaoStock连接成功")
        except Exception as e:
            self.logger.error(f"BaoStock连接失败: {str(e)}")
            raise
            
    def setup_params(self):
        """设置策略参数"""
        # 目标行业
        self.target_industries = [
            '电力设备', '计算机', '电子', '医药生物', '银行证券'
        ]
        
        # 目标板块
        self.target_sectors = [
            '人工智能', '新能源', '新能源汽车', '半导体', '医疗器械',
            '智能驾驶', '储能', '光伏', '消费电子', '数字经济',
            '机器人', '工业互联网', '云计算', '大数据', '生物医药'
        ]
        
        # 选股参数
        self.min_industry_stocks = 10  # 行业最少股票数
        self.min_sector_stocks = 5     # 板块最少股票数
        self.min_annual_return = -0.1  # 最小年化收益率
        self.max_drawdown = 0.3       # 最大回撤
        self.min_sharpe = 0.5         # 最小夏普比率
        
        # 回测参数
        self.start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 性能指标参数
        self.top_industries = 3        # 选择前3个行业
        self.sector_rise_days = 5      # 统计板块上涨天数
        
        # 个股筛选参数
        self.pe_range = (0, 100)       # PE范围放宽
        self.pb_range = (0, 15)        # PB范围放宽
        self.roe_min = 5               # 最小ROE降低
        self.max_stocks_per_group = 5  # 每个行业/板块最多选择的股票数
        
        # 技术指标参数
        self.ma_periods = [5, 10, 20]  # 均线周期
        self.volume_ratio = 1.8        # 成交量放大倍数
        
    def calculate_metrics(self, returns):
        """计算性能指标"""
        try:
            if len(returns) == 0:
                return None
                
            # 过滤无效值
            returns = pd.Series(returns).replace([np.inf, -np.inf], np.nan).dropna()
            if len(returns) == 0:
                return None
                
            # 计算年化收益率
            annual_return = np.mean(returns) * 252
            
            # 计算波动率，避免除零
            volatility = np.std(returns) * np.sqrt(252)
            if volatility == 0:
                volatility = 0.0001  # 设置一个很小的非零值
            
            # 计算夏普比率（假设无风险利率为3%）
            risk_free_rate = 0.03
            sharpe = (annual_return - risk_free_rate) / volatility
            
            # 计算最大回撤
            cum_returns = (1 + returns).cumprod()
            rolling_max = np.maximum.accumulate(cum_returns)
            drawdowns = (cum_returns - rolling_max) / rolling_max
            max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
            
            return {
                'annual_return': annual_return,
                'volatility': volatility,
                'sharpe': sharpe,
                'max_drawdown': max_drawdown
            }
            
        except Exception as e:
            self.logger.error(f"计算指标失败: {str(e)}")
            return None
            
    def get_historical_data(self, stock_code, start_date=None, end_date=None):
        """获取历史数据（带缓存）"""
        try:
            # 检查缓存
            cache_key = f"{stock_code}_{start_date}_{end_date}"
            if cache_key in self.data_cache:
                return self.data_cache[cache_key]
            
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(stock_code,
                "date,code,close,volume,amount,turn,pctChg",
                start_date=start_date, 
                end_date=end_date,
                frequency="d", 
                adjustflag="3")
            
            if rs.error_code != '0':
                logging.warning(f"获取股票 {stock_code} 历史数据失败: {rs.error_msg}")
                return None
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                logging.warning(f"股票 {stock_code} 没有历史数据")
                return None
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            # 转换数据类型
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            df['turn'] = pd.to_numeric(df['turn'], errors='coerce')
            df['pctChg'] = pd.to_numeric(df['pctChg'], errors='coerce')
            
            # 处理缺失值
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # 保存到缓存
            self.data_cache[cache_key] = df
            
            return df
            
        except Exception as e:
            logging.warning(f"处理股票 {stock_code} 数据时出错: {str(e)}")
            return None

    def calculate_technical_indicators(self, df):
        """计算技术指标"""
        try:
            df = df.copy()
            # 将字符串转换为数值
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            df['pctChg'] = pd.to_numeric(df['pctChg'], errors='coerce')
            
            # 计算均线
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            # 计算MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Hist'] = df['MACD'] - df['Signal']
            
            # 计算RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # 计算布林带
            df['BB_middle'] = df['close'].rolling(window=20).mean()
            df['BB_upper'] = df['BB_middle'] + 2 * df['close'].rolling(window=20).std()
            df['BB_lower'] = df['BB_middle'] - 2 * df['close'].rolling(window=20).std()
            
            # 计算成交量变化
            df['Volume_MA5'] = df['volume'].rolling(window=5).mean()
            df['Volume_MA10'] = df['volume'].rolling(window=10).mean()
            
            return df
        except Exception as e:
            self.logger.error(f"计算技术指标时出错: {str(e)}")
            return None

    def check_technical_signals(self, df):
        """检查技术指标信号"""
        try:
            if len(df) < 20:  # 确保有足够的数据
                return False
                
            # 获取最新数据和前一天数据
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            prev_2 = df.iloc[-3]

            # 检查均线金叉（5日线从下方突破10日线，且均线都向上）
            ma_trend = (
                prev_2['MA5'] <= prev_2['MA10'] and  # 两天前5日线在10日线下方
                prev['MA5'] <= prev['MA10'] and      # 前一天5日线在10日线下方
                latest['MA5'] > latest['MA10'] and   # 今天5日线突破10日线
                latest['MA5'] > prev['MA5'] and      # 5日线向上
                latest['MA10'] > prev['MA10']        # 10日线向上
            )

            # 如果不满足金叉条件，直接返回False
            if not ma_trend:
                return False

            # 检查MACD信号
            macd_signal = latest['MACD'] > 0 and latest['MACD'] > prev['MACD']

            # 检查RSI信号
            rsi_signal = 30 < latest['RSI'] < 70

            # 检查布林带信号
            bb_signal = latest['close'] > latest['BB_middle']

            # 检查成交量信号
            volume_signal = latest['volume'] > latest['Volume_MA5']

            # 统计满足的信号数量（不包括ma_trend，因为它是必须的）
            signals = [macd_signal, rsi_signal, bb_signal, volume_signal]
            signal_count = sum(signals)

            # 记录调试信息
            self.logger.debug(f"""
技术指标检查结果:
均线金叉: {ma_trend}
- 5日线: {latest['MA5']:.2f} (前值: {prev['MA5']:.2f})
- 10日线: {latest['MA10']:.2f} (前值: {prev['MA10']:.2f})
MACD信号: {macd_signal}
RSI信号: {rsi_signal} (RSI: {latest['RSI']:.2f})
布林带信号: {bb_signal}
成交量信号: {volume_signal}
满足辅助信号数: {signal_count}
""")

            # 必须满足金叉条件，且至少满足一个其他辅助指标
            return ma_trend and signal_count >= 1

        except Exception as e:
            self.logger.error(f"检查技术指标时出错: {str(e)}")
            return False

    def analyze_group_performance(self, stock_codes, start_date=None):
        """分析股票组表现"""
        try:
            # 并行获取数据
            stock_data = {}
            matched_stocks = []  # 存储符合金叉条件的股票
            total_stocks = len(stock_codes)
            processed = 0
            
            for stock in stock_codes:
                try:
                    df = self.get_historical_data(stock, start_date=self.start_date, end_date=self.end_date)
                    if df is not None and len(df) >= 20:  # 需要20天数据计算技术指标
                        # 计算技术指标
                        df = self.calculate_technical_indicators(df)
                        if df is not None:
                            # 检查是否满足金叉条件
                            if self.check_technical_signals(df):
                                matched_stocks.append(stock)
                                stock_data[stock] = df
                                self.logger.info(f"股票 {stock} 满足金叉条件")
                            
                    processed += 1
                    if processed % 50 == 0:
                        self.logger.info(f"已处理 {processed}/{total_stocks} 只股票")
                except Exception as e:
                    self.logger.warning(f"处理股票 {stock} 时出错: {str(e)}")
                    continue
                    
            if not matched_stocks:
                self.logger.warning("没有找到满足金叉条件的股票")
                return None
            
            # 计算整体指标
            total_returns = []
            total_volume = []
            valid_stocks = len(matched_stocks)  # 使用满足金叉条件的股票数量
            
            self.logger.info(f"开始计算 {valid_stocks} 只金叉股票的指标")
            
            for stock_code in matched_stocks:
                try:
                    df = stock_data[stock_code]
                    # 确保数据有效
                    if df is None or len(df) < 5:
                        continue
                        
                    # 计算近期趋势（最近5天的累积收益率）
                    recent_returns = pd.to_numeric(df['pctChg'].tail(5), errors='coerce') / 100
                    # 过滤无效值
                    recent_returns = recent_returns.replace([np.inf, -np.inf], np.nan).dropna()
                    
                    if len(recent_returns) > 0:
                        cumulative_return = (1 + recent_returns).prod() - 1
                        if not pd.isna(cumulative_return) and np.isfinite(cumulative_return):
                            total_returns.append(cumulative_return)
                        
                    # 计算平均成交量（最近5天）
                    recent_volume = pd.to_numeric(df['volume'].tail(5), errors='coerce').mean()
                    if not pd.isna(recent_volume) and recent_volume > 0:
                        total_volume.append(recent_volume)
                        
                except Exception as e:
                    self.logger.warning(f"计算股票 {stock_code} 指标时出错: {str(e)}")
                    continue
                
            # 计算平均指标
            if total_returns:
                # 过滤异常值
                total_returns = np.array(total_returns)
                total_returns = total_returns[np.isfinite(total_returns)]
                avg_return = np.mean(total_returns) if len(total_returns) > 0 else 0
                self.logger.info(f"计算得到 {len(total_returns)} 只金叉股票的收益率")
            else:
                avg_return = 0
                self.logger.warning("没有有效的收益率数据")
                
            if total_volume:
                # 过滤异常值
                total_volume = np.array(total_volume)
                total_volume = total_volume[np.isfinite(total_volume)]
                avg_volume = np.mean(total_volume) if len(total_volume) > 0 else 0
                self.logger.info(f"计算得到 {len(total_volume)} 只金叉股票的成交量")
            else:
                avg_volume = 0
                self.logger.warning("没有有效的成交量数据")
            
            self.logger.info(f"""
指标计算结果:
- 金叉股票数: {valid_stocks}
- 平均收益率: {avg_return:.2%}
- 平均成交量: {avg_volume:.2f}
""")
            
            avg_metrics = {
                'avg_return': avg_return,
                'avg_volume': avg_volume,
                'valid_stocks': valid_stocks,
                'matched_stocks': matched_stocks  # 添加金叉股票列表
            }
            
            return avg_metrics
            
        except Exception as e:
            self.logger.error(f"分析股票组表现出错: {str(e)}")
            return None
        
    def check_performance_criteria(self, metrics):
        """检查是否满足业绩指标要求"""
        if not metrics:
            return False
        
        # 放宽业绩指标要求
        min_return = metrics.get('avg_return', 0) >= -0.15  # 允许更大幅度的下跌
        min_volume = metrics.get('avg_volume', 0) > 100000  # 设置最小成交量门槛
        min_stocks = metrics.get('valid_stocks', 0) >= self.min_industry_stocks
        
        self.logger.info(f"""
检查业绩指标:
- 收益率检查: {min_return} (阈值: -15%, 实际: {metrics.get('avg_return', 0):.2%})
- 成交量检查: {min_volume} (阈值: >10万, 实际: {metrics.get('avg_volume', 0):.2f})
- 股票数量检查: {min_stocks} (阈值: {self.min_industry_stocks}, 实际: {metrics.get('valid_stocks', 0)})
""")
        
        return min_return and min_volume and min_stocks
        
    def layer1_industry_selection(self):
        """第一层：行业筛选"""
        try:
            # 获取行业列表
            industries = self.get_industry_list()
            if not industries:
                self.logger.warning("没有获取到行业列表")
                return []
            
            self.logger.info(f"获取到 {len(industries)} 个行业")
            self.logger.info(f"获取到 {len(self.target_industries)} 个目标行业")
            
            # 分析每个目标行业
            industry_metrics = []
            for industry in self.target_industries:
                # 获取行业股票
                stocks = self.get_industry_stocks(industry)
                if not stocks:
                    self.logger.warning(f"行业 {industry} 没有获取到股票")
                    continue
                    
                self.logger.info(f"行业 {industry} 包含 {len(stocks)} 只股票")
                
                # 分析行业表现
                metrics = self.analyze_group_performance(stocks)
                if metrics and metrics.get('matched_stocks'):  # 只要有符合金叉条件的股票就添加
                    industry_metrics.append({
                        'name': industry,
                        'metrics': metrics,
                        'stocks': stocks,
                        'score': len(metrics['matched_stocks'])  # 得分改为金叉股票数量
                    })
                    self.logger.info(f"行业 {industry} 有 {len(metrics['matched_stocks'])} 只金叉股票")
                    
            # 按照金叉股票数量排序
            selected_industries = sorted(
                industry_metrics,
                key=lambda x: x['score'],
                reverse=True
            )
            
            if not selected_industries:
                self.logger.warning("没有找到符合金叉条件的股票")
            else:
                self.logger.info(f"共找到 {len(selected_industries)} 个有金叉股票的行业")
                for ind in selected_industries:
                    self.logger.info(f"- {ind['name']}: {len(ind['metrics']['matched_stocks'])} 只金叉股票")
                
            return selected_industries
            
        except Exception as e:
            self.logger.error(f"行业筛选失败: {str(e)}")
            return []
        
    def layer2_sector_selection(self):
        """第二层：板块选择"""
        try:
            self.logger.info("开始第二层选股：板块筛选...")
            
            # 获取板块列表
            sectors = self.get_sector_list()
            if not sectors:
                self.logger.warning("没有获取到有效的板块列表")
                return []
            
            self.logger.info(f"获取到 {len(sectors)} 个板块")
            
            # 分析每个板块
            sector_metrics = []
            for sector in sectors:
                try:
                    self.logger.info(f"开始分析板块：{sector}")
                    stocks = self.get_sector_stocks(sector)
                    if len(stocks) < self.min_sector_stocks:
                        self.logger.info(f"板块 {sector} 股票数量 {len(stocks)} 小于最小要求 {self.min_sector_stocks}")
                        continue
                        
                    self.logger.info(f"板块 {sector} 包含 {len(stocks)} 只股票")
                    metrics = self.analyze_group_performance(stocks)
                    
                    if metrics and self.check_performance_criteria(metrics):
                        self.logger.info(f"板块 {sector} 符合性能指标要求")
                        sector_metrics.append({
                            'name': sector,
                            'metrics': metrics,
                            'annual_return': metrics['avg_return'],
                            'score': metrics['valid_stocks'] * (1 + metrics['avg_return'])
                        })
                except Exception as e:
                    self.logger.error(f"处理板块 {sector} 时出错: {str(e)}")
                    continue
            
            # 按照板块得分排序选择前几个板块
            selected_sectors = sorted(
                sector_metrics,
                key=lambda x: x['score'],
                reverse=True
            )[:self.top_industries]
            
            self.logger.info(f"筛选出 {len(selected_sectors)} 个符合条件的板块")
            for sector in selected_sectors:
                self.logger.info(f"板块: {sector['name']}, 得分: {sector['score']:.2f}, 收益率: {sector['annual_return']:.2%}")
            
            return selected_sectors
            
        except Exception as e:
            self.logger.error(f"板块选择失败: {str(e)}")
            return []
        
    def layer3_hybrid_selection(self, industries, sectors):
        """第三层：行业+板块混合选股"""
        self.logger.info("开始第三层选股：行业+板块混合选股...")
        
        hybrid_stocks = []
        
        # 获取行业和板块的股票
        industry_stocks = set()
        sector_stocks = set()
        
        for industry in industries:
            stocks = self.get_industry_stocks(industry['name'])
            industry_stocks.update(stocks)
            
        for sector in sectors:
            stocks = self.get_sector_stocks(sector['name'])
            sector_stocks.update(stocks)
            
        # 找出同时在行业和板块中的股票
        common_stocks = industry_stocks.intersection(sector_stocks)
        
        # 对这些股票进行基本面和技术面筛选
        for stock in common_stocks:
            if self.check_stock_conditions(stock):
                stock_data = self.get_stock_data(stock)
                if stock_data:
                    stock_data['source'] = 'hybrid'
                    hybrid_stocks.append(stock_data)
                    
        return hybrid_stocks[:self.max_stocks_per_group]
        
    def layer4_industry_neutral(self, industries, sectors):
        """第四层：行业中性+板块增强"""
        self.logger.info("开始第四层选股：行业中性+板块增强...")
        
        neutral_stocks = []
        industry_weights = {}
        
        # 计算行业权重
        total_market_cap = 0
        for industry in industries:
            stocks = self.get_industry_stocks(industry['name'])
            industry_cap = 0
            for stock in stocks:
                data = self.get_stock_data(stock)
                if data:
                    industry_cap += data['market_cap']
            industry_weights[industry['name']] = industry_cap
            total_market_cap += industry_cap
            
        # 标准化行业权重
        for industry in industry_weights:
            industry_weights[industry] /= total_market_cap
            
        # 在每个行业中选择受板块增强的股票
        for industry in industries:
            stocks = self.get_industry_stocks(industry['name'])
            industry_selected = []
            
            for stock in stocks:
                if stock in sector_stocks and self.check_stock_conditions(stock):
                    stock_data = self.get_stock_data(stock)
                    if stock_data:
                        stock_data['source'] = f"neutral-{industry['name']}"
                        stock_data['weight'] = industry_weights[industry['name']]
                        industry_selected.append(stock_data)
                        
            # 按照板块动量排序
            industry_selected.sort(key=lambda x: x.get('momentum_score', 0), reverse=True)
            neutral_stocks.extend(industry_selected[:self.max_stocks_per_group])
            
        return neutral_stocks
        
    def run(self):
        """运行策略"""
        try:
            self.logger.info("开始运行策略...")
            
            # 只保留第一层：行业选股
            industries = self.layer1_industry_selection()
            if not industries:
                self.logger.warning("没有找到符合条件的行业")
                error_message = "【推荐股票】❌ 选股失败：未找到符合条件的行业"
                self.ding.send_message(error_message)
                return
            
            # 直接发送行业选股结果
            self.send_simple_result(industries)
            
        except Exception as e:
            self.logger.error(f"策略运行失败: {str(e)}")
            try:
                error_message = f"""【推荐股票】❌ 选股系统运行异常
时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
错误信息：{str(e)}"""
                self.ding.send_message(error_message)
            except:
                self.logger.error("发送错误信息到钉钉也失败了")
        finally:
            # 清理缓存
            self.data_cache.clear()

    def send_simple_result(self, industries):
        """发送简单的选股结果"""
        try:
            message = f"""【推荐股票】A股每日精选
--------------------------------
⏰ 选股时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 选股策略说明：
1. 均线金叉（5日线上穿10日线）
2. 均线系统整体向上
3. 价格站上所有均线
4. MACD/RSI/量能等辅助确认

🏭 选股结果：
"""
            if not industries:
                message += "\n❌ 今日没有符合条件的行业"
            else:
                for industry in industries:
                    matched_stocks = industry['metrics'].get('matched_stocks', [])
                    if matched_stocks:
                        message += f"""
• {industry['name']}
  - 金叉股票数: {len(matched_stocks)}只
  - 平均收益率: {industry['metrics']['avg_return']:.2%}
  - 平均成交量: {industry['metrics']['avg_volume']/10000:.2f}万

  推荐股票:
"""
                        # 显示所有符合条件的股票
                        for stock in matched_stocks:
                            stock_code = stock.replace('.', '')  # 移除股票代码中的点
                            message += f"  · {stock_code}\n"
                    else:
                        message += f"""
• {industry['name']}
  - 暂无满足金叉条件的股票
"""

            message += """
--------------------------------
💡 风险提示：
1. 以上结果仅供参考，不构成投资建议
2. 投资需谨慎，入市需谨慎
--------------------------------"""
            
            self.ding.send_message(message)
            self.logger.info("选股结果已推送到钉钉")
            
        except Exception as e:
            self.logger.error(f"钉钉消息发送失败: {str(e)}")

    def __del__(self):
        """析构函数"""
        try:
            bs.logout()
        except:
            pass

    def get_industry_list(self):
        """获取行业列表"""
        try:
            # 返回所有目标行业
            self.logger.info("获取所有目标行业")
            return self.target_industries
        except Exception as e:
            self.logger.error(f"获取行业列表失败: {str(e)}")
            return []

    def get_industry_stocks(self, industry_name):
        """获取行业成分股列表"""
        try:
            self.logger.info(f"获取行业 {industry_name} 的成分股...")
            rs = bs.query_stock_industry()
            industry_list = []
            
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                if row[3] == industry_name:  # 第4列是行业名称
                    # 获取股票代码
                    stock_code = row[1]  # 第2列是股票代码
                    
                    # 根据股票代码规则添加正确的前缀
                    if stock_code.startswith('6'):
                        stock_code = f'sh.{stock_code}'
                    elif stock_code.startswith(('0', '3')):
                        stock_code = f'sz.{stock_code}'
                        
                    if stock_code.startswith(('sh.', 'sz.')):
                        industry_list.append(stock_code)
                    
            self.logger.info(f"找到 {len(industry_list)} 只股票")
            return industry_list
            
        except Exception as e:
            self.logger.error(f"获取行业成分股失败: {str(e)}")
            return []

    def get_sector_list(self):
        """获取板块列表"""
        try:
            self.logger.info("开始获取板块列表...")
            
            # 使用BaoStock获取板块列表
            rs = bs.query_stock_industry()
            if rs.error_code != '0':
                self.logger.error(f"获取板块列表失败: {rs.error_msg}")
                return []
                
            # 解析结果
            industry_list = []
            while (rs.error_code == '0') & rs.next():
                industry = rs.get_row_data()
                if industry and len(industry) > 2:  # 确保数据格式正确
                    industry_list.append(industry[2])  # 第三列是板块名称
                    
            # 去重
            unique_industries = list(set(industry_list))
            self.logger.info(f"获取到 {len(unique_industries)} 个板块")
            
            return unique_industries
            
        except Exception as e:
            self.logger.error(f"获取板块列表时出错: {str(e)}")
            return []

    def get_sector_stocks(self, sector_name):
        """获取板块成分股"""
        try:
            rs = bs.query_stock_industry()
            stocks = []
            while (rs.error_code == '0') & rs.next():
                row = rs.get_row_data()
                if row[4] == sector_name:  # 概念板块名称匹配
                    code = row[1]
                    if code.startswith('sh.6') or code.startswith('sz.00') or code.startswith('sz.300'):
                        stocks.append(code)
            self.logger.info(f"板块 {sector_name} 包含 {len(stocks)} 只股票")
            return stocks
        except Exception as e:
            self.logger.error(f"获取板块 {sector_name} 成分股失败: {str(e)}")
            return []

    def get_stock_data(self, stock_code):
        """获取个股数据"""
        try:
            # 获取最新交易日数据
            rs = bs.query_history_k_data_plus(
                stock_code,
                "date,code,close,volume,amount,turn,peTTM,pbMRQ,roeMRQ",
                start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d'),
                frequency="d",
                adjustflag="3"
            )
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                
            if not data_list:
                return None
                
            df = pd.DataFrame(data_list, columns=['date','code','close','volume','amount','turn','peTTM','pbMRQ','roeMRQ'])
            for col in ['close','volume','amount','turn','peTTM','pbMRQ','roeMRQ']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            latest = df.iloc[-1]
            
            # 计算市值（以亿为单位）
            market_cap = latest['close'] * float(latest['volume']) / latest['turn'] * 100 / 100000000
            
            # 计算动量得分
            df['returns'] = df['close'].pct_change()
            momentum_score = df['returns'].mean() / df['returns'].std() if len(df) > 1 else 0
            
            return {
                'code': stock_code,
                'price': latest['close'],
                'pe': latest['peTTM'],
                'pb': latest['pbMRQ'],
                'roe': latest['roeMRQ'],
                'market_cap': market_cap,
                'momentum_score': momentum_score
            }
            
        except Exception as e:
            self.logger.error(f"获取股票 {stock_code} 数据失败: {str(e)}")
            return None

    def check_stock_conditions(self, stock_code):
        """检查股票是否满足基本面条件"""
        try:
            stock_data = self.get_stock_data(stock_code)
            if not stock_data:
                return False
            
            # 检查基本面指标
            if not (self.pe_range[0] <= stock_data['pe'] <= self.pe_range[1]):
                return False
            if not (self.pb_range[0] <= stock_data['pb'] <= self.pb_range[1]):
                return False
            if stock_data['roe'] < self.roe_min:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查股票 {stock_code} 条件失败: {str(e)}")
            return False

if __name__ == "__main__":
    strategy = AdvancedFactorStrategy()
    strategy.run()