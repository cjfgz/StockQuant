"""
Author: Gary-Hertel
Email:  garyhertel@foxmail.com
Date:   2022-01-23
"""

import json
import requests
from stockquant.utils.logger import logger

from stockquant.tick import Tick


class MoneyData:

    @staticmethod
    def get_realtime_data(symbol: str):
        """
        获取股票实时数据
        :param symbol: 例如："sh601003"，或者"sz002307"
        :return: 返回dict
        """
        try:
            url = f"http://api.money.126.net/data/feed/{symbol},money.api"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            res = requests.get(url, headers=headers)
            data = res.json()[symbol]
            
            result = {
                'symbol': symbol,
                'name': data['name'],
                'price': float(data['price']),
                'open': float(data['open']),
                'close': float(data['yestclose']),
                'high': float(data['high']),
                'low': float(data['low']),
                'volume': float(data['volume']),
                'amount': float(data['turnover'])
            }
            return result
        except Exception as e:
            logger.error(f"获取网易财经数据失败: {str(e)}")
            return None

    @staticmethod
    def shenzhen_component_index():
        """获取深圳成指"""
        return MoneyData.get_realtime_data("sz399001")

    @staticmethod
    def shanghai_component_index():
        """获取上证综指"""
        return MoneyData.get_realtime_data("sh000001")


if __name__ == '__main__':
    
    tick = MoneyData.get_realtime_data(symbol="sh603176")
    print(tick)
    
    sh = MoneyData.shanghai_component_index()
    print(sh)
    
    sz = MoneyData.shenzhen_component_index()
    print(sz)