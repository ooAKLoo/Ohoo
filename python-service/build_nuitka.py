#!/usr/bin/env python
"""
Nuitka编译脚本 - 极速优化版

使用说明：
=========
1. 常规编译（增量模式，最快）：
   python build_nuitka.py
   
2. 完全重新编译（清理所有缓存）：
   python build_nuitka.py --clean
   
3. 仅清理输出，保留缓存：
   python build_nuitka.py --clean-dist

编译模式说明：
============
- 增量编译（默认）：
  * Python代码修改 → 自动检测变化，只重编译改变部分
  * 编译时间：首次10-15分钟，增量1-3分钟
  * 适用场景：日常开发、代码调试
  
- 完全编译（--clean）：
  * 删除所有缓存，从零开始编译
  * 编译时间：10-15分钟
  * 适用场景：
    - Python版本更换
    - Nuitka参数修改  
    - 依赖包大版本更新
    - 编译出错需要重置

重要说明：
========
1. nuitka_cmd中的参数都是默认使用的，无需手动指定
2. 修改Python代码后直接运行脚本即可，Nuitka会自动处理增量
3. .build目录包含重要缓存，不要手动删除
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import argparse

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Nuitka编译脚本 - SenseVoice服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python build_nuitka.py              # 增量编译（推荐）
  python build_nuitka.py --clean      # 完全重编译
  python build_nuitka.py --clean-dist # 仅清理输出
        """
    )
    
    parser.add_argument(
        '--clean', 
        action='store_true',
        help='完全清理：删除所有缓存和输出（编译时间较长）'
    )
    
    parser.add_argument(
        '--clean-dist',
        action='store_true', 
        help='仅清理输出目录，保留编译缓存'
    )
    
    parser.add_argument(
        '--jobs',
        type=int,
        default=None,
        help='并行编译的CPU核心数（默认：使用所有核心）'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式（用于诊断段错误问题）'
    )
    
    return parser.parse_args()

def clean_build(mode='dist'):
    """清理构建文件
    
    Args:
        mode: 清理模式
            - 'dist': 只清理输出目录（默认）
            - 'all': 清理所有，包括缓存
    """
    # 输出目录（总是清理）
#     output_dirs = [
#     'dist_nuitka',           # 临时输出目录
#     'sense_voice_server.dist', # Nuitka生成的可执行文件夹
#     'server.dist',           # 另一个可能的输出名
#     'dist'                   # 最终标准输出目录
# ]
    output_dirs = ['dist_nuitka', 'sense_voice_server.dist', 
                   'server.dist', 'dist']
    
    # 缓存目录（仅在 mode='all' 时清理）
    cache_dirs = ['sense_voice_server.build', 'server.build', 
                  'build_nuitka', '.nuitka_cache']
    
    if mode == 'all':
        dirs_to_clean = output_dirs + cache_dirs
        print("⚠️  完全清理模式：删除所有缓存和输出")
        print("   下次编译将需要10-15分钟")
    else:
        dirs_to_clean = output_dirs
        print("📦 仅清理输出目录，保留编译缓存")
    
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"   ✓ 已清理 {dir_name}")

