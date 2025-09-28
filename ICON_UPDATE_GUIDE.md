# 应用图标更新指南

## 步骤1: 保存图标文件
将您提供的紫色渐变图标保存到项目根目录，命名为 `new_icon.png`

## 步骤2: 运行图标生成脚本
```bash
# 确保安装了Pillow库
pip install Pillow

# 运行图标更新脚本
python update_icon.py
```

## 步骤3: 重新构建应用
```bash
# 开发模式查看效果
npm run tauri dev

# 或构建发布版本
npm run tauri build
```

## 生成的文件
脚本将在 `src-tauri/icons/` 目录中生成以下文件：
- `32x32.png` - 小尺寸图标
- `128x128.png` - 中等尺寸图标  
- `128x128@2x.png` - 高DPI中等尺寸图标
- `icon.png` - 大尺寸图标 (512x512)
- `icon.ico` - Windows图标
- `icon.icns` - macOS图标

## 注意事项
- 确保原图片质量足够高，建议至少512x512像素
- 如果ICNS生成失败，可以使用在线工具或专用软件转换
- 更新图标后需要重新构建应用才能看到效果