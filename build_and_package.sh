#!/bin/bash

# Ohoo应用完整打包脚本
# 包含Python服务器和Tauri应用的完整打包流程

set -e

echo "🚀 开始Ohoo应用完整打包流程"
echo "=" * 50

# 步骤1: 打包Python服务器
echo "📦 步骤1: 打包Python服务器"
cd python-service

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到虚拟环境，请先运行:"
    echo "python -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 安装PyInstaller
pip install pyinstaller

# 构建可执行文件
echo "🔨 构建Python可执行文件..."
pyinstaller --clean --onefile --name=sense_voice_server --console server.py

# 检查构建结果
if [ ! -f "dist/sense_voice_server" ]; then
    echo "❌ Python服务器构建失败"
    exit 1
fi

# 创建Tauri binaries目录
mkdir -p ../src-tauri/binaries

# 复制可执行文件
cp dist/sense_voice_server ../src-tauri/binaries/
chmod +x ../src-tauri/binaries/sense_voice_server

echo "✅ Python服务器打包完成"

# 返回项目根目录
cd ..

# 步骤2: 构建Tauri应用
echo "📱 步骤2: 构建Tauri应用"

# 安装前端依赖
npm install

# 构建Tauri应用
npm run tauri:build

echo "🎉 Ohoo应用打包完成!"
echo ""
echo "📋 构建产物位置:"
echo "• Python服务器: python-service/dist/sense_voice_server"
echo "• Tauri二进制: src-tauri/binaries/sense_voice_server"
echo "• 最终应用: src-tauri/target/release/bundle/"
echo ""
echo "💡 测试建议:"
echo "1. 运行打包后的应用，检查是否能正常启动"
echo "2. 测试录音和转写功能"
echo "3. 检查应用是否独立运行（不依赖外部Python环境）"