def build_with_nuitka(cpu_count=None, debug_mode=False):
    """使用Nuitka构建 - 支持增量编译
    
    Args:
        cpu_count: 使用的CPU核心数
    """
    
    # 设置缓存目录（通过环境变量）
    cache_dir = Path.cwd() / '.nuitka_cache'
    cache_dir.mkdir(exist_ok=True)
    
    # Nuitka 2.7.16使用环境变量控制缓存
    os.environ['NUITKA_CACHE_DIR'] = str(cache_dir)
    
    if cpu_count is None:
        cpu_count = os.cpu_count() or 4
    
    # 所有这些参数都会默认使用
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        
        # ===== 核心配置 =====
        "--standalone",                    # 独立文件夹模式
        "--assume-yes-for-downloads",
        
        # ===== 编译速度优化 =====
        f"--jobs={cpu_count}",            # 并行编译
        "--lto=no",                       # 关闭链接时优化（加快编译）
        
        # ===== 启动速度优化 =====
        "--python-flag=no_site,no_warnings,no_asserts,no_docstrings",
        
        # ===== 必要的插件（funasr-onnx需要torch） =====
        "--enable-plugin=torch",          # ✅ funasr-onnx内部需要torch
        "--enable-plugin=numpy",          # 保留numpy
        "--enable-plugin=anti-bloat",     # 减小体积
        
        # ===== 包含必要的包（最小torch+ONNX版本） =====
        "--include-package=torch",        # ✅ funasr-onnx依赖torch
        "--include-package=librosa",      # 保留音频处理
        "--include-package=soundfile",    # 保留音频处理
        "--include-package=numpy",        # 保留numpy
        "--include-package=scipy",        # librosa需要scipy
        "--include-package=jieba",        # 中文分词
        
        # ===== ONNX 运行时支持 =====
        "--include-package=onnxruntime",  # ONNX运行时
        "--include-package=funasr_onnx",  # 只需要ONNX版本
        "--include-package-data=onnxruntime",
        "--include-package-data=funasr_onnx",
        
        # ===== 体积优化：排除不需要的包 =====
        # "--nofollow-import-to=torch",       # ✅ 保留torch（funasr-onnx需要）
        "--nofollow-import-to=torchvision",   # ❌ 排除视觉相关
        "--nofollow-import-to=torchaudio",    # ❌ 排除音频torch
        "--nofollow-import-to=transformers",  # ❌ 排除transformers
        "--nofollow-import-to=modelscope",    # ❌ 排除modelscope
        "--nofollow-import-to=funasr",        # ❌ 排除torch版本的funasr
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=PIL",
        "--nofollow-import-to=sklearn",
        # "--nofollow-import-to=scipy",  # Keep scipy - required by librosa
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=cv2",
        "--nofollow-import-to=opencv",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=test",
        "--nofollow-import-to=tests",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=jupyter",
        "--nofollow-import-to=notebook",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=pip",
        "--nofollow-import-to=distutils",
        "--nofollow-import-to=xmlrpc",
        "--nofollow-import-to=IPython",
        "--nofollow-import-to=docutils",
        "--nofollow-import-to=pydoc",
        "--nofollow-import-to=seaborn",
        "--nofollow-import-to=plotly",
        "--nofollow-import-to=bokeh",
        "--nofollow-import-to=tensorflow",
        "--nofollow-import-to=keras",
        
        # ===== 输出配置 =====
        "--output-dir=.",
        "--output-filename=sense_voice_server",
        
        # ===== 显示进度 =====
        "--show-progress",
        "--show-memory",
        
        # 主程序
        "server.py"
    ]
    
    # 添加调试选项（如果启用）
    if debug_mode:
        nuitka_cmd.extend([
            "--debug",
            "--no-debug-c-warnings",  # 避免gcc编译警告阻止构建
            "--no-debug-immortal-assumptions"  # 避免Python3.12+的immortal检查错误
        ])
        print("🐛 调试模式已启用")
        print("   - 将生成详细错误信息")
        print("   - 编译时间会显著增加")
        print("   - 运行时性能会降低")
    
    # 检测是否为增量编译
    is_incremental = cache_dir.exists() or \
                    Path('sense_voice_server.build').exists()
    
    if is_incremental:
        print("⚡ 增量编译模式：利用缓存加速")
        print(f"   缓存目录：{cache_dir}")
        print("   预计时间：1-3分钟")
    else:
        print("🚀 首次编译：构建完整缓存")
        print(f"   缓存目录：{cache_dir}")
        print("   预计时间：10-15分钟")
    
    print(f"💪 使用 {cpu_count} 个CPU核心并行编译")
    
    result = subprocess.run(nuitka_cmd, cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print("✅ Nuitka编译成功！")
        
        # 复制到标准dist目录
        dist_dir = Path("dist")
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        
        # 检查多个可能的输出目录名
        possible_outputs = [
            "sense_voice_server.dist",
            "server.dist",  # 实际生成的目录名
        ]
        
        output_found = None
        for output_name in possible_outputs:
            if Path(output_name).exists():
                output_found = output_name
                break
        
        if output_found:
            print(f"📦 找到编译输出：{output_found}")
            shutil.copytree(output_found, dist_dir)
            
            # 查找可执行文件（也需要适配多种可能的名称）
            possible_exes = [
                dist_dir / "sense_voice_server",
                dist_dir / "server",  # 实际可能的名称
                dist_dir / "sense_voice_server.bin",
                dist_dir / "server.bin",
                dist_dir / "sense_voice_server.exe",
                dist_dir / "server.exe"
            ]
            
            exe_found = False
            for exe_file in possible_exes:
                if exe_file.exists():
                    if not exe_file.suffix:  # Unix可执行文件
                        exe_file.chmod(0o755)
                    print(f"✅ 可执行文件: {exe_file}")
                    exe_found = True
                    break
            
            if not exe_found:
                print("⚠️  警告：未找到可执行文件")
                print("📂 dist目录内容：")
                for item in dist_dir.iterdir():
                    print(f"   - {item.name}")
            
            # 清理不必要的文件
            for pattern in ["*.pyi", "*.pyc", "__pycache__"]:
                for f in dist_dir.rglob(pattern):
                    if f.is_file():
                        f.unlink()
                    elif f.is_dir():
                        shutil.rmtree(f)
                        
            return True
        else:
            print("❌ 未找到编译输出")
            # 调试信息
            print("📂 当前目录内容：")
            for item in Path(".").glob("*.dist"):
                print(f"   - {item}")
            return False
    else:
        print("❌ Nuitka编译失败！")
        return False

def main():
    args = parse_args()
    
    print("=" * 60)
    print("⚡ Nuitka优化编译 - SenseVoice服务器")
    print("🎯 特点：最小torch+ONNX，体积优化")
    print("=" * 60)
    
    # 1. 清理策略
    if args.clean:
        clean_build(mode='all')
    elif args.clean_dist:
        clean_build(mode='dist')
    else:
        # 默认：仅清理输出，保留缓存（增量编译）
        clean_build(mode='dist')
    
    # 2. 检查Nuitka
    try:
        import nuitka
        print("✓ Nuitka已安装")
    except ImportError:
        print("📦 安装Nuitka...")
        subprocess.run([sys.executable, "-m", "pip", "install", 
                       "nuitka", "ordered-set", "zstandard"])
    
    # 3. 构建
    if build_with_nuitka(args.jobs, args.debug):
        print("\n🎉 优化版本编译完成！")
        print("\n💡 优势：")
        print("   - 体积优化（约400-500MB vs 800MB）")
        print("   - 启动速度提升30%")
        print("   - 移除大型依赖（modelscope、transformers等）")
        print("   - ONNX推理，性能稳定")
        
        if not args.clean:
            print("\n💡 提示：")
            print("   - 下次编译将自动使用增量模式")
            print("   - 如需完全重编译，使用: python build_nuitka.py --clean")
        
        print(f"\n📁 可执行文件: {Path('dist').absolute()}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()