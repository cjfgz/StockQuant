import requests
import json
from stockquant.utils.logger import logger


class Tencent(object):
    @staticmethod
    def get_realtime_data(symbol):
        """
        获取腾讯股票实时数据接口
        :param symbol: 例如："sh601003"，或者"sz002307"，前者是沪市，后者是深市
        :return: 返回dict
        """
        try:
            market = 'sh' if symbol.startswith('sh') else 'sz'
            code = symbol[2:]
            url = f"http://qt.gtimg.cn/q={market}{code}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            res = requests.get(url, headers=headers)
            res.encoding = 'gbk'
            data = res.text.split('~')
            
            if len(data) < 2:
                logger.error("获取腾讯股票数据格式错误")
                return None
                
            result = {
                'symbol': symbol,
                'name': data[1],
                'price': float(data[3]),
                'open': float(data[5]),
                'close': float(data[4]),  # 昨收
                'high': float(data[33]),
                'low': float(data[34]),
                'volume': float(data[6]),
                'amount': float(data[37])
            }
            return result
        except Exception as e:
            logger.error(f"获取腾讯股票实时数据失败: {str(e)}")
            return None 