from PIL import Image
import os

def create_icon_from_source(source_path, output_dir):
    """从源图片创建各种尺寸的图标"""
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 打开源图片
        source_img = Image.open(source_path)
        
        # 如果图片是RGBA模式，保持透明度；否则转换为RGB
        if source_img.mode in ('RGBA', 'LA'):
            source_img = source_img.convert('RGBA')
        else:
            source_img = source_img.convert('RGB')
        
        # 定义需要的尺寸和文件名
        sizes = [
            (32, '32x32.png'),
            (128, '128x128.png'), 
            (256, '128x128@2x.png'),
            (512, 'icon.png')
        ]
        
        # 生成不同尺寸的PNG图标
        for size, filename in sizes:
            resized_img = source_img.resize((size, size), Image.Resampling.LANCZOS)
            output_path = os.path.join(output_dir, filename)
            resized_img.save(output_path, 'PNG')
            print(f'✓ Created {filename} ({size}x{size})')
        
        # 生成ICO文件 (Windows)
        ico_img = source_img.resize((256, 256), Image.Resampling.LANCZOS)
        ico_path = os.path.join(output_dir, 'icon.ico')
        ico_img.save(ico_path, 'ICO')
        print(f'✓ Created icon.ico (256x256)')
        
        # 生成ICNS文件 (macOS) - 需要多个尺寸
        icns_sizes = [16, 32, 64, 128, 256, 512, 1024]
        icns_images = []
        
        for size in icns_sizes:
            icns_img = source_img.resize((size, size), Image.Resampling.LANCZOS)
            icns_images.append(icns_img)
        
        # 保存为ICNS (如果Pillow支持)
        try:
            icns_path = os.path.join(output_dir, 'icon.icns')
            # 使用最大尺寸的图片作为基础
            largest_img = source_img.resize((1024, 1024), Image.Resampling.LANCZOS)
            largest_img.save(icns_path, 'ICNS')
            print(f'✓ Created icon.icns (1024x1024)')
        except Exception as e:
            print(f'⚠ Could not create ICNS file: {e}')
            print('  You may need to install additional dependencies or use a different tool for ICNS generation')
        
        print(f'\n✅ All icons generated successfully in {output_dir}')
        
    except FileNotFoundError:
        print(f'❌ Source image not found: {source_path}')
        print('Please save your icon image as "new_icon.png" in the project root directory')
    except Exception as e:
        print(f'❌ Error processing image: {e}')

if __name__ == '__main__':
    # 使用新图标文件
    source_image = 'new_icon.png'  # 您需要将图片保存为这个文件名
    output_directory = 'src-tauri/icons'
    
    print('🎨 Updating app icons...')
    create_icon_from_source(source_image, output_directory)