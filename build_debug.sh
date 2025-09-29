#!/bin/bash

# Ohoo Debug 版本构建脚本
# 功能：快速构建debug版本，保持sidecar文件更新

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在正确的目录
if [ ! -f "package.json" ] || [ ! -d "src-tauri" ] || [ ! -d "python-service" ]; then
    log_error "请在 Ohoo 项目根目录运行此脚本！"
    exit 1
fi

log_info "🛠️  开始构建 Ohoo Debug 版本..."
echo "=================================================="

# 步骤1: 重新打包Python服务（如果需要）
PYTHON_CHANGED=false

# 检查Python服务是否有更新
if [ ! -f "python-service/dist/sense_voice_server" ]; then
    PYTHON_CHANGED=true
elif [ "python-service/server.py" -nt "python-service/dist/sense_voice_server" ]; then
    PYTHON_CHANGED=true
fi

if [ "$PYTHON_CHANGED" = true ]; then
    log_info "🐍 Python 服务有更新，重新打包..."
    cd python-service
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
        log_success "已激活 Python 虚拟环境"
    else
        log_error "未找到 Python 虚拟环境！"
        exit 1
    fi
    
    # 清理旧文件
    rm -rf dist build
    
    # 重新打包
    pyinstaller sense_voice_server.spec
    
    if [ ! -f "dist/sense_voice_server" ]; then
        log_error "Python 服务打包失败！"
        exit 1
    fi
    
    log_success "Python 服务打包完成"
    cd ..
else
    log_info "🐍 Python 服务无需更新"
fi

# 步骤2: 更新sidecar文件
log_info "🔗 更新 sidecar 文件"
mkdir -p src-tauri/binaries

# 复制到sidecar目录
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    cp python-service/dist/sense_voice_server src-tauri/binaries/sense_voice_server-x86_64-apple-darwin
    cp python-service/dist/sense_voice_server src-tauri/binaries/sense_voice_server-aarch64-apple-darwin
    cp python-service/dist/sense_voice_server src-tauri/binaries/sense_voice_server
    log_success "已更新 macOS sidecar 文件"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    cp python-service/dist/sense_voice_server src-tauri/binaries/sense_voice_server-x86_64-unknown-linux-gnu
    cp python-service/dist/sense_voice_server src-tauri/binaries/sense_voice_server
    log_success "已更新 Linux sidecar 文件"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    cp python-service/dist/sense_voice_server.exe src-tauri/binaries/sense_voice_server-x86_64-pc-windows-msvc.exe
    cp python-service/dist/sense_voice_server.exe src-tauri/binaries/sense_voice_server.exe
    log_success "已更新 Windows sidecar 文件"
fi

# 步骤3: 构建debug版本的Tauri应用
log_info "⚡ 构建 Tauri Debug 版本"

# 强制重新构建（解决缓存问题）
rm -rf src-tauri/target/debug

# 构建debug版本
npm run tauri dev &
DEV_PID=$!

log_success "🎉 Debug 版本启动中..."
log_info "📝 开发服务器 PID: $DEV_PID"
log_info "🛑 按 Ctrl+C 停止开发服务器"

# 等待用户按Ctrl+C
trap "kill $DEV_PID 2>/dev/null; log_info '已停止开发服务器'; exit 0" SIGINT

wait $DEV_PID