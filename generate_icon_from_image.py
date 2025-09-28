from PIL import Image, ImageOps
import os
import sys

def generate_icons_from_source(source_image_path):
    """
    从源图片生成Tauri应用所需的所有图标尺寸
    
    Args:
        source_image_path: 源图片路径（推荐使用1024x1024像素的PNG图片）
    """
    
    # 检查源图片是否存在
    if not os.path.exists(source_image_path):
        print(f"❌ 源图片不存在: {source_image_path}")
        return False
    
    # 创建图标目录
    icon_dir = 'src-tauri/icons'
    os.makedirs(icon_dir, exist_ok=True)
    
    try:
        # 打开并处理源图片
        source_img = Image.open(source_image_path)
        print(f"📸 源图片尺寸: {source_img.size}")
        
        # 确保图片是RGBA模式
        if source_img.mode != 'RGBA':
            source_img = source_img.convert('RGBA')
        
        # 如果图片不是正方形，居中裁剪为正方形
        width, height = source_img.size
        if width != height:
            size = min(width, height)
            # 计算裁剪位置（居中）
            left = (width - size) // 2
            top = (height - size) // 2
            right = left + size
            bottom = top + size
            source_img = source_img.crop((left, top, right, bottom))
            print(f"🔲 图片已裁剪为正方形: {source_img.size}")
        
        # 定义需要生成的尺寸和文件名
        icon_sizes = [
            (32, '32x32.png'),
            (128, '128x128.png'), 
            (256, '128x128@2x.png'),  # 2x版本
            (512, 'icon.icns'),
            (1024, 'icon.png'),
            (256, 'icon.ico')  # Windows图标
        ]
        
        # 生成各种尺寸的图标
        for size, filename in icon_sizes:
            # 调整图片尺寸
            resized_img = source_img.resize((size, size), Image.Resampling.LANCZOS)
            
            # 保存图标
            file_path = os.path.join(icon_dir, filename)
            
            if filename.endswith('.ico'):
                # Windows ICO格式需要特殊处理
                resized_img.save(file_path, format='ICO')
            else:
                resized_img.save(file_path, format='PNG')
            
            print(f"✅ 创建: {filename} ({size}x{size})")
        
        print("\n🎉 所有图标生成成功！")
        print("\n📋 生成的文件:")
        for _, filename in icon_sizes:
            file_path = os.path.join(icon_dir, filename)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  - {filename} ({file_size/1024:.1f} KB)")
        
        print("\n🔧 下一步操作:")
        print("1. 运行 'npm run tauri build' 重新构建应用")
        print("2. 清除macOS图标缓存: killall Dock && killall Finder") 
        print("3. 如果图标还是旧的，可能需要删除应用重新安装")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成图标时出错: {e}")
        return False

def main():
    print("🎨 Tauri应用图标生成器")
    print("=" * 40)
    
    # 检查命令行参数
    if len(sys.argv) != 2:
        print("📝 使用方法:")
        print("  python generate_icon_from_image.py <图片路径>")
        print("\n💡 建议:")
        print("  - 使用1024x1024像素的PNG图片获得最佳效果")
        print("  - 图片应该有透明背景或适合的背景")
        print("  - 避免使用过于复杂的细节，小尺寸时可能看不清")
        print("\n📖 示例:")
        print("  python generate_icon_from_image.py my_icon.png")
        print("  python generate_icon_from_image.py /path/to/icon.jpg")
        return
    
    source_image = sys.argv[1]
    
    # 生成图标
    success = generate_icons_from_source(source_image)
    
    if success:
        print("\n✨ 图标生成完成！请重新构建应用以查看新图标。")
    else:
        print("\n💥 图标生成失败，请检查源图片和错误信息。")

if __name__ == "__main__":
    main()