"""
配置模块
Author: Gary-Hertel
Date:   2021/01/19
"""

import json


class Config:
    """ 配置模块
    """

    def __init__(self):
        self.dingtalk = None    # 钉钉配置
        self.tushare_api = None # tushare api

    def loads(self, config_file=None):
        """ 加载配置
        @param config_file json配置文件
        """
        configures = {}
        if config_file:
            try:
                with open(config_file) as f:
                    data = f.read()
                    configures = json.loads(data)
            except Exception as e:
                print(e)
                exit(0)
            if not configures:
                print("配置文件错误!")
                exit(0)
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
    TUSHARE_TOKEN = ""  # 在 https://tushare.pro 注册后获取


config = Config()