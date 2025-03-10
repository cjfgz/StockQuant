import sys
import os
import importlib.util

def check_module(module_name):
    """检查模块是否已安装"""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"模块 {module_name} 未安装")
            return False
        else:
            print(f"模块 {module_name} 已安装")
            module = importlib.import_module(module_name)
            print(f"模块路径: {module.__file__}")
            if hasattr(module, '__version__'):
                print(f"模块版本: {module.__version__}")
            return True
    except Exception as e:
        print(f"检查模块 {module_name} 时出错: {str(e)}")
        return False

print("Python版本:", sys.version)
print("Python路径:", sys.executable)
print("\n检查easyutils模块:")
check_module("easyutils")

print("\n检查easytrader模块:")
check_module("easytrader")

print("\n尝试导入easytrader.clienttrader:")
try:
    from easytrader import clienttrader
    print("成功导入easytrader.clienttrader")
    print("模块路径:", clienttrader.__file__)
except Exception as e:
    print(f"导入easytrader.clienttrader失败: {str(e)}")

print("\n尝试导入easytrader.grid_strategies:")
try:
    from easytrader import grid_strategies
    print("成功导入easytrader.grid_strategies")
    print("模块路径:", grid_strategies.__file__)
except Exception as e:
    print(f"导入easytrader.grid_strategies失败: {str(e)}")

print("\n检查Python路径:")
for p in sys.path:
    print(f"  - {p}")

print("\n检查环境变量:")
for key, value in os.environ.items():
    if "PATH" in key or "PYTHON" in key:
        print(f"{key}: {value}") 