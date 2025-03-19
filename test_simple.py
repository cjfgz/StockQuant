import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
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
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 添加重试机制
        for retry in range(max_retries):
            try:
                # 添加重试延迟，避免频率限制
                if retry > 0:
                    logger.info(f"重试获取 {stock_code} 数据，第 {retry+1}/{max_retries} 次")
                    import time
                    time.sleep(1 * retry)  # 第一次重试等待1秒，第二次等待2秒...
                
                # 登录BaoStock
                bs.login()
                
                rs = bs.query_history_k_data_plus(stock_code,
                    "date,code,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=start_date, 
                    end_date=end_date,
                    frequency="d", 
                    adjustflag="3")
                
                if rs.error_code != '0':
                    logger.warning(f"获取股票 {stock_code} 历史数据失败 (尝试 {retry+1}/{max_retries}): {rs.error_msg}")
                    bs.logout()
                    continue  # 尝试重试
                
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                
                if not data_list:
                    logger.warning(f"股票 {stock_code} 没有历史数据 (尝试 {retry+1}/{max_retries})")
                    bs.logout()
                    if retry < max_retries - 1:
                        continue  # 尝试重试
                    return None
                
                logger.info(f"成功获取 {stock_code} 历史数据，共 {len(data_list)} 条记录")
                
                df = pd.DataFrame(data_list, columns=rs.fields)
                
                # 直接转换数据类型
                numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']
                for col in numeric_cols:
                    if col in df.columns:
                        logger.info(f"转换列 {col} 的数据类型，原始类型: {df[col].dtype}")
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        logger.info(f"转换后类型: {df[col].dtype}")
                
                # 检查数据是否足够
                min_days = 10  # 降低到10天，因为大多数股票只有11天的数据
                if len(df) < min_days:
                    logger.warning(f"数据交易日不足 {len(df)} < {min_days}")
                    bs.logout()
                    if retry < max_retries - 1:
                        continue  # 尝试重试
                    return None
                
                # 检查是否有无效数据
                for col in ['close', 'volume']:
                    if col in df.columns:
                        # 检查是否有空值
                        if df[col].isnull().any():
                            logger.warning(f"数据中存在空值: {col}")
                            bs.logout()
                            if retry < max_retries - 1:
                                continue  # 尝试重试
                            return None
                        
                        # 检查是否有非正值
                        non_positive = (df[col] <= 0)
                        if non_positive.any():
                            logger.warning(f"数据中存在非正值: {col}")
                            bs.logout()
                            if retry < max_retries - 1:
                                continue  # 尝试重试
                            return None
                
                # 登出BaoStock
                bs.logout()
                
                return df
                
            except Exception as e:
                logger.warning(f"处理股票 {stock_code} 数据时出错 (尝试 {retry+1}/{max_retries}): {str(e)}")
                try:
                    bs.logout()
                except:
                    pass
                if retry < max_retries - 1:
                    import time
                    time.sleep(1 * retry)  # 添加延迟
                    continue
        
        return None  # 所有重试都失败
            
    except Exception as e:
        logger.warning(f"处理股票 {stock_code} 数据时出错: {str(e)}")
        try:
            bs.logout()
        except:
            pass
        return None

def calculate_metrics(df):
    """计算技术指标和性能指标"""
    try:
        # 确保数据框已经过验证
        if df is None:
            logger.warning("数据为空，无法计算指标")
            return None
            
        # 创建一个副本以避免警告
        df = df.copy()
            
        # 计算每日收益率
        logger.info("计算每日收益率")
        df.loc[:, 'return'] = df['close'].pct_change()
        
        # 去除第一天的NaN
        df = df.dropna(subset=['return'])
        
        # 计算累计收益率
        logger.info("计算累计收益率")
        df.loc[:, 'cumulative_return'] = (1 + df['return']).cumprod() - 1
        
        # 获取最新的累计收益率
        latest_return = df['cumulative_return'].iloc[-1]
        logger.info(f"最新累计收益率: {latest_return:.4f}")
        
        # 计算最大回撤
        logger.info("计算最大回撤")
        df.loc[:, 'cummax'] = df['cumulative_return'].cummax()
        df.loc[:, 'drawdown'] = df['cummax'] - df['cumulative_return']
        max_drawdown = df['drawdown'].max()
        logger.info(f"最大回撤: {max_drawdown:.4f}")
        
        # 计算年化收益率
        days = len(df)
        annual_return = (1 + latest_return) ** (252 / days) - 1
        logger.info(f"年化收益率: {annual_return:.4f}")
        
        # 计算夏普比率
        risk_free_rate = 0.03
        volatility = df['return'].std() * np.sqrt(252)
        sharpe = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        logger.info(f"夏普比率: {sharpe:.4f}")
        
        return df
        
    except Exception as e:
        logger.error(f"计算指标失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def test_stock_data():
    """测试股票数据获取和处理"""
    # 测试股票列表
    test_stocks = [
        'sh.600519',  # 贵州茅台
        'sh.601398',  # 工商银行
        'sz.000001',  # 平安银行
        'sz.300750',  # 宁德时代
    ]
    
    for stock_code in test_stocks:
        logger.info(f"\n开始测试股票 {stock_code}")
        
        # 获取历史数据
        df = get_historical_data(stock_code)
        if df is None:
            logger.error(f"获取股票 {stock_code} 数据失败")
            continue
        
        logger.info(f"获取到 {len(df)} 条历史数据")
        logger.info(f"数据类型:\n{df.dtypes}")
        
        # 计算指标
        result_df = calculate_metrics(df)
        if result_df is None:
            logger.error(f"计算股票 {stock_code} 指标失败")
            continue
        
        logger.info(f"计算指标后数据框，形状: {result_df.shape}")
        logger.info(f"计算指标后列名: {result_df.columns.tolist()}")
        
        # 打印最终结果
        logger.info("\n最终数据框前5行:")
        logger.info(result_df.head().to_string())

if __name__ == "__main__":
    test_stock_data() 