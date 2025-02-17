# from stockquant.market import Market
# from stockquant.message import DingTalk
# from stockquant.utils.logger import logger
# from datetime import datetime, timedelta
# import tushare as ts
# import json
# import os


# class StockChooser:
#     def __init__(self):
#         self.market = Market()
#         self.ding = DingTalk()
        
#         # 读取配置文件
#         config_path = os.path.join(os.path.dirname(__file__), 'docs/config.json')
#         with open(config_path, 'r') as f:
#             self.config = json.load(f)
        
#         # 初始化 Tushare
#         ts.set_token(self.config['TUSHARE']['token'])
#         self.pro = ts.pro_api()
        
#         # 选股参数设置
#         self.MAX_PRICE = 30     # 股价上限
#         self.MIN_VOLUME = 1000  # 最小成交量(万)
#         self.UP_PERCENT = 5     # 涨幅限制(%)

#     def get_stock_data(self, stock_code):
#         """获取单个股票数据"""
#         try:
#             # 使用 Tushare 获取实时数据
#             code = stock_code[2:] + '.'+stock_code[:2].upper()  # 转换格式，如 sh600000 转为 600000.SH
#             df = self.pro.daily(ts_code=code, trade_date=datetime.now().strftime('%Y%m%d'))
#             if df.empty:
#                 return None
                
#             return {
#                 'code': stock_code,
#                 'name': self.get_stock_name(code),
#                 'price': float(df.iloc[0]['close']),
#                 'close': float(df.iloc[0]['pre_close']),
#                 'volume': float(df.iloc[0]['vol'] * 100),  # 转换为股
#                 'amount': float(df.iloc[0]['amount'] * 1000)  # 转换为元
#             }
#         except Exception as e:
#             logger.error(f"获取股票{stock_code}数据失败: {str(e)}")
#             return None
            
#     def get_stock_name(self, ts_code):
#         """获取股票名称"""
#         try:
#             df = self.pro.stock_basic(ts_code=ts_code, fields='name')
#             return df.iloc[0]['name']
#         except:
#             return ts_code

#     def check_stock_condition(self, price_info):
#         """
#         选股条件判断
#         :param price_info: 股票数据
#         :return: True 满足条件，False 不满足条件
#         """
#         try:
#             if not price_info:
#                 return False
                
#             # 计算涨跌幅
#             price_change = (price_info['price'] - price_info['close']) / price_info['close'] * 100
            
#             # 选股条件：
#             # 1. 股价低于设定价格
#             # 2. 成交量大于设定值
#             # 3. 涨幅在设定范围内
#             if (price_info['price'] <= self.MAX_PRICE and 
#                 price_info['volume'] >= self.MIN_VOLUME * 10000 and 
#                 0 <= price_change <= self.UP_PERCENT):
#                 return True
#             return False
            
#         except Exception as e:
#             logger.error(f"选股条件判断出错: {str(e)}")
#             return False

#     def run(self):
#         """运行选股程序"""
#         try:
#             # 获取所有股票列表
#             # 使用 Tushare 获取股票列表替代 market.stocks_list()
#             df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol')
#             if df.empty:
#                 error_msg = "【小火箭】获取股票列表失败"
#                 logger.error(error_msg)
#                 self.ding.send_message(error_msg)
#                 return
            
#             stock_list = []
#             for _, row in df.iterrows():
#                 # 转换为 sh/sz 开头的格式
#                 prefix = 'sh' if row['ts_code'].endswith('.SH') else 'sz'
#                 symbol = prefix + row['symbol']
#                 stock_list.append(symbol)

#             # 符合条件的股票列表
#             matched_stocks = []
            
#             # 遍历股票列表
#             for stock in stock_list:
#                 try:
#                     # 获取股票数据
#                     price_info = self.get_stock_data(stock)
#                     if not price_info:
#                         continue

#                     # 判断是否符合条件
#                     if self.check_stock_condition(price_info):
#                         matched_stocks.append({
#                             'code': stock,
#                             'name': price_info['name'],
#                             'price': price_info['price'],
#                             'volume': price_info['volume'],
#                             'amount': price_info['amount']
#                         })

#                 except Exception as e:
#                     logger.error(f"处理股票 {stock} 时出错: {str(e)}")
#                     continue

#             # 发送选股结果
#             if matched_stocks:
#                 message = f"""【小火箭】选股结果播报
# --------------------------------
# 选股时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 选股条件:
# 1. 股价 <= {self.MAX_PRICE}元
# 2. 成交量 >= {self.MIN_VOLUME}万
# 3. 涨幅 0~{self.UP_PERCENT}%
# --------------------------------
# 符合条件的股票:
# """
#                 for stock in matched_stocks:
#                     message += f"""
# {stock['name']}({stock['code']})
# 当前价格: {stock['price']}元
# 成交量: {stock['volume']/10000:.2f}万
# 成交额: {stock['amount']/10000:.2f}万
# --------------------------------"""
                
