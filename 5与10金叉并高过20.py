from stockquant.market import Market
from stockquant.message import DingTalk
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import baostock as bs

class MACrossScreener:
    def __init__(self):
        self.market = Market()
        self.ding = DingTalk()  # 创建钉钉实例用于推送消息
        self.setup_logging()
        
        # 登录 baostock
        bs_result = bs.login()
        if bs_result.error_code != '0':
            self.logger.error(f'baostock 登录失败: {bs_result.error_msg}')
        else:
            self.logger.info('baostock 登录成功')
        
        # 测试股票池
        self.test_stocks = self.get_all_stock()
        
    def __del__(self):
        """析构函数，确保退出时登出 baostock"""
        try:
            bs.logout()
            self.logger.info('baostock 已登出')
        except:
            pass

    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ma_cross_screen.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def convert_stock_code(self, stock_code):
        """转换股票代码为 baostock 格式"""
        # 从 'sh600000' 转换为 'sh.600000'
        if len(stock_code) < 8:
            return None
        market = stock_code[:2].lower()
        code = stock_code[2:]
        return f"{market}.{code}"

    def get_ma_data(self, stock_code):
        """获取均线数据"""
        try:
            # 获取实时数据
            price_info = self.market.sina.get_realtime_data(stock_code)
            if not price_info:
                return None
                
            # 转换股票代码格式
            bs_stock_code = self.convert_stock_code(stock_code)
            if not bs_stock_code:
                self.logger.error(f"股票代码格式转换失败: {stock_code}")
                return None
                
            # 获取历史K线数据（使用baostock）
            end_date = datetime.now().strftime('%Y-%m-%d')
            rs = bs.query_history_k_data_plus(bs_stock_code,
                "date,code,close",
                start_date='2023-01-01',
                end_date=end_date,
                frequency="d",
                adjustflag="3"  # 复权类型，3表示后复权
            )
            
            if rs.error_code != '0':
                self.logger.error(f"获取K线数据失败: {rs.error_msg}")
                return None
                
            # 转换数据为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return None
                
            # 计算均线
            df = pd.DataFrame(data_list, columns=['date','code','close'])
            df['close'] = df['close'].astype(float)
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            if len(df) < 20:  # 确保有足够的数据计算均线
                return None
                
            # 获取最新数据
            current_price = float(price_info['price'])
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
            ma20_above_price = data['MA20'] > data['price']
            
            # 记录日志
            self.logger.info(f"\n检查股票 {data['name']}({data['code']}) 的均线信号：")
            self.logger.info(f"当前价格: {data['price']:.2f}")
            self.logger.info(f"5日均线: {data['MA5']:.2f}")
            self.logger.info(f"10日均线: {data['MA10']:.2f}")
            self.logger.info(f"20日均线: {data['MA20']:.2f}")
            self.logger.info(f"是否金叉: {'是' if golden_cross else '否'}")
            self.logger.info(f"20日线是否高于当前价: {'是' if ma20_above_price else '否'}")
            
            return golden_cross and ma20_above_price
            
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
                    stock_data = self.get_ma_data(stock_code)
                    if not stock_data:
                        continue
                        
                    # 检查均线信号
                    if self.check_ma_signal(stock_data):
                        matched_stocks.append({
                            'code': stock_data['code'],
                            'name': stock_data['name'],
                            'price': stock_data['price'],
                            'MA5': stock_data['MA5'],
                            'MA10': stock_data['MA10'],
                            'MA20': stock_data['MA20']
                        })
                        self.logger.info(f"发现符合条件的股票：{stock_data['name']}({stock_code})")
                        
                except Exception as e:
                    self.logger.error(f"处理股票 {stock_code} 时出错: {str(e)}")
                    continue
            
            # 构建推送消息
            if matched_stocks:
                message = f"""【推荐股票】均线金叉选股结果
--------------------------------
选股时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
选股条件:
1. 5日均线上穿10日均线（金叉）
2. 20日均线高于当前价格
--------------------------------
符合条件的股票:
"""
                for stock in matched_stocks:
                    message += f"""
{stock['name']}({stock['code']})
当前价格: {stock['price']:.2f}
5日均线: {stock['MA5']:.2f}
10日均线: {stock['MA10']:.2f}
20日均线: {stock['MA20']:.2f}
--------------------------------"""
                
                # 推送到钉钉
                self.ding.send_message(message)
                self.logger.info("选股结果已推送到钉钉")
            else:
                message = """【推荐股票】均线金叉选股结果
--------------------------------
当前没有符合条件的股票
选股条件:
1. 5日均线上穿10日均线（金叉）
2. 20日均线高于当前价格
--------------------------------"""
                self.ding.send_message(message)
                self.logger.info("没有找到符合条件的股票，已推送消息")
                
            return matched_stocks
            
        except Exception as e:
            error_msg = f"选股程序运行出错: {str(e)}"
            self.logger.error(error_msg)
            self.ding.send_message(f"【错误提醒】{error_msg}")
            return []

    def get_all_stock(self):
        """获取测试股票列表"""
        return [
            'sz000099',  # 中信海直
            'sz002085',  # 万丰奥威
            'sh688776',  # 国光电气
            'sz000969',  # 安泰科技
            'sz002173',  # 创新医疗
            'sz301293',  # 三博脑科
            'sh688027',  # 国盾量子
            'sz300520',  # 科大国创
            'sz002882',  # 金龙羽
            'sh603200',  # 上海洗霸 
            'sz301230',  # 泓博医药
            'sh688222',  # 成都先导 
            'sx000725',  # 航天晨光 
            'sz300053',  # 欧比特 
            'sz301301',  # 川宁生物 
            'sh688089',  # 嘉必优 
            'sz300423',  # 昇辉科技 
            'sz300540',  # 蜀道装备 
            'sh688328',  # 深科达 

        ]


if __name__ == "__main__":
    screener = MACrossScreener()
    screener.screen_stocks()