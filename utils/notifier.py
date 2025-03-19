from dingtalkchatbot.chatbot import DingtalkChatbot

def send_notification(message):
    webhook = 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN'
    xiaoding = DingtalkChatbot(webhook)
    xiaoding.send_text(msg=message, is_at_all=False) 