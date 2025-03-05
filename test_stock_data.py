import baostock as bs
import pandas as pd
import numpy as np
from stockquant.market import Market
import logging
from datetime import datetime, timedelta
import time

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('stock_data_test.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def test_stock_data():
    """测试股票数据获取"""
    logger = setup_logging()
    market = Market()
    
    # 测试股票列表
    stock_codes = [
        {"baostock": "sz.300616", "sina": "sz300616", "name": "尚品宅配"},
        {"baostock": "sh.600519", "sina": "sh600519", "name": "贵州茅台"},
        {"baostock": "sz.000001", "sina": "sz000001", "name": "平安银行"},
        {"baostock": "sh.601318", "sina": "sh601318", "name": "中国平安"}
    ]
    
    # 连接BaoStock
    logger.info("连接BaoStock...")
    bs_result = bs.login()
    if bs_result.error_code != '0':
        logger.error(f"BaoStock连接失败: {bs_result.error_msg}")
        return
    logger.info(f"BaoStock连接成功: {bs_result.error_code} {bs_result.error_msg}")
    
    try:
        # 测试每个股票
        for stock in stock_codes:
            logger.info(f"\n测试股票: {stock['name']} ({stock['baostock']})")
            
            # 1. 测试新浪实时数据
            try:
                logger.info(f"获取新浪实时数据: {stock['sina']}")
                price_info = market.sina.get_realtime_data(stock['sina'])
                if price_info:
                    logger.info(f"实时数据: 价格={price_info['price']}, 成交量={price_info['volume']}, 名称={price_info['name']}")
                else:
                    logger.error("获取实时数据失败")
            except Exception as e:
                logger.error(f"获取实时数据出错: {str(e)}")
            
            # 2. 测试BaoStock历史数据
            try:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                logger.info(f"获取BaoStock历史数据: {stock['baostock']}, 开始日期: {start_date}, 结束日期: {end_date}")
                
                rs = bs.query_history_k_data_plus(
                    stock['baostock'],
                    "date,code,open,high,low,close,volume",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"  # 复权类型，3表示不复权
                )
                
                if rs.error_code != '0':
                    logger.error(f"获取历史数据失败: {rs.error_msg}")
                    continue
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                logger.info(f"成功获取到 {len(data_list)} 条历史数据")
                
                if data_list:
                    # 转换为DataFrame
                    df = pd.DataFrame(data_list, columns=['date', 'code', 'open', 'high', 'low', 'close', 'volume'])
                    # 转换数据类型
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    # 打印最新数据
                    latest = df.iloc[-1]
                    logger.info(f"最新历史数据: 日期={latest['date']}, 收盘价={latest['close']}, 成交量={latest['volume']}")
                    
                    # 计算简单技术指标
                    df['ma5'] = df['close'].rolling(window=5).mean()
                    df['ma10'] = df['close'].rolling(window=10).mean()
                    
                    if len(df) >= 10:
                        latest_ma = df.iloc[-1]
                        logger.info(f"技术指标: MA5={latest_ma['ma5']:.2f}, MA10={latest_ma['ma10']:.2f}")
                        
                        # 判断金叉/死叉
                        if df['ma5'].iloc[-1] > df['ma10'].iloc[-1] and df['ma5'].iloc[-2] <= df['ma10'].iloc[-2]:
                            logger.info("MA5上穿MA10，形成金叉")
                        elif df['ma5'].iloc[-1] < df['ma10'].iloc[-1] and df['ma5'].iloc[-2] >= df['ma10'].iloc[-2]:
                            logger.info("MA5下穿MA10，形成死叉")
            except Exception as e:
                logger.error(f"获取历史数据出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # 暂停一秒，避免请求过快
            time.sleep(1)
    
    finally:
        # 登出BaoStock
        bs.logout()
        logger.info("BaoStock登出成功")

if __name__ == "__main__":
    test_stock_data() 