import baostock as bs
import tushare as ts
from stockquant.market import Market
import pandas as pd
import logging
from datetime import datetime, timedelta
import time

class DataFetcher:
    def __init__(self, config=None):
        """初始化数据获取器"""
        self.setup_logging()
        self.market = Market()
        self.connect_apis(config)
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/data_fetcher.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def connect_apis(self, config):
        """连接各数据源API"""
        try:
            # 连接BaoStock
            bs_result = bs.login()
            if bs_result.error_code != '0':
                self.logger.error(f"BaoStock连接失败: {bs_result.error_msg}")
                raise Exception("BaoStock连接失败")
            self.logger.info("BaoStock连接成功")
            
            # 设置Tushare token
            if config and 'tushare_token' in config:
                ts.set_token(config['tushare_token'])
                self.pro = ts.pro_api()
                self.logger.info("Tushare API初始化成功")
            else:
                self.logger.warning("未提供Tushare token，部分功能可能受限")
                self.pro = None
                
        except Exception as e:
            self.logger.error(f"API连接失败: {str(e)}")
            raise
            
    def get_realtime_data(self, stock_code, max_retries=3):
        """获取实时数据"""
        for retry in range(max_retries):
            try:
                price_info = self.market.sina.get_realtime_data(stock_code)
                if price_info:
                    return price_info
                time.sleep(retry + 1)
            except Exception as e:
                self.logger.error(f"获取实时数据失败 (尝试 {retry+1}/{max_retries}): {str(e)}")
                if retry < max_retries - 1:
                    time.sleep(retry + 1)
        return None
        
    def get_history_data(self, stock_code, start_date=None, end_date=None, max_retries=3):
        """获取历史数据"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        for retry in range(max_retries):
            try:
                rs = bs.query_history_k_data_plus(
                    stock_code,
                    "date,code,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"
                )
                
                if rs.error_code != '0':
                    self.logger.warning(f"获取历史数据失败 (尝试 {retry+1}/{max_retries}): {rs.error_msg}")
                    if retry < max_retries - 1:
                        time.sleep(retry + 1)
                        continue
                    return None
                    
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                    
                if not data_list:
                    self.logger.warning(f"股票 {stock_code} 没有历史数据")
                    return None
                    
                df = pd.DataFrame(data_list, columns=rs.fields)
                # 转换数据类型
                for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                return df
                
            except Exception as e:
                self.logger.error(f"获取历史数据出错 (尝试 {retry+1}/{max_retries}): {str(e)}")
                if retry < max_retries - 1:
                    time.sleep(retry + 1)
                    
        return None
        
    def get_fundamental_data(self, stock_code):
        """获取基本面数据"""
        if not self.pro:
            self.logger.warning("Tushare API未初始化，无法获取基本面数据")
            return None
            
        try:
            # 获取基本信息
            basic = self.pro.daily_basic(ts_code=stock_code)
            if basic is None or basic.empty:
                return None
                
            # 获取财务指标
            financial = self.pro.fina_indicator(ts_code=stock_code)
            if financial is not None and not financial.empty:
                basic = pd.merge(basic, financial, on='ts_code', how='left')
                
            return basic
            
        except Exception as e:
            self.logger.error(f"获取基本面数据失败: {str(e)}")
            return None
            
    def __del__(self):
        """清理资源"""
        try:
            bs.logout()
            self.logger.info("BaoStock已登出")
        except:
            pass 