from PIL import Image, ImageDraw, ImageFilter, ImageOps
import os
import sys

def create_rounded_mask(size, radius):
    """创建圆角遮罩"""
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size, size], radius=radius, fill=255)
    return mask

def add_subtle_shadow(img, offset=3, blur=5, opacity=30):
    """添加微妙阴影"""
    # 创建阴影层
    shadow = Image.new('RGBA', (img.width + offset*2, img.height + offset*2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    
    # 在偏移位置画一个半透明的形状作为阴影
    shadow_shape = Image.new('RGBA', img.size, (0, 0, 0, opacity))
    shadow.paste(shadow_shape, (offset, offset))
    
    # 模糊阴影
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    
    # 将原图粘贴到阴影上
    result = Image.new('RGBA', shadow.size, (0, 0, 0, 0))
    result.paste(shadow, (0, 0))
    result.paste(img, (0, 0), img)
    
    return result

def generate_icon_variants(source_image_path, style='auto'):
    """
    生成多种风格的图标
    
    Args:
        source_image_path: 源图片路径
        style: 图标风格
            - 'transparent': 纯透明背景
            - 'rounded_white': 圆角白色背景
            - 'rounded_subtle': 圆角微妙背景
            - 'modern': 现代风格(圆角+阴影)
            - 'auto': 自动选择最适合的风格
    """
    
    if not os.path.exists(source_image_path):
        print(f"❌ 源图片不存在: {source_image_path}")
        return False
    
    # 创建图标目录
    icon_dir = 'src-tauri/icons'
    os.makedirs(icon_dir, exist_ok=True)
    
    try:
        # 打开源图片
        source_img = Image.open(source_image_path)
        print(f"📸 源图片: {source_img.size}, 模式: {source_img.mode}")
        
        # 确保是RGBA模式
        if source_img.mode != 'RGBA':
            source_img = source_img.convert('RGBA')
        
        # 裁剪为正方形
        width, height = source_img.size
        if width != height:
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            source_img = source_img.crop((left, top, left + size, top + size))
            print(f"🔲 已裁剪为正方形: {source_img.size}")
        
        # 定义图标尺寸
        icon_sizes = [
            (32, '32x32.png'),
            (128, '128x128.png'), 
            (256, '128x128@2x.png'),
            (512, 'icon.icns'),
            (1024, 'icon.png'),
            (256, 'icon.ico')
        ]
        
        print(f"\n🎨 生成图标风格: {style}")
        
        for size, filename in icon_sizes:
            print(f"⚙️ 处理 {filename} ({size}x{size})...")
            
            # 调整基础尺寸
            base_img = source_img.resize((size, size), Image.Resampling.LANCZOS)
            
            # 根据风格处理图标
            if style == 'transparent':
                # 纯透明背景 - 确保透明度正确
                final_img = base_img
                
            elif style == 'rounded_white':
                # 圆角白色背景
                final_img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
                mask = create_rounded_mask(size, size // 8)  # 12.5% 圆角
                final_img = Image.composite(final_img, Image.new('RGBA', (size, size), (0, 0, 0, 0)), mask)
                
                # 缩放原图并居中放置
                content_size = int(size * 0.8)  # 内容占80%
                content_img = source_img.resize((content_size, content_size), Image.Resampling.LANCZOS)
                offset = (size - content_size) // 2
                final_img.paste(content_img, (offset, offset), content_img)
                
            elif style == 'rounded_subtle':
                # 圆角微妙背景
                final_img = Image.new('RGBA', (size, size), (248, 249, 250, 255))  # 非常浅的灰色
                mask = create_rounded_mask(size, size // 6)  # 更大的圆角
                final_img = Image.composite(final_img, Image.new('RGBA', (size, size), (0, 0, 0, 0)), mask)
                
                # 缩放原图并居中
                content_size = int(size * 0.75)
                content_img = source_img.resize((content_size, content_size), Image.Resampling.LANCZOS)
                offset = (size - content_size) // 2
                final_img.paste(content_img, (offset, offset), content_img)
                
            elif style == 'modern':
                # 现代风格：圆角+阴影+渐变背景
                # 创建渐变背景
                gradient = Image.new('RGBA', (size, size), (255, 255, 255, 255))
                for y in range(size):
                    alpha = int(255 * (1 - y / size * 0.1))  # 微妙渐变
                    color = (250, 251, 252, alpha)
                    gradient.paste(color, (0, y, size, y + 1))
                
                # 应用圆角
                mask = create_rounded_mask(size, size // 5)
                final_img = Image.composite(gradient, Image.new('RGBA', (size, size), (0, 0, 0, 0)), mask)
                
                # 添加内容
                content_size = int(size * 0.7)
                content_img = source_img.resize((content_size, content_size), Image.Resampling.LANCZOS)
                offset = (size - content_size) // 2
                final_img.paste(content_img, (offset, offset), content_img)
                
                # 添加微妙阴影
                if size >= 128:  # 只为大尺寸添加阴影
                    final_img = add_subtle_shadow(final_img)
                    final_img = final_img.resize((size, size), Image.Resampling.LANCZOS)
                
            else:  # auto - 自动选择
                # 检查图片是否有足够的边距
                # 如果图片内容靠近边缘，使用带背景的版本
                final_img = Image.new('RGBA', (size, size), (255, 255, 255, 240))  # 半透明白色
                mask = create_rounded_mask(size, size // 8)
                final_img = Image.composite(final_img, Image.new('RGBA', (size, size), (0, 0, 0, 0)), mask)
                
                content_size = int(size * 0.8)
                content_img = source_img.resize((content_size, content_size), Image.Resampling.LANCZOS)
                offset = (size - content_size) // 2
                final_img.paste(content_img, (offset, offset), content_img)
            
            # 保存文件
            file_path = os.path.join(icon_dir, filename)
            
            if filename.endswith('.ico'):
                final_img.save(file_path, format='ICO')
            elif filename.endswith('.icns'):
                # 对于macOS，确保透明度正确处理
                final_img.save(file_path, format='PNG')
            else:
                final_img.save(file_path, format='PNG')
            
            print(f"✅ 已生成: {filename}")
        
        # 生成预览图
        preview_size = 256
        preview_img = source_img.resize((preview_size, preview_size), Image.Resampling.LANCZOS)
        preview_path = 'icon_preview.png'
        preview_img.save(preview_path)
        print(f"\n🔍 预览图已保存: {preview_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成图标时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🎨 macOS图标问题解决器")
    print("=" * 50)
    
    styles = {
        '1': ('transparent', '纯透明背景（可能被macOS添加白色背景）'),
        '2': ('rounded_white', '圆角白色背景（推荐）'),
        '3': ('rounded_subtle', '圆角微妙灰色背景'),
        '4': ('modern', '现代风格（圆角+阴影+渐变）'),
        '5': ('auto', '自动选择最佳风格')
    }
    
    if len(sys.argv) < 2:
        print("📝 使用方法:")
        print("  python advanced_icon_generator.py <图片路径> [风格编号]")
        print("\n🎨 可选风格:")
        for key, (style, desc) in styles.items():
            print(f"  {key}. {desc}")
        print(f"\n📖 示例:")
        print(f"  python advanced_icon_generator.py jimeng-2025-09-28-1424-背景透明.png 2")
        return
    
    source_image = sys.argv[1]
    
    # 获取风格选择
    style_choice = sys.argv[2] if len(sys.argv) > 2 else '2'  # 默认圆角白色
    
    if style_choice in styles:
        style_name, style_desc = styles[style_choice]
        print(f"🎯 选择的风格: {style_desc}")
    else:
        style_name = 'rounded_white'
        print(f"⚠️ 无效选择，使用默认风格: 圆角白色背景")
    
    # 生成图标
    success = generate_icon_variants(source_image, style_name)
    
    if success:
        print("\n🎉 图标生成完成！")
        print("\n📋 下一步:")
        print("1. npm run tauri build  # 重新构建应用")
        print("2. killall Dock && killall Finder  # 清除图标缓存")
        print("3. 如果还是白色方块，尝试不同的风格选项")
        
        print(f"\n💡 建议:")
        print(f"• 推荐使用风格2（圆角白色背景）避免macOS的白色方块问题")
        print(f"• 如果您想要完全透明，可以尝试风格1，但macOS可能仍会添加背景")
        print(f"• 风格4（现代风格）最接近原生macOS应用的外观")
    else:
        print("\n💥 图标生成失败")

if __name__ == "__main__":
    main()