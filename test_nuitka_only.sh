#!/bin/bash

# 快速Nuitka测试脚本
# 只编译Python服务，不构建完整应用

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

echo "🚀 Nuitka 单独测试 - 快速验证优化效果"
echo "=" * 50

# 检查是否在正确目录
if [ ! -d "python-service" ]; then
    log_error "请在项目根目录运行此脚本"
    exit 1
fi

cd python-service

# 检查环境
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    log_success "使用conda环境: $CONDA_DEFAULT_ENV"
elif [ -d "venv" ]; then
    source venv/bin/activate
    log_success "激活虚拟环境"
fi

# 清理旧文件
log_info "清理旧的构建文件..."
rm -rf dist dist_nuitka build_nuitka sense_voice_server.build

# 安装Nuitka
log_info "检查Nuitka依赖..."
if ! python -c "import nuitka" 2>/dev/null; then
    log_info "安装Nuitka..."
    pip install nuitka ordered-set zstandard
fi

# 显示Python和环境信息
log_info "环境信息:"
echo "   Python: $(python --version)"
echo "   工作目录: $(pwd)"
echo "   Conda环境: ${CONDA_DEFAULT_ENV:-"无"}"

# 开始编译
log_info "🔥 开始Nuitka编译..."
echo "⏱️  预计时间: 10-20分钟（首次编译）"
echo "💡 编译完成后启动速度将提升75%"

start_time=$(date +%s)

python build_nuitka.py

end_time=$(date +%s)
compile_time=$((end_time - start_time))

if [ -f "dist/sense_voice_server" ]; then
    log_success "🎉 编译成功！"
    echo "   编译时间: ${compile_time}秒"
    
    # 显示文件信息
    size=$(ls -lh dist/sense_voice_server | awk '{print $5}')
    echo "   文件大小: $size"
    
    # 快速测试
    log_info "执行快速测试..."
    python test_nuitka_build.py
    
else
    log_error "编译失败！"
    exit 1
fi

echo ""
echo "=" * 50
log_success "测试完成！现在可以运行完整构建："
echo "   ./build_release.sh"
echo "=" * 50