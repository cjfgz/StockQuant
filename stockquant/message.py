import json
import requests
from stockquant.config import config
from stockquant.utils.logger import logger


class DingTalk:
    """钉钉机器人消息发送"""

    def __init__(self):
        """
        初始化钉钉机器人
        配置文件 config.json 中需要设置:
        {
            "DINGTALK": {
                "webhook": "钉钉机器人的webhook地址",
                "secret": "钉钉机器人的secret密钥"  # 可选
            }
        }
        """
        self.webhook = config.dingtalk.get("webhook", "") if config.dingtalk else ""
        self.secret = config.dingtalk.get("secret", "") if config.dingtalk else ""

    def send_message(self, msg):
        """
        发送消息
        :param msg: 要发送的消息内容
        :return: None
        """
        if not self.webhook:
            logger.warning("未配置钉钉机器人webhook，消息未发送")
            return

        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                "msgtype": "text",
                "text": {
                    "content": msg
                }
            }
            response = requests.post(
                self.webhook,
                headers=headers,
                data=json.dumps(data)
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info("钉钉消息发送成功")
                else:
                    logger.error(f"钉钉消息发送失败: {result.get('errmsg')}")
            else:
                logger.error(f"钉钉消息发送失败: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"钉钉消息发送异常: {str(e)}") 