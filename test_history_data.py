import baostock as bs
import pandas as pd
import time
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_history.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_historical_data(stock_code, start_date=None, end_date=None, max_retries=3):
    """获取历史数据（带重试机制）"""
    try:
        # 标准化股票代码格式
        if not stock_code.startswith(('sh.', 'sz.')):
            if stock_code.startswith('6'):
                stock_code = f'sh.{stock_code}'
            elif stock_code.startswith(('0', '3')):
                stock_code = f'sz.{stock_code}'
            logger.info(f"股票代码已标准化为: {stock_code}")
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 添加重试机制
        for retry in range(max_retries):
            try:
                # 添加重试延迟，避免频率限制
                if retry > 0:
                    logger.info(f"重试获取 {stock_code} 数据，第 {retry+1}/{max_retries} 次")
                    time.sleep(1 * retry)  # 第一次重试等待1秒，第二次等待2秒...
                
                rs = bs.query_history_k_data_plus(stock_code,
                    "date,code,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=start_date, 
                    end_date=end_date,
                    frequency="d", 
                    adjustflag="3")
                
                if rs.error_code != '0':
                    logger.warning(f"获取股票 {stock_code} 历史数据失败 (尝试 {retry+1}/{max_retries}): {rs.error_msg}")
                    continue  # 尝试重试
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if not data_list:
                    logger.warning(f"股票 {stock_code} 没有历史数据 (尝试 {retry+1}/{max_retries})")
                    if retry < max_retries - 1:
                        continue  # 尝试重试
                    return None
                
                logger.info(f"成功获取 {stock_code} 历史数据，共 {len(data_list)} 条记录")
                
                df = pd.DataFrame(data_list, columns=rs.fields)
                # 转换数据类型
                for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                return df
                
            except Exception as e:
                logger.warning(f"处理股票 {stock_code} 数据时出错 (尝试 {retry+1}/{max_retries}): {str(e)}")
                if retry < max_retries - 1:
                    time.sleep(1 * retry)  # 添加延迟
                    continue
        
        return None  # 所有重试都失败
            
    except Exception as e:
        logger.warning(f"处理股票 {stock_code} 数据时出错: {str(e)}")
        return None

def test_stocks():
    """测试多只股票的历史数据获取"""
    # 连接BaoStock
    logger.info("连接BaoStock...")
    bs.login()
    
    try:
        # 测试股票列表
        test_stocks = [
            'sh.600519',  # 贵州茅台
            'sh.601398',  # 工商银行
            'sz.000001',  # 平安银行
            'sz.300750',  # 宁德时代
            '600036',     # 招商银行（测试自动添加前缀）
            '000858',     # 五粮液（测试自动添加前缀）
            'sh.603906',  # 测试一个可能没有历史数据的股票
        ]
        
        success_count = 0
        for stock in test_stocks:
            logger.info(f"测试获取 {stock} 的历史数据...")
            df = get_historical_data(stock)
            
            if df is not None and len(df) > 0:
                logger.info(f"成功获取 {stock} 数据，共 {len(df)} 条记录")
                logger.info(f"最新收盘价: {df['close'].iloc[-1]}")
                success_count += 1
            else:
                logger.warning(f"获取 {stock} 数据失败")
        
        logger.info(f"测试完成，成功率: {success_count}/{len(test_stocks)}")
        
    finally:
        # 登出BaoStock
        bs.logout()
        logger.info("BaoStock登出成功")

if __name__ == "__main__":
    test_stocks() 