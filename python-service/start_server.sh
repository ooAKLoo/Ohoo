#!/bin/bash
# 启动Python服务

cd "$(dirname "$0")"

# 设置环境变量，强制Python无缓冲输出
export PYTHONUNBUFFERED=1

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 激活环境
source venv/bin/activate

# 升级pip
echo "Upgrading pip..."
pip install --upgrade pip

# 检查并安装依赖
if ! pip list | grep -q funasr; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# 清屏并启动服务
clear
echo "==============================================="
echo "🎤 Ohoo 语音转写服务启动器"
echo "==============================================="
echo ""

# 启动服务
python server.py