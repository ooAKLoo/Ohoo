# Ohoo - 语音转写桌面应用

基于 Tauri + Vue + SenseVoice 的语音转写桌面应用，支持实时录音转写和内容置顶功能。

## 功能特性

- 🎤 实时录音转写
- 📌 内容置顶管理
- 📋 一键复制功能
- 🎨 现代化 UI 设计（Tailwind CSS）
- 🚀 跨平台支持

## 技术栈

- **前端**: Vue 3 + Tailwind CSS + Vite
- **后端**: Tauri (Rust) + Python FastAPI
- **AI模型**: SenseVoice (FunASR)

## 项目结构

```
Ohoo/
├── src/                 # Vue 前端源码
├── src-tauri/          # Rust 后端
├── python-service/     # Python 服务
│   ├── server.py      # FastAPI 服务
│   ├── requirements.txt
│   └── build.py       # 打包脚本
└── README.md
```

## 开发环境设置

### 1. 安装依赖

```bash
# 安装前端依赖
npm install

# 安装 Python 依赖
cd python-service
pip install -r requirements.txt
cd ..
```

### 2. 开发模式运行

```bash
# 启动前端开发服务器
npm run dev

# 或者直接启动 Tauri 开发模式
npm run tauri:dev
```

### 3. 构建应用

```bash
# 首先打包 Python 服务
cd python-service
python build.py
cd ..

# 构建 Tauri 应用
npm run tauri:build
```

## 使用说明

1. 点击麦克风按钮开始录音
2. 再次点击停止录音并自动转写
3. 转写结果会显示在文本框中
4. 点击"置顶"按钮将内容添加到置顶列表
5. 在置顶列表中可以复制或删除内容

## 系统要求

- Node.js 16+
- Rust 1.60+
- Python 3.8+
- 支持麦克风的设备

## 许可证

MIT License