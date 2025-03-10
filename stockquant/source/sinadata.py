import requests
from stockquant.tick import Tick


class SinaData:

    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 10
        self.session = requests.Session()

    def get_realtime_data(self, symbol):
        """
        获取指定股票的实时数据，带重试机制和数据验证
        :param symbol: 例如："sh601003"，或者"sz002307"，前者是沪市，后者是深市
        :return:返回一个字典或None（如果获取失败）
        """
        for retry in range(self.max_retries):
            try:
                if retry > 0:
                    logger.info(f"第{retry + 1}次尝试获取{symbol}实时数据...")
                    time.sleep(self.retry_delay)
                    
                tick = Tick(symbol)
                response = self.session.get(
                    f"http://hq.sinajs.cn/list={symbol}",
                    timeout=self.timeout
                ).text
                
                if not response or len(response) < 10:
                    logger.warning(f"获取{symbol}数据响应为空或无效")
                    continue
                    
                data = response.split(",")
                if len(data) < 30:
                    logger.warning(f"获取{symbol}数据格式错误")
                    continue
        tick.timestamp = data[-4] + " " + data[-3] if str(symbol).startswith("sh") else data[-3] + " " + data[-2]
        tick.symbol = data[0].replace('"', "").split("=")[1]
        tick.open = float(data[1])
        tick.yesterday_close = float(data[2])
        tick.last = float(data[3])
        tick.high = float(data[4])
        tick.low = float(data[5])
        tick.bid_price = float(data[6])
        tick.ask_price = float(data[7])
        tick.transactions = round(float(data[8]))
        tick.turnover = round(float(data[9]))
        tick.bid1_quantity = round(float(data[10]))
        tick.bid1_price = float(data[11])
        tick.bid2_quantity = round(float(data[12]))
        tick.bid2_price = float(data[13])
        tick.bid3_quantity = round(float(data[14]))
        tick.bid3_price = float(data[15])
        tick.bid4_quantity = round(float(data[16]))
        tick.bid4_price = float(data[17])
        tick.bid5_quantity = round(float(data[18]))
        tick.bid5_price = float(data[19])
        tick.ask1_quantity = round(float(data[20]))
        tick.ask1_price = float(data[21])
        tick.ask2_quantity = round(float(data[22]))
        tick.ask2_price = float(data[23])
        tick.ask3_quantity = round(float(data[24]))
        tick.ask3_price = float(data[25])
        tick.ask4_quantity = round(float(data[26]))
        tick.ask4_price = float(data[27])
        tick.ask5_quantity = round(float(data[28]))
        tick.ask5_price = float(data[29])
        return tick

    @staticmethod
    def shenzhen_component_index():
        """
        获取深圳成指
        :return:返回一个字典
        """
        response = requests.get("http://hq.sinajs.cn/list=s_sz399001").text
        data = response.split(",")
        result = {
            "指数名称": data[0].replace('"', "").split("=")[1],
            "当前点数": float(data[1]),
            "涨跌点数": float(data[2]),
            "涨跌率": float(data[3]),
            "成交数量": float(data[4]),
            "成交金额": float(data[5].split('";')[0])
        }
        return result

    @staticmethod
    def shanghai_component_index():
        """
        获取上证综指
        :return:
        """
        response = requests.get("http://hq.sinajs.cn/list=s_sh000001").text
        data = response.split(",")
        result = {
            "指数名称": data[0].replace('"', "").split("=")[1],
            "当前点数": float(data[1]),
            "涨跌点数": float(data[2]),
            "涨跌率": float(data[3]),
            "成交数量": float(data[4]),
            "成交金额": float(data[5].split('";')[0])
        }
        return result