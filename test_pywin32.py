import sys
import os

print("Python版本:", sys.version)
print("当前工作目录:", os.getcwd())
print("PATH环境变量:", os.environ.get('PATH', ''))

try:
    print("\n尝试导入win32api...")
    import win32api
    print("win32api导入成功!")
    print("win32api版本:", win32api.GetFileVersionInfo(win32api.__file__, '\\'))
except Exception as e:
    print(f"win32api导入失败: {str(e)}")
    import traceback
    print(traceback.format_exc())

try:
    print("\n尝试导入pywinauto...")
    from pywinauto.application import Application
    print("pywinauto导入成功!")
except Exception as e:
    print(f"pywinauto导入失败: {str(e)}")
    import traceback
    print(traceback.format_exc())

print("\n系统信息:")
try:
    import platform
    print("操作系统:", platform.platform())
    print("处理器:", platform.processor())
    print("Python编译器:", platform.python_compiler())
except Exception as e:
    print(f"获取系统信息失败: {str(e)}")

print("\nPython路径:")
for p in sys.path:
    print(f"  - {p}")

print("\n尝试查找DLL文件位置:")
try:
    import os
    python_dir = os.path.dirname(sys.executable)
    site_packages = os.path.join(python_dir, 'Lib', 'site-packages')
    pywin32_system32 = os.path.join(site_packages, 'pywin32_system32')
    
    if os.path.exists(pywin32_system32):
        print(f"pywin32_system32目录存在: {pywin32_system32}")
        dll_files = [f for f in os.listdir(pywin32_system32) if f.endswith('.dll')]
        print(f"DLL文件: {', '.join(dll_files)}")
    else:
        print(f"pywin32_system32目录不存在: {pywin32_system32}")
        
    # 检查System32目录
    system32_dir = os.path.join(os.environ['SystemRoot'], 'System32')
    if os.path.exists(system32_dir):
        print(f"System32目录存在: {system32_dir}")
        # 检查DLL是否在System32中
        for dll in ['pythoncom37.dll', 'pywintypes37.dll']:
            dll_path = os.path.join(system32_dir, dll)
            if os.path.exists(dll_path):
                print(f"  - {dll} 存在于System32中")
            else:
                print(f"  - {dll} 不存在于System32中")
    else:
        print(f"System32目录不存在: {system32_dir}")
except Exception as e:
    print(f"查找DLL文件失败: {str(e)}") 