#!/usr/bin/env python3
"""
下载完整的模型文件（包含Python代码）
"""
import os
import sys
from pathlib import Path

# 添加父目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def download_models():
    """下载完整的模型文件"""
    print("=" * 70)
    print("🚀 开始下载完整的 SenseVoice 模型文件...")
    print("=" * 70)
    
    try:
        from modelscope import snapshot_download
        
        # 设置模型保存路径
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(exist_ok=True)
        
        # 下载SenseVoiceSmall模型（包含所有文件）
        print("\n📥 下载 SenseVoiceSmall 模型...")
        sense_voice_path = snapshot_download(
            'iic/SenseVoiceSmall',
            cache_dir=str(models_dir),
            revision='master'
        )
        print(f"✅ SenseVoiceSmall 下载完成: {sense_voice_path}")
        
        # 下载VAD模型
        print("\n📥 下载 VAD 模型...")
        vad_path = snapshot_download(
            'iic/speech_fsmn_vad_zh-cn-16k-common-pytorch',
            cache_dir=str(models_dir),
            revision='master'
        )
        print(f"✅ VAD 模型下载完成: {vad_path}")
        
        # 列出下载的文件
        print("\n📂 下载的文件列表:")
        sense_voice_files = list(Path(sense_voice_path).glob("**/*"))
        py_files = [f for f in sense_voice_files if f.suffix == '.py']
        
        if py_files:
            print(f"\n✅ 找到 {len(py_files)} 个 Python 文件:")
            for py_file in py_files:
                print(f"   - {py_file.name}")
        else:
            print("\n⚠️  警告：未找到 Python 文件！")
        
        print("\n" + "=" * 70)
        print("✅ 模型下载完成！")
        print("=" * 70)
        
        return sense_voice_path, vad_path
        
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return None, None

if __name__ == "__main__":
    download_models()