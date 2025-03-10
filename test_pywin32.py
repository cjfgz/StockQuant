import sys
import os
import platform

print(f"Python版本: {sys.version}")
print(f"当前工作目录: {os.getcwd()}")
print(f"PATH环境变量: {os.environ.get('PATH')}")

print("\n尝试导入win32api...")
try:
    import win32api
    print(f"win32api导入成功! 版本信息: {win32api.__file__}")
except Exception as e:
    print(f"win32api导入失败: {str(e)}")
    print()

print("\n尝试导入pywinauto...")
try:
    from pywinauto.application import Application
    print("pywinauto导入成功!")
except Exception as e:
    print(f"pywinauto导入失败: {str(e)}")
    print()

print("\n系统信息:")
print(f"操作系统: {platform.platform()}")
print(f"处理器: {platform.processor()}")
print(f"Python编译器: {platform.python_compiler()}")

print("\nPython路径:")
for p in sys.path:
    print(f"  - {p}")

print("\n尝试查找DLL文件位置:")
pywin32_system32 = os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "pywin32_system32")
print(f"pywin32_system32目录存在: {os.path.exists(pywin32_system32)}")
print(f"DLL文件: pythoncom37.dll, pywintypes37.dll")

system32_dir = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
print(f"System32目录存在: {os.path.exists(system32_dir)}")
print(f"  - pythoncom37.dll 存在于System32中: {os.path.exists(os.path.join(system32_dir, 'pythoncom37.dll'))}")
print(f"  - pywintypes37.dll 存在于System32中: {os.path.exists(os.path.join(system32_dir, 'pywintypes37.dll'))}") 