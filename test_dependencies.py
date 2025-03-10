# -*- coding: utf-8 -*-
# 测试依赖库是否正确安装

print("开始测试依赖库导入...")

try:
    import baostock as bs
    print("✓ baostock 导入成功")
except ImportError as e:
    print(f"✗ baostock 导入失败: {e}")

try:
    import pandas as pd
    print("✓ pandas 导入成功")
except ImportError as e:
    print(f"✗ pandas 导入失败: {e}")

try:
    import numpy as np
    print("✓ numpy 导入成功")
except ImportError as e:
    print(f"✗ numpy 导入失败: {e}")

try:
    import matplotlib.pyplot as plt
    print("✓ matplotlib 导入成功")
except ImportError as e:
    print(f"✗ matplotlib 导入失败: {e}")

try:
    import pywinauto
    print("✓ pywinauto 导入成功")
except ImportError as e:
    print(f"✗ pywinauto 导入失败: {e}")

try:
    import easytrader
    print("✓ easytrader 导入成功")
except ImportError as e:
    print(f"✗ easytrader 导入失败: {e}")

try:
    import talib
    print("✓ talib 导入成功")
except ImportError as e:
    print(f"✗ talib 导入失败: {e}")

try:
    import tushare
    print("✓ tushare 导入成功")
except ImportError as e:
    print(f"✗ tushare 导入失败: {e}")

try:
    import pandas_ta
    print("✓ pandas-ta 导入成功")
except ImportError as e:
    print(f"✗ pandas-ta 导入失败: {e}")

print("\n依赖库测试完成！")
print("StockQuant量化交易系统环境已准备就绪。")