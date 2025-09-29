#!/usr/bin/env python3
"""
SenseVoice服务器打包脚本（已弃用）
请使用 build_nuitka.py 进行优化编译
"""

import subprocess
from pathlib import Path

def build_executable():
    """使用现有的spec文件构建可执行文件"""
    print("🔨 开始构建可执行文件...")
    
    # 检查spec文件是否存在
    if not Path('sense_voice_server.spec').exists():
        print("❌ 未找到 sense_voice_server.spec 文件")
        return False
    
    # 使用spec文件构建
    cmd = ['pyinstaller', '--clean', 'sense_voice_server.spec']
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 构建成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def main():
    print("🚀 SenseVoice服务器打包工具")
    print("=" * 50)
    
    # 检查必要文件
    if not Path('server.py').exists() or not Path('sense_voice_server.spec').exists():
        print("❌ 请确保 server.py 和 sense_voice_server.spec 文件存在")
        return
    
    try:
        # 构建可执行文件
        if build_executable():
            print("\n✅ 打包完成! 可执行文件位于 dist/sense_voice_server")
        else:
            print("❌ 构建失败，请检查错误信息")
            
    except Exception as e:
        print(f"❌ 打包过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()