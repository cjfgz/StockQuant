import requests
import json
import time
import smtplib
from email.mime.text import MIMEText
import logging
from datetime import datetime
import os

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StockMonitor:
    def __init__(self, symbol, target_price, interval=60):
        self.symbol = symbol
        self.target_price = target_price
        self.interval = interval
        self.email_config = {
            "sender": "",
            "receiver": "",
            "password": "",
            "smtp_server": "",
            "smtp_port": 587
        }

    def get_stock_price(self):
        """获取实时股价（使用Alpha Vantage API）"""
        try:
            # 可以申请免费的Alpha Vantage API密钥
            api_key = "YOUR_API_KEY"  # 替换为您的API密钥
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={self.symbol}&apikey={api_key}"
            response = requests.get(url)
            data = json.loads(response.text)

            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                return float(data["Global Quote"]["05. price"])
            else:
                logger.error(f"无法获取股价数据: {data}")
                return None
        except Exception as e:
            logger.error(f"获取股价失败: {e}")
            return None

    def configure_email(self, sender, receiver, password, smtp_server, smtp_port=587):
        """配置邮件设置"""
        self.email_config["sender"] = sender
        self.email_config["receiver"] = receiver
        self.email_config["password"] = password
        self.email_config["smtp_server"] = smtp_server
        self.email_config["smtp_port"] = smtp_port

    def send_email_notification(self, subject, body):
        """发送邮件提醒"""
        if not all(self.email_config.values()):
            logger.warning("邮件配置不完整，无法发送邮件提醒")
            return False

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.email_config["sender"]
            msg["To"] = self.email_config["receiver"]

            with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as server:
                server.starttls()
                server.login(self.email_config["sender"], self.email_config["password"])
                server.sendmail(self.email_config["sender"], self.email_config["receiver"], msg.as_string())

            logger.info("邮件发送成功")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    def send_desktop_notification(self, title, message):
        """发送桌面提醒（兼容多平台）"""
        try:
            # 尝试使用系统原生通知
            if os.name == 'posix':  # Linux/Mac
                os.system(f"notify-send '{title}' '{message}'")
            elif os.name == 'nt':  # Windows
                # 使用简单的弹窗代替
                from tkinter import Tk, messagebox
                root = Tk()
                root.withdraw()  # 隐藏主窗口
                messagebox.showinfo(title, message)
                root.destroy()

            logger.info("桌面通知发送成功")
            return True
        except Exception as e:
            logger.error(f"桌面通知发送失败: {e}")
            return False

    def write_to_log_file(self, message):
        """将提醒信息写入日志文件"""
        log_file = f"stock_alert_{self.symbol}.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def start_monitoring(self):
        """开始监控股价"""
        logger.info(f"开始监控 {self.symbol} 股票，目标价格: ${self.target_price:.2f}")

        while True:
            current_price = self.get_stock_price()

            if current_price is None:
                logger.warning("获取股价失败，等待下次尝试...")
                time.sleep(self.interval)
                continue

            logger.info(f"当前股价: ${current_price:.2f}")

            # 实现价格达到目标或跌破目标的双向提醒
            if current_price >= self.target_price:
                message = f"{self.symbol} 股价已上涨至 ${current_price:.2f}，达到目标价格 ${self.target_price:.2f}。"
                self.send_desktop_notification("股价上涨提醒", message)
                self.send_email_notification("股价上涨提醒", message)
                self.write_to_log_file(message)
                break

            time.sleep(self.interval)


def main():
    # 示例用法
    symbol = input("请输入股票代码 (例如 AAPL): ")
    target_price = float(input("请输入目标价格: "))
    interval = int(input("请输入检查间隔(秒): ") or "60")

    monitor = StockMonitor(symbol=symbol, target_price=target_price, interval=interval)

    # 配置邮件（如需使用）
    use_email = input("是否配置邮件提醒? (y/n): ").lower() == 'y'
    if use_email:
        sender = input("发送邮箱: ")
        receiver = input("接收邮箱: ")
        password = input("邮箱密码: ")
        smtp_server = input("SMTP服务器: ")
        smtp_port = int(input("SMTP端口 (默认587): ") or "587")
        monitor.configure_email(sender, receiver, password, smtp_server, smtp_port)

    monitor.start_monitoring()


if __name__ == "__main__":
    main()
