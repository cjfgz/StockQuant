import time
import smtplib
from email.mime.text import MIMEText
from plyer import notification
import logging
from datetime import datetime
import requests
from threading import Timer

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StockMonitor:
    def __init__(self, stock_config, interval=60):
        """
        初始化股票监控器
        :param stock_config: 股票配置字典，格式：{'sh600000': {'target_price': 10.0}}
        :param interval: 检查间隔（秒）
        """
        self.stock_config = {
            code.replace('sh.', 'sh').replace('sz.', 'sz'): config 
            for code, config in stock_config.items()
        }
        self.interval = interval
        self.email_config = {
            "sender": "",
            "receiver": "",
            "password": "",
            "smtp_server": "",
            "smtp_port": 587
        }
        self.triggered_stocks = set()  # 记录已触发提醒的股票
        self.session = requests.Session()  # 使用会话保持连接
        self.headers = {
            "Referer": "http://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0"
        }

    def is_trading_time(self):
        """检查是否在交易时间内"""
        now = datetime.now().time()
        morning_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        morning_end = datetime.strptime("11:30:00", "%H:%M:%S").time()
        afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
        afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()

        return ((morning_start <= now <= morning_end) or 
                (afternoon_start <= now <= afternoon_end))

    def get_stock_prices(self):
        """获取所有股票的实时股价"""
        try:
            # 使用新浪财经的实时数据接口批量获取
            codes = ','.join(self.stock_config.keys())
            url = f"http://hq.sinajs.cn/list={codes}"
            
            response = self.session.get(url, headers=self.headers, timeout=5)
            response.encoding = 'gbk'  # 设置正确的编码
            
            results = {}
            for line in response.text.strip().split('\n'):
                if not line:
                    continue
                code = line.split('=')[0].split('_')[-1]
                data = line.split('=')[1].split(',')
                if len(data) < 4:
                    continue
                    
                stock_name = data[0].strip('"')  # 股票名称
                current_price = float(data[3])  # 当前价格
                results[code] = {
                    'name': stock_name,
                    'price': current_price
                }
            
            return results

        except Exception as e:
            logger.error(f"获取股价失败: {str(e)}")
            return None

    def send_notifications(self, alerts):
        """发送所有通知"""
        if not alerts:
            return
            
        message = "股价提醒：\n" + "\n".join(alerts)
        
        # 发送桌面通知
        try:
            notification.notify(
                title="股价提醒",
                message=message,
                timeout=10
            )
        except Exception as e:
            logger.error(f"桌面通知发送失败: {e}")

        # 如果配置了邮件，发送邮件通知
        if all(self.email_config.values()):
            try:
                msg = MIMEText(message)
                msg["Subject"] = "股价提醒"
                msg["From"] = self.email_config["sender"]
                msg["To"] = self.email_config["receiver"]

                with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as server:
                    server.starttls()
                    server.login(self.email_config["sender"], self.email_config["password"])
                    server.sendmail(self.email_config["sender"], self.email_config["receiver"], msg.as_string())
            except Exception as e:
                logger.error(f"邮件发送失败: {e}")

    def check_prices(self):
        """检查股票价格并处理提醒"""
        if not self.is_trading_time():
            Timer(300, self.check_prices).start()  # 非交易时间，5分钟后再检查
            return

        stock_prices = self.get_stock_prices()
        if stock_prices is None:
            Timer(self.interval, self.check_prices).start()
            return

        alerts = []
        for code, price_info in stock_prices.items():
            if code in self.triggered_stocks:
                continue

            config = self.stock_config.get(code)
            if not config:
                continue

            current_price = price_info['price']
            if current_price >= config['target_price']:
                alert = f"{price_info['name']}({code}) 股价已上涨至 ¥{current_price:.2f}，达到目标价格 ¥{config['target_price']:.2f}"
                alerts.append(alert)
                self.triggered_stocks.add(code)
                logger.info(alert)

        if alerts:
            self.send_notifications(alerts)

        # 如果所有股票都已触发，则结束监控
        if len(self.triggered_stocks) < len(self.stock_config):
            Timer(self.interval, self.check_prices).start()

    def start_monitoring(self):
        """开始监控股价"""
        logger.info("开始监控以下股票：")
        for code, config in self.stock_config.items():
            logger.info(f"股票代码: {code}, 目标价格: ¥{config['target_price']:.2f}")

        self.check_prices()

def main():
    # 示例用法 - 同时监控多只股票
    stock_config = {
        'sh600000': {'target_price': 10.0},  # 浦发银行
        'sh601318': {'target_price': 50.0},  # 中国平安
        'sz000001': {'target_price': 15.0},  # 平安银行
        'sh600519': {'target_price': 1800.0},  # 贵州茅台
        'sz000858': {'target_price': 150.0},  # 五粮液
    }
    
    monitor = StockMonitor(stock_config, interval=60)
    # 配置邮件（如需使用）
    # monitor.configure_email("your_email@example.com", "receiver_email@example.com",
    #                        "your_password", "smtp.example.com")
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
