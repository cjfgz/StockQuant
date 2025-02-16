import tushare as ts
from stockquant.utils.logger import logger
from stockquant.config import config


class TuSharePro(object):
    def __init__(self):
        self.pro = None
        try:
            ts.set_token(config.TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        except Exception as e:
            logger.error(f"初始化TuShare Pro失败: {str(e)}")

    def get_realtime_data(self, symbol):
        """
        获取股票实时数据
        :param symbol: 例如："sh601003"，或者"sz002307"
        :return: 返回dict
        """
        try:
            code = symbol[2:]
            market = 'XSHG' if symbol.startswith('sh') else 'XSHE'
            df = ts.get_realtime_quotes(code)
            if df is None or df.empty:
                return None
            
            data = df.iloc[0]
            result = {
                'symbol': symbol,
                'name': data['name'],
                'price': float(data['price']),
                'open': float(data['open']),
                'close': float(data['pre_close']),
                'high': float(data['high']),
                'low': float(data['low']),
                'volume': float(data['volume']),
                'amount': float(data['amount'])
            }
            return result
        except Exception as e:
            logger.error(f"获取TuShare实时数据失败: {str(e)}")
            return None 