"""
配置模块
Author: Gary-Hertel
Date:   2021/01/19
"""

import json
import os


class Config:
    """ 配置模块
    """

    def __init__(self):
        self.dingtalk = None    # 钉钉配置
        self.tushare_api = None # tushare api
        
        # 自动加载配置文件
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "docs/config.json"
        )
        self.loads(config_file)

    def loads(self, config_file=None):
        """ 加载配置
        @param config_file json配置文件
        """
        configures = {}
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = f.read()
                    configures = json.loads(data)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return
        self.update(configures)

    def update(self, update_fields):
        """ 更新配置
        @param update_fields 更新字段
        """
        self.dingtalk = update_fields.get("DINGTALK", {})
        self.tushare_api = update_fields.get("TUSHARE", {})
        for k, v in update_fields.items():
            setattr(self, k, v)

    # TuShare配置
    TUSHARE_TOKEN = "你的tushare token"  # 在 https://tushare.pro 注册后获取


config = Config()