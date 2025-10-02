# Ohoo 打包说明

## 准备工作

### 1. 编译 FunASR HTTP 服务器

```bash
cd /Users/yangdongju/Desktop/code_project/C++/FunASR/runtime/websocket
mkdir -p build && cd build
cmake .. && make -j
```

### 2. 准备资源文件

```bash
# 回到Ohoo项目目录
cd /Users/yangdongju/Desktop/code_project/pc/Ohoo

# 创建资源目录
mkdir -p resources/bin
mkdir -p resources/models

# 复制服务器二进制文件
cp /Users/yangdongju/Desktop/code_project/C++/FunASR/runtime/websocket/build/bin/funasr-http-server resources/bin/
chmod +x resources/bin/funasr-http-server

# 复制模型文件
cp -r python-service/models/models/iic resources/models/
```

## 开发测试

```bash
# 使用测试脚本
./test_server.sh

# 或手动运行
npm run tauri dev
```

## 打包应用

### macOS打包

```bash
# 构建生产版本
npm run tauri build

# 生成的.app文件位于：
# src-tauri/target/release/bundle/macos/Ohoo.app
```

### 打包后的应用结构

```
Ohoo.app/
└── Contents/
    ├── MacOS/
    │   └── Ohoo (主程序)
    ├── Resources/
    │   ├── bin/
    │   │   └── funasr-http-server (语音识别服务器)
    │   └── models/
    │       └── iic/
    │           ├── SenseVoiceSmall/ (ASR模型)
    │           └── speech_fsmn_vad_zh-cn-16k-common-onnx/ (VAD模型)
    └── Info.plist
```

## 功能集成说明

1. **自动服务管理**
   - 应用启动时自动检测服务器状态
   - 首次录音时自动启动语音识别服务
   - 应用退出时自动清理服务器进程

2. **资源打包**
   - 服务器二进制文件和模型文件都打包在.app内
   - 无需用户手动安装或配置
   - 支持离线运行

3. **性能优化**
   - 直接PCM传输，零拷贝处理
   - 专业重采样算法
   - 本地服务，低延迟

## 注意事项

1. **模型大小**
   - SenseVoiceSmall: ~200MB
   - VAD模型: ~50MB
   - 打包后应用约 300MB+

2. **系统要求**
   - macOS 10.13+
   - 内存: 2GB+
   - CPU: 支持x86_64或ARM64

3. **首次启动**
   - 首次启动服务器可能需要几秒钟加载模型
   - 后续录音响应会很快

## 故障排除

如果语音识别服务无法启动：

1. 检查资源文件是否完整
2. 查看控制台日志: `Console.app` > 搜索 "Ohoo"
3. 手动测试服务器: `resources/bin/funasr-http-server --help`