import baostock as bs
import pandas as pd
from stockquant.message import DingTalk
import logging
from datetime import datetime

def test_environment():
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # 1. 测试BaoStock连接
        logger.info("测试BaoStock连接...")
        bs_result = bs.login()
        if bs_result.error_code != '0':
            logger.error(f"BaoStock连接失败: {bs_result.error_msg}")
            return False
        logger.info("BaoStock连接成功")
        
        # 2. 测试钉钉机器人
        logger.info("测试钉钉机器人...")
        try:
            ding = DingTalk()
            test_message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "股票提醒",
                    "text": "### 股票提醒：环境测试\n" +
                            "> 测试时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n" +
                            "测试内容：\n" +
                            "- BaoStock连接测试\n" +
                            "- 钉钉机器人消息测试\n" +
                            "- 股票数据获取测试\n\n" +
                            "关注A股，关注行情，每日精选"
                }
            }
            ding.send_message(test_message)
            logger.info("钉钉消息发送成功")
        except Exception as e:
            logger.error(f"钉钉测试失败: {str(e)}")
            return False
            
        # 3. 测试获取一只股票的数据
        logger.info("测试获取股票数据...")
        rs = bs.query_history_k_data_plus(
            "sh.600000",
            "date,code,close",
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
        
        # 4. 清理
        bs.logout()
        logger.info("环境测试完成")
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
    test_environment() 