#!/bin/bash

# Ohoo 自动化构建脚本
# 功能：Python服务打包 + Tauri应用构建 + 发布文件夹准备

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查是否在正确的目录
if [ ! -f "package.json" ] || [ ! -d "src-tauri" ] || [ ! -d "python-service" ]; then
    log_error "请在 Ohoo 项目根目录运行此脚本！"
    exit 1
fi

log_info "🚀 开始构建 Ohoo 应用..."
echo "=================================================="

# 步骤1: 清理旧的构建文件
log_info "📦 步骤1: 清理旧的构建文件"
if [ -d "Release" ]; then
    rm -rf Release
    log_success "已清理 Release 文件夹"
fi

if [ -d "python-service/dist" ]; then
    rm -rf python-service/dist
    log_success "已清理 Python 服务构建文件"
fi

if [ -d "python-service/build" ]; then
    rm -rf python-service/build
    log_success "已清理 Python 服务临时文件"
fi

# 清理 Tauri 构建缓存 (解决debug版本问题)
if [ -d "src-tauri/target" ]; then
    rm -rf src-tauri/target
    log_success "已清理 Tauri 构建缓存"
fi

# 步骤2: 构建Python服务
log_info "🐍 步骤2: 构建 Python 服务"
cd python-service

# 检查虚拟环境
if [ ! -d "venv" ]; then
    log_error "未找到 Python 虚拟环境！请先运行: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate
log_success "已激活 Python 虚拟环境"

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    log_info "安装 PyInstaller..."
    pip install pyinstaller
fi

# 打包Python服务
log_info "正在打包 Python 服务..."
pyinstaller sense_voice_server.spec

if [ ! -f "dist/sense_voice_server" ]; then
    log_error "Python 服务打包失败！"
    exit 1
fi

log_success "Python 服务打包完成"
cd ..

# 步骤3: 准备sidecar文件
log_info "🔗 步骤3: 更新 sidecar 文件"
mkdir -p src-tauri/binaries

# 复制到sidecar目录（根据平台）
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

# 步骤4: 构建前端
log_info "🌐 步骤4: 构建前端应用"
npm run build
log_success "前端构建完成"

# 步骤5: 构建Tauri应用
log_info "⚡ 步骤5: 构建 Tauri 应用"
npm run tauri build

# 检查构建结果
if [[ "$OSTYPE" == "darwin"* ]]; then
    APP_PATH="src-tauri/target/release/bundle/macos/Ohoo.app"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    APP_PATH="src-tauri/target/release/bundle/appimage/ohoo_1.0.0_amd64.AppImage"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    APP_PATH="src-tauri/target/release/bundle/msi/Ohoo_1.0.0_x64_en-US.msi"
fi

if [ ! -e "$APP_PATH" ]; then
    log_error "Tauri 应用构建失败！"
    exit 1
fi

log_success "Tauri 应用构建完成"

# 步骤6: 准备发布文件夹
log_info "📁 步骤6: 准备发布文件夹"
mkdir -p Release

# 复制应用
if [[ "$OSTYPE" == "darwin"* ]]; then
    cp -r "src-tauri/target/release/bundle/macos/Ohoo.app" Release/
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    cp "src-tauri/target/release/bundle/appimage/ohoo_1.0.0_amd64.AppImage" Release/
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    cp "src-tauri/target/release/bundle/msi/Ohoo_1.0.0_x64_en-US.msi" Release/
fi

# 复制模型文件夹
if [ -d "python-service/models" ]; then
    cp -r python-service/models Release/
    log_success "已复制模型文件夹"
else
    log_warning "未找到模型文件夹，用户需要手动下载模型"
fi

# 创建使用说明
cat > Release/README.md << EOF
# Ohoo 语音识别应用

## 使用方法

1. **运行应用**
   - macOS: 双击 \`Ohoo.app\`
   - Linux: 运行 \`./ohoo_1.0.0_amd64.AppImage\`
   - Windows: 运行安装程序

2. **模型文件**
   - 模型文件位于 \`models/\` 文件夹中
   - 如果缺少模型，应用会自动下载（需要网络连接）

3. **注意事项**
   - 请保持 \`models/\` 文件夹与应用在同一目录
   - 首次运行可能需要等待模型加载

## 文件结构

\`\`\`
Release/
├── Ohoo.app (或其他平台的应用文件)
├── models/                    # 模型文件夹
│   └── iic/
│       ├── SenseVoiceSmall/
│       └── speech_fsmn_vad_zh-cn-16k-common-pytorch/
└── README.md                  # 此文件
\`\`\`

## 支持

如有问题，请联系开发者。
EOF

log_success "已创建使用说明"

# 步骤7: 显示构建结果
echo "=================================================="
log_success "🎉 构建完成！"
echo ""
log_info "📊 构建统计:"
echo "   - Python 服务: $(ls -lh python-service/dist/sense_voice_server* | awk '{print $5}')"
if [ -d "Release/models" ]; then
    echo "   - 模型文件: $(du -sh Release/models | awk '{print $1}')"
fi
echo "   - 发布文件夹: $(du -sh Release | awk '{print $1}')"
echo ""
log_info "📂 发布文件位置: $(pwd)/Release"
echo ""
log_info "✅ 可以将 Release 文件夹打包分发给用户！"
echo "=================================================="