#!/bin/bash

# Ohoo 快速构建脚本选择器

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Ohoo 构建脚本选择器${NC}"
echo "=================================================="
echo ""
echo "请选择构建类型："
echo ""
echo -e "${GREEN}1)${NC} Debug 版本   - 快速开发调试 (自动更新sidecar)"
echo -e "${GREEN}2)${NC} Release 版本 - 完整发布构建 (包含打包)"
echo -e "${GREEN}3)${NC} 仅更新 Python 服务"
echo -e "${GREEN}4)${NC} 清理所有构建文件"
echo ""
echo -e "${YELLOW}q)${NC} 退出"
echo ""
read -p "请输入选择 [1-4/q]: " choice

case $choice in
    1)
        echo -e "${BLUE}启动 Debug 构建...${NC}"
        ./build_debug.sh
        ;;
    2)
        echo -e "${BLUE}启动 Release 构建...${NC}"
        ./build_release.sh
        ;;
    3)
        echo -e "${BLUE}仅重新打包 Python 服务...${NC}"
        cd python-service
        if [ -d "venv" ]; then
            source venv/bin/activate
            rm -rf dist build
            pyinstaller sense_voice_server.spec
            echo -e "${GREEN}Python 服务打包完成！${NC}"
        else
            echo -e "${RED}错误: 未找到虚拟环境${NC}"
        fi
        cd ..
        ;;
    4)
        echo -e "${BLUE}清理所有构建文件...${NC}"
        rm -rf Release
        rm -rf python-service/dist
        rm -rf python-service/build
        rm -rf src-tauri/target
        rm -rf dist
        echo -e "${GREEN}清理完成！${NC}"
        ;;
    q|Q)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac