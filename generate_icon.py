from PIL import Image, ImageDraw
import os

# 创建图标目录
os.makedirs('src-tauri/icons', exist_ok=True)

# 创建不同尺寸的图标
sizes = [(32, '32x32.png'), (128, '128x128.png'), (256, '128x128@2x.png'), 
         (512, 'icon.icns'), (1024, 'icon.png')]

for size, filename in sizes:
    # 创建白色背景
    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 画黑色圆角矩形轮廓 - 模仿你提供的图标
    margin = size // 10
    corner_radius = size // 8
    
    # 画轮廓
    draw.rounded_rectangle([margin, margin, size-margin, size-margin], 
                          radius=corner_radius, 
                          outline=(0, 0, 0, 255), 
                          width=size//20)
    
    # 保存图标
    img.save(f'src-tauri/icons/{filename}')
    print(f'Created {filename}')

# 也创建ico格式用于Windows
if sizes:
    img = Image.new('RGBA', (256, 256), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    margin = 256 // 10
    corner_radius = 256 // 8
    draw.rounded_rectangle([margin, margin, 256-margin, 256-margin], 
                          radius=corner_radius, 
                          outline=(0, 0, 0, 255), 
                          width=256//20)
    img.save('src-tauri/icons/icon.ico')
    print('Created icon.ico')

print('All icons generated successfully!')