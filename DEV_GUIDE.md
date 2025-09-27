# Ohoo 开发指南

## 快速启动

### 1. 启动Python服务

在终端1中运行：
```bash
cd python-service
./start_server.sh
```

或手动启动：
```bash
cd python-service
source venv/bin/activate
python server.py
```

服务将在 http://localhost:8001 启动

### 2. 启动Tauri开发服务器

在终端2中运行：
```bash
npm run tauri:dev
```

应用将在新窗口中打开

## 功能说明

- 🎤 **录音转写**: 点击麦克风按钮开始/停止录音
- 📌 **置顶功能**: 将重要文本固定在底部
- 📋 **复制功能**: 点击置顶内容即可复制

## 常见问题

### 端口被占用
```bash
# 查找并杀死占用端口的进程
lsof -ti:1420 | xargs kill -9
lsof -ti:8001 | xargs kill -9
```

### Python依赖安装失败
```bash
# 使用清华源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 首次运行慢
SenseVoice模型首次运行会下载模型文件（约1GB），请耐心等待。

## 项目结构

```
Ohoo/
├── src/                # Vue前端
│   └── App.vue        # 主应用组件
├── src-tauri/         # Rust后端
│   └── src/main.rs    # Tauri主程序
├── python-service/    # Python API服务
│   ├── server.py      # FastAPI服务
│   ├── venv/          # Python虚拟环境
│   └── start_server.sh # 启动脚本
└── package.json       # Node依赖
```

## 生产环境打包

1. 打包Python服务为exe：
```bash
cd python-service
python build.py
```

2. 构建Tauri应用：
```bash
npm run tauri:build
```

## 技术栈

- **前端**: Vue 3 + Tailwind CSS
- **桌面**: Tauri (Rust)
- **后端**: FastAPI (Python)
- **AI**: SenseVoice (阿里FunASR)