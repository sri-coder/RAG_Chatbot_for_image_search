"""
generate_icons.py
Generates simple placeholder PNG icons for the Chrome extension.
Run this once: python scripts/generate_icons.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

sizes = [16, 48, 128]
output_dir = os.path.join(os.path.dirname(__file__), "../extension/icons")
os.makedirs(output_dir, exist_ok=True)

for size in sizes:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    draw.ellipse([0, 0, size-1, size-1], fill=(79, 70, 229, 255))

    # Simple "R" letter for RAG
    if size >= 48:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size * 0.5))
        except:
            font = ImageFont.load_default()
        text = "R"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(
            ((size - text_w) // 2, (size - text_h) // 2 - bbox[1]),
            text, fill="white", font=font
        )
    else:
        draw.ellipse([size//4, size//4, 3*size//4, 3*size//4], fill="white")

    path = os.path.join(output_dir, f"icon{size}.png")
    img.save(path)
    print(f"Created: {path}")

print("Icons generated successfully!")
