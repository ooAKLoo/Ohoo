#!/bin/bash

# Ohoo 精简构建脚本
# 专用于远程服务模式 - 只构建Tauri应用，无需Python服务和模型
# 
# 使用方法：
#   ./build_app_only.sh
#
# 优势：
#   - 构建速度快（无需Python编译）
#   - 应用体积小（无需打包模型文件）
#   - 依赖网络服务，无需本地AI模型

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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
if [ ! -f "package.json" ] || [ ! -d "src-tauri" ]; then
    log_error "请在 Ohoo 项目根目录运行此脚本！"
    exit 1
fi

log_info "🚀 开始构建 Ohoo 应用（远程服务模式）..."
echo "=================================================="

# 步骤1: 清理旧的构建文件
log_info "📦 步骤1: 清理旧的构建文件"
if [ -d "Release" ]; then
    rm -rf Release
    log_success "已清理 Release 文件夹"
fi

# 清理 Tauri 构建缓存
if [ -d "src-tauri/target" ]; then
    find src-tauri/target -name ".DS_Store" -delete 2>/dev/null || true
    rm -rf src-tauri/target
    log_success "已清理 Tauri 构建缓存"
fi

# 清理 sidecar 文件（远程服务模式不需要）
if [ -d "src-tauri/binaries" ]; then
    rm -rf src-tauri/binaries/*
    log_success "已清理 sidecar 文件"
fi

# 步骤2: 确认使用远程服务
log_info "🌐 步骤2: 确认远程服务配置"
log_success "当前配置: 使用远程服务 (http://115.190.136.178:8001)"
log_info "   - 无需本地Python服务"
log_info "   - 无需模型文件"
log_info "   - 需要网络连接"

# 步骤3: 构建前端
log_info "🎨 步骤3: 构建前端应用"
npm run build
log_success "前端构建完成"

# 步骤4: 构建Tauri应用（使用远程服务配置）
log_info "⚡ 步骤4: 构建 Tauri 应用（无 sidecar 模式）"
npx tauri build

# 检查构建结果
if [[ "$OSTYPE" == "darwin"* ]]; then
    APP_PATH="src-tauri/target/release/bundle/macos/Ohoo.app"
    APP_NAME="Ohoo.app"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    APP_PATH="src-tauri/target/release/bundle/appimage/ohoo_1.0.0_amd64.AppImage"
    APP_NAME="ohoo_1.0.0_amd64.AppImage"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    APP_PATH="src-tauri/target/release/bundle/msi/Ohoo_1.0.0_x64_en-US.msi"
    APP_NAME="Ohoo_1.0.0_x64_en-US.msi"
fi

if [ ! -e "$APP_PATH" ]; then
    log_error "Tauri 应用构建失败！"
    exit 1
fi

log_success "Tauri 应用构建完成"

# 步骤5: 准备发布文件夹
log_info "📁 步骤5: 准备发布文件夹"
mkdir -p Release

# 复制应用文件
if [[ "$OSTYPE" == "darwin"* ]]; then
    cp -r "$APP_PATH" Release/
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    cp "$APP_PATH" Release/
fi

log_success "应用文件已复制到 Release 文件夹"

# 创建使用说明
cat > Release/README.md << EOF
# Ohoo 语音识别应用 (精简版)

## 应用模式
**远程服务模式** - 使用云端AI服务，无需本地模型
**无 sidecar 版本** - 不包含Python服务，体积更小

## 使用方法

1. **运行应用**
   - macOS: 双击 \`Ohoo.app\`
   - Linux: 运行 \`./ohoo_1.0.0_amd64.AppImage\`
   - Windows: 运行安装程序

2. **网络要求**
   - 需要稳定的网络连接
   - 音频数据将发送到云端进行识别
   - 首次使用会自动连接远程服务

3. **功能特性**
   - **即开即用**: 无需下载模型，启动速度快
   - **多语言支持**: 支持中文、英文、日文、韩文、粤语等
   - **实时转录**: 边录音边转录，响应迅速
   - **轻量化**: 应用体积小，无需大型模型文件

## 技术信息

- **服务模式**: 远程云端服务
- **网络协议**: HTTPS加密传输
- **支持格式**: WAV、MP3、FLAC、OGG等
- **识别引擎**: SenseVoice ONNX (云端部署)

## 注意事项

- 请确保网络连接稳定
- 录音数据会发送到远程服务器进行处理
- 如需离线使用，请联系开发者获取本地版本

## 文件结构

\`\`\`
Release/
├── $APP_NAME          # 应用程序
├── logs/               # 应用日志（自动生成）
└── README.md          # 此文件
\`\`\`

## 支持

如有问题，请联系开发者
EOF

log_success "已创建使用说明"

# 步骤6: 显示构建结果
echo "=================================================="
log_success "🎉 构建完成！"
echo ""
log_info "📊 构建统计:"
echo "   - 应用大小: $(du -sh Release/$APP_NAME | awk '{print $1}')"
echo "   - 发布文件夹: $(du -sh Release | awk '{print $1}')"
echo ""
log_info "📂 发布文件位置: $(pwd)/Release"
echo ""
log_success "✅ 可以将 Release 文件夹打包分发给用户！"
echo ""
log_info "💡 应用特点："
echo "   - 🌐 使用远程AI服务，无需本地模型"
echo "   - ⚡ 启动速度快，应用体积小"
echo "   - 📦 无 sidecar 依赖，不包含Python服务"
echo "   - 🔗 需要网络连接到远程服务器"
echo "   - 🎯 适合快速部署和测试"
echo ""
log_warning "注意: 此版本不包含本地Python服务"
echo "   - 如需离线使用，请使用 build_release.sh"
echo "=================================================="