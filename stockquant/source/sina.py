import requests
import json
from stockquant.utils.logger import logger


class Sina(object):
    @staticmethod
    def get_realtime_data(symbol):
        """
        获取新浪股票实时数据接口
        :param symbol: 例如："sh601003"，或者"sz002307"，前者是沪市，后者是深市
        :return: 返回dict
        """
        try:
            if symbol.startswith('sh'):
                symbol_code = 'sh' + symbol[2:]
            elif symbol.startswith('sz'):
                symbol_code = 'sz' + symbol[2:]
            else:
                logger.error(f"股票代码格式错误: {symbol}")
                return None

            url = f"http://hq.sinajs.cn/list={symbol_code}"
            headers = {
                "Referer": "http://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            res = requests.get(url, headers=headers)
            res.encoding = 'gbk'
            
            text = res.text.strip()
            if not text or '""' in text:
                logger.error(f"获取不到股票数据: {symbol}")
                return None
                
            data = text.split('=')[1].split(',')
            if len(data) < 32:
                logger.error(f"股票数据格式错误: {symbol}")
                return None
                
            result = {
                'symbol': symbol,
                'name': data[0].replace('"', ''),
                'open': float(data[1]),
                'close': float(data[2]),  # 昨收
                'price': float(data[3]),  # 当前价格
                'high': float(data[4]),
                'low': float(data[5]),
                'volume': float(data[8]),
                'amount': float(data[9])
            }
            return result
        except Exception as e:
            logger.error(f"获取新浪股票实时数据失败: {str(e)}")
            return None 