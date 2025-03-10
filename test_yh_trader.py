#!/usr/bin/env python
# -*- coding: utf-8 -*-

import easytrader
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """测试easytrader库的基本功能"""
    try:
        logger.info("开始测试easytrader库...")
        
        # 打印easytrader版本
        logger.info(f"easytrader版本: {easytrader.__version__}")
        
        # 列出支持的券商
        logger.info(f"支持的券商: {easytrader.use.__doc__}")
        
        # 创建一个模拟的银河证券客户端
        logger.info("创建银河证券客户端...")
        user = easytrader.use('yh_client')
        
        # 打印客户端信息
        logger.info(f"客户端类型: {user.broker_type}")
        logger.info(f"客户端类: {user.__class__.__name__}")
        
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 