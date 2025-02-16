import requests
import json
from stockquant.utils.logger import logger


class Sina:
    def __init__(self):
        self.base_url = "http://hq.sinajs.cn/list="

    def get_realtime_data(self, symbol):
        """
        获取新浪实时行情数据
        :param symbol: 股票代码，如 'sh600000' 或 'sz000001'
        :return: dict 或 None
        """
        try:
            url = f"{self.base_url}{symbol}"
            headers = {
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0'
            }
            response = requests.get(url, headers=headers)
            response.encoding = 'gbk'
            
            text = response.text.split('="')[1].split('";')[0].split(',')
            if len(text) < 32:  # 确保数据完整
                return None
                
            return {
                'name': text[0],
                'open': float(text[1]),
                'close': float(text[2]),  # 昨日收盘价
                'price': float(text[3]),  # 当前价格
                'high': float(text[4]),
                'low': float(text[5]),
                'volume': float(text[8]),
                'amount': float(text[9])
            }
            
        except Exception as e:
            logger.error(f"获取股票{symbol}实时数据失败: {str(e)}")
            return None 