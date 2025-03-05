import yfinance as yf
import time
import smtplib
from email.mime.text import MIMEText
from plyer import notification

# 设置股票代码和提醒价格
STOCK_SYMBOL = "AAPL"
TARGET_PRICE = 150  # 目标价格
CHECK_INTERVAL = 60  # 检查间隔（秒）

# 邮件提醒配置
EMAIL_SENDER = "your_email@example.com"
EMAIL_RECEIVER = "receiver_email@example.com"
EMAIL_PASSWORD = "your_email_password"
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587

def get_stock_price(symbol):
    """获取实时股价"""
    stock = yf.Ticker(symbol)
    return stock.history(period="1d")["Close"].iloc[-1]

def send_email_notification(subject, body):
    """发送邮件提醒"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

def send_desktop_notification(title, message):
    """发送桌面提醒"""
    notification.notify(
        title=title,
        message=message,
        timeout=10
    )

def main():
    while True:
        current_price = get_stock_price(STOCK_SYMBOL)
        print(f"当前股价: ${current_price:.2f}")

        if current_price >= TARGET_PRICE:
            # 发送提醒
            message = f"{STOCK_SYMBOL} 股价已达到 ${current_price:.2f}，目标价格为 ${TARGET_PRICE}。"
            send_email_notification("股价提醒", message)
            send_desktop_notification("股价提醒", message)
            break

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
