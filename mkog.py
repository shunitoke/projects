"""og:image из лицевой стороны визитки: 1200x630 JPEG.

Снимаем .card в 3x, срезаем 3 мм вылетов, вписываем по высоте 630 и центрируем
на холсте 1200x630, залитом тилом. Мессенджеры webp не показывают, поэтому JPEG.
"""
from PIL import Image, ImageFilter

TILE = (0, 59, 59)
SRC = '/tmp/gstmp/visitka-front.png'
OUT = '/home/shuni/projects/portfolio/assets/og-preview-20261103.jpg'

img = Image.open(SRC).convert('RGB')
w, h = img.size
bleed = round(h * 3 / 56)
img = img.crop((bleed, bleed, w - bleed, h - bleed))

scale = 630 / img.height
img = img.resize((round(img.width * scale), 630), Image.LANCZOS)

canvas = Image.new('RGB', (1200, 630), TILE)

shadow = Image.new('RGB', (1200, 630), TILE)
dark = Image.new('RGB', img.size, (0, 32, 32))
mask = Image.new('L', img.size, 90)
shadow.paste(dark, ((1200 - img.width) // 2 + 6, 6), mask)
shadow = shadow.filter(ImageFilter.GaussianBlur(18))
canvas = Image.blend(canvas, shadow, 0.55)

canvas.paste(img, ((1200 - img.width) // 2, 0))
canvas.save(OUT, 'JPEG', quality=88, optimize=True)
print(f'og-preview: {canvas.size}, {round(len(open(OUT, "rb").read())/1024)} КБ')
