import os
import sys
import shutil
from pathlib import Path

def fix_pywin32():
    """修复pywin32 DLL加载问题"""
    print("开始修复pywin32...")
    
    # 获取Python安装路径
    python_path = sys.executable
    python_dir = os.path.dirname(python_path)
    site_packages = os.path.join(python_dir, 'Lib', 'site-packages')
    
    # 检查pywin32_system32目录
    pywin32_system32 = os.path.join(site_packages, 'pywin32_system32')
    if not os.path.exists(pywin32_system32):
        print(f"未找到pywin32_system32目录: {pywin32_system32}")
        return False
    
    # 检查Windows System32目录
    system32_dir = os.path.join(os.environ['SystemRoot'], 'System32')
    if not os.path.exists(system32_dir):
        print(f"未找到System32目录: {system32_dir}")
        return False
    
    # 复制DLL文件
    dll_files = [f for f in os.listdir(pywin32_system32) if f.endswith('.dll')]
    if not dll_files:
        print("未找到DLL文件")
        return False
    
    print(f"找到以下DLL文件: {', '.join(dll_files)}")
    
    success = True
    for dll in dll_files:
        src = os.path.join(pywin32_system32, dll)
        dst = os.path.join(system32_dir, dll)
        
        try:
            if not os.path.exists(dst):
                print(f"复制 {dll} 到 System32...")
                shutil.copy2(src, dst)
            else:
                print(f"{dll} 已存在于System32中")
        except Exception as e:
            print(f"复制 {dll} 失败: {str(e)}")
            success = False
    
    # 尝试运行postinstall脚本
    try:
        print("运行pywin32 postinstall脚本...")
        pywin32_postinstall = os.path.join(site_packages, 'pywin32_system32', 'scripts', 'pywin32_postinstall.py')
        if os.path.exists(pywin32_postinstall):
            os.system(f'"{python_path}" "{pywin32_postinstall}" -install')
        else:
            # 尝试其他可能的位置
            pywin32_postinstall = os.path.join(site_packages, 'win32', 'scripts', 'pywin32_postinstall.py')
            if os.path.exists(pywin32_postinstall):
                os.system(f'"{python_path}" "{pywin32_postinstall}" -install')
            else:
                print("未找到pywin32_postinstall.py脚本")
    except Exception as e:
        print(f"运行postinstall脚本失败: {str(e)}")
        success = False
    
    # 添加路径到环境变量
    try:
        print("将pywin32_system32添加到PATH环境变量...")
        path = os.environ.get('PATH', '')
        if pywin32_system32 not in path:
            os.environ['PATH'] = f"{pywin32_system32};{path}"
            print("已添加到当前会话的PATH")
    except Exception as e:
        print(f"添加环境变量失败: {str(e)}")
        success = False
    
    if success:
        print("pywin32修复完成！请重启Python程序尝试。")
    else:
        print("pywin32修复过程中遇到一些问题，可能需要手动解决。")
    
    return success

if __name__ == "__main__":
    fix_pywin32() 