#                 print(message)
#                 self.ding.send_message(message)
#             else:
#                 message = f"""【小火箭】选股结果播报
# --------------------------------
# 当前没有符合条件的股票
# 选股条件:
# 1. 股价 <= {self.MAX_PRICE}元
# 2. 成交量 >= {self.MIN_VOLUME}万
# 3. 涨幅 0~{self.UP_PERCENT}%
# --------------------------------"""
#                 print(message)
#                 self.ding.send_message(message)

#         except Exception as e:
#             error_msg = f"【小火箭】选股程序运行出错: {str(e)}"
#             logger.error(error_msg)
#             self.ding.send_message(error_msg)


# if __name__ == '__main__':
#     chooser = StockChooser()
#     chooser.run()




from stockquant.market import Market
from stockquant.message import DingTalk
from stockquant.utils.logger import logger
from datetime import datetime, timedelta
import tushare as ts
import json
import os


class StockChooser:
    def __init__(self):
        self.market = Market()
        self.ding = DingTalk()
        
        # 读取配置文件
        config_path = os.path.join(os.path.dirname(__file__), 'docs/config.json')
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # 初始化 Tushare
        ts.set_token(self.config['TUSHARE']['token'])
        self.pro = ts.pro_api()
        
        # 优化选股参数设置
        self.MAX_PRICE = 50        # 提高股价上限到50元
        self.MIN_VOLUME = 500      # 降低最小成交量到500万
        self.UP_PERCENT = 7        # 扩大涨幅范围到7%
        self.MIN_TURNOVER = 2      # 降低最低换手率到2%
        self.MIN_CIRC_MV = 30000   # 降低最小流通市值到30亿
        self.MAX_CIRC_MV = 800000  # 提高最大流通市值到800亿

    def get_stock_data(self, stock_code):
        """获取股票数据（含基本面指标）"""
        try:
            # 首先尝试使用 Tushare 获取数据
            code = stock_code[2:] + '.' + stock_code[:2].upper()
            trade_date = datetime.now().strftime('%Y%m%d')
            
            try:
                # 获取日线数据
                df_daily = self.pro.daily(ts_code=code, trade_date=trade_date)
                if not df_daily.empty:
                    # 获取基本面数据
                    df_basic = self.pro.daily_basic(
                        ts_code=code, 
                        trade_date=trade_date,
                        fields='turnover_rate,circ_mv'
                    )
                    
                    if not df_basic.empty:
                        return {
                            'code': stock_code,
                            'name': self.get_stock_name(code),
                            'price': float(df_daily.iloc[0]['close']),
                            'close': float(df_daily.iloc[0]['pre_close']),
                            'volume': float(df_daily.iloc[0]['vol'] * 100),  # 转换为股
                            'amount': float(df_daily.iloc[0]['amount'] * 1000),  # 转换为元
                            'turnover_rate': float(df_basic.iloc[0]['turnover_rate']),
                            'circ_mv': float(df_basic.iloc[0]['circ_mv'])
                        }
            except Exception as e:
                logger.warning(f"Tushare数据获取失败，尝试使用新浪数据源: {str(e)}")
            
            # 如果Tushare获取失败，使用新浪数据源作为备用
            sina_data = self.market.sina.get_realtime_data(stock_code)
            if sina_data:
                # 计算换手率和流通市值
                try:
                    stock_basic = self.pro.stock_basic(ts_code=code, fields='total_share')
                    if not stock_basic.empty:
                        total_share = float(stock_basic.iloc[0]['total_share']) * 10000  # 转换为股
                        circ_mv = sina_data['price'] * total_share
                        turnover_rate = (sina_data['volume'] / total_share) * 100
                    else:
                        circ_mv = 0
                        turnover_rate = 0
                except:
                    circ_mv = 0
                    turnover_rate = 0
                    
                return {
                    'code': stock_code,
                    'name': sina_data['name'],
                    'price': float(sina_data['price']),
                    'close': float(sina_data['close']),
                    'volume': float(sina_data['volume']),
                    'amount': float(sina_data['amount']),
                    'turnover_rate': turnover_rate,
                    'circ_mv': circ_mv
                }
            
            logger.error(f"获取股票{stock_code}数据失败: 所有数据源均无法获取数据")
            return None
        
        except Exception as e:
            logger.error(f"获取股票{stock_code}数据失败: {str(e)}")
            return None

    def get_stock_name(self, ts_code):
        """获取股票名称"""
        try:
            # 首先尝试从缓存获取
            if hasattr(self, '_stock_names') and ts_code in self._stock_names:
                return self._stock_names[ts_code]
            
            # 如果缓存中没有，则从Tushare获取
            df = self.pro.stock_basic(ts_code=ts_code, fields='name')
            if not df.empty:
                name = df.iloc[0]['name']
                # 缓存股票名称
                if not hasattr(self, '_stock_names'):
                    self._stock_names = {}
                self._stock_names[ts_code] = name
                return name
            
            return ts_code
        except:
            return ts_code

    def check_stock_condition(self, price_info):
        """优化后的选股条件判断"""
        try:
            if not price_info:
                return False
                
            # 计算涨跌幅
            price_change = (price_info['price'] - price_info['close']) / price_info['close'] * 100
            
            # 分步判断条件，便于调试
            price_condition = price_info['price'] <= self.MAX_PRICE
            volume_condition = price_info['volume'] >= self.MIN_VOLUME * 10000
            change_condition = -1 <= price_change <= self.UP_PERCENT  # 允许小幅回调
            turnover_condition = price_info['turnover_rate'] >= self.MIN_TURNOVER
            mv_condition = self.MIN_CIRC_MV <= price_info['circ_mv'] <= self.MAX_CIRC_MV
            
            # 记录不满足的条件，方便调试
            if not any([price_condition, volume_condition, change_condition, turnover_condition, mv_condition]):
                logger.debug(f"股票{price_info['code']}不满足条件：")
                logger.debug(f"价格条件: {price_condition}, 当前价格: {price_info['price']}")
                logger.debug(f"成交量条件: {volume_condition}, 当前成交量: {price_info['volume']/10000}万")
                logger.debug(f"涨跌幅条件: {change_condition}, 当前涨跌幅: {price_change:.2f}%")
                logger.debug(f"换手率条件: {turnover_condition}, 当前换手率: {price_info['turnover_rate']}%")
                logger.debug(f"市值条件: {mv_condition}, 当前流通市值: {price_info['circ_mv']/10000:.2f}亿")
            
            return all([
                price_condition,
                volume_condition,
                change_condition,
                turnover_condition,
                mv_condition
            ])
            
        except Exception as e:
            logger.error(f"选股条件判断出错: {str(e)}")
            return False

    def run(self):
        """运行选股程序"""
        try:
            # 获取股票列表并排除ST股
            df = self.pro.stock_basic(
                exchange='', 
                list_status='L', 
                fields='ts_code,symbol,name'
            )
            if df.empty:
                error_msg = "【小火箭】获取股票列表失败"
                logger.error(error_msg)
                self.ding.send_message(error_msg)
                return
            
            stock_list = []
            for _, row in df.iterrows():
                if 'ST' in row['name']:
                    continue  # 排除ST股票
                prefix = 'sh' if row['ts_code'].endswith('.SH') else 'sz'
                stock_list.append(f"{prefix}{row['symbol']}")

            # 筛选符合条件的股票
            matched_stocks = []
            for stock in stock_list:
                try:
                    price_info = self.get_stock_data(stock)
                    if self.check_stock_condition(price_info):
                        matched_stocks.append({
                            'code': stock,
                            'name': price_info['name'],
                            'price': price_info['price'],
                            'volume': price_info['volume'],
                            'amount': price_info['amount'],
                            'turnover': price_info['turnover_rate'],
                            'circ_mv': price_info['circ_mv']
                        })
                except Exception as e:
                    logger.error(f"处理股票 {stock} 时出错: {str(e)}")
                    continue

            # 格式化输出结果
            condition_desc = f"""
1. 股价 <= {self.MAX_PRICE}元
2. 成交量 >= {self.MIN_VOLUME}万
3. 涨幅 0~{self.UP_PERCENT}%
4. 换手率 >= {self.MIN_TURNOVER}%
5. 流通市值 {self.MIN_CIRC_MV/10000:.0f}亿~{self.MAX_CIRC_MV/10000:.0f}亿
--------------------------------"""
            
            if matched_stocks:
                message = f"""【小火箭】选股结果播报
--------------------------------
选股时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
选股条件:{condition_desc}
符合条件股票({len(matched_stocks)}只):"""
                for stock in matched_stocks:
                    message += f"""
{stock['name']}({stock['code']})
当前价格: {stock['price']:.2f}元
成交量: {stock['volume']/10000:.2f}万
换手率: {stock['turnover']:.2f}%
流通市值: {stock['circ_mv']/10000:.2f}亿
--------------------------------"""
            else:
                message = f"""【小火箭】选股结果播报
--------------------------------
当前没有符合条件的股票
选股条件:{condition_desc}"""
            
            print(message)
            self.ding.send_message(message)

        except Exception as e:
            error_msg = f"【小火箭】选股程序运行出错: {str(e)}"
            logger.error(error_msg)
            self.ding.send_message(error_msg)


if __name__ == '__main__':
    chooser = StockChooser()
    chooser.run()