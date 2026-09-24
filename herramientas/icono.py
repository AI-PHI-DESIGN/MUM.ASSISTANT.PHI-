"""Genera el icono del programa (icono.png) — lo usa la compilación de GitHub."""
from PIL import Image, ImageDraw, ImageFont

T = 512
img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((16, 16, T - 16, T - 16), radius=110, fill=(37, 77, 107, 255))
try:
    fuente = ImageFont.truetype("georgia.ttf", 330)
except OSError:
    try:
        fuente = ImageFont.truetype("DejaVuSerif.ttf", 330)
    except OSError:
        fuente = ImageFont.load_default(size=330)
d.text((T / 2, T / 2 + 10), "P", font=fuente, fill="white", anchor="mm")
img.save("icono.png")
print("icono.png generado")
