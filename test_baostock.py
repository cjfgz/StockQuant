import baostock as bs
import pandas as pd
import logging
from datetime import datetime

def test_baostock():
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # 1. 测试连接
        logger.info("正在连接BaoStock...")
        bs_result = bs.login()
        if bs_result.error_code != '0':
            logger.error(f"BaoStock连接失败: {bs_result.error_msg}")
            return False
        logger.info(f"BaoStock连接成功，结果：{bs_result.error_code} {bs_result.error_msg}")
        
        # 2. 测试获取沪深300成分股
        logger.info("正在获取沪深300成分股...")
        rs_hs300 = bs.query_hs300_stocks()
        if rs_hs300.error_code != '0':
            logger.error(f"获取沪深300成分股失败: {rs_hs300.error_msg}")
            return False
            
        hs300_stocks = []
        while (rs_hs300.error_code == '0') & rs_hs300.next():
            hs300_stocks.append(rs_hs300.get_row_data())
        logger.info(f"成功获取到 {len(hs300_stocks)} 只沪深300成分股")
        
        # 3. 测试获取单只股票数据
        if hs300_stocks:
            test_stock = hs300_stocks[0][1]  # 获取第一只股票的代码
            logger.info(f"正在获取股票 {test_stock} 的数据...")
            
            rs = bs.query_history_k_data_plus(
                test_stock,
                "date,code,close,volume",
                start_date='2024-03-01',
                end_date='2024-03-02',
                frequency="d"
            )
            
            if rs.error_code != '0':
                logger.error(f"获取股票数据失败: {rs.error_msg}")
                return False
                
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            logger.info(f"成功获取到 {len(data_list)} 条数据")
            if data_list:
                logger.info(f"数据示例: {data_list[0]}")
        
        # 4. 清理
        bs.logout()
        logger.info("测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        return False
    finally:
        try:
            bs.logout()
        except:
            pass

if __name__ == "__main__":
    test_baostock() 