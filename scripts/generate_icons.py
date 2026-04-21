"""
generate_icons.py
Generates PNG icons for the RAG Visual Chatbot Chrome extension.
Theme: Olive Green Organic — forest background, olive-pale leaf mark.

Palette (from chatbot CSS):
  --forest:      #2d3a1e   ← background circle
  --olive:       #6b7c45   ← ring accent
  --olive-pale:  #c8d4a8   ← leaf / mark color
  --terracotta:  #c4734a   ← small dot accent (16px skips this)

Run once:  python generate_icons.py
"""

from PIL import Image, ImageDraw
import os, math

sizes      = [16, 48, 128]
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "extension", "icons")
os.makedirs(output_dir, exist_ok=True)

# ── Theme colours ─────────────────────────────────────────────────
FOREST      = (45,  58,  30,  255)   # #2d3a1e
OLIVE       = (107, 124, 69,  255)   # #6b7c45
OLIVE_PALE  = (200, 212, 168, 255)   # #c8d4a8
TERRACOTTA  = (196, 115, 74,  255)   # #c4734a


def draw_leaf(draw, cx, cy, r, color):
    """Draw a simple two-arc leaf centred at (cx, cy) fitting in radius r."""
    # Leaf is two quadratic bezier-like arcs; approximate with polygon points
    pts = []
    steps = 24
    for i in range(steps + 1):
        t = i / steps
        angle = math.pi * t            # 0 → π  (top arc)
        x = cx + r * 0.55 * math.cos(angle - math.pi / 2)
        y = cy + r * 0.85 * math.sin(angle - math.pi / 2) * (1 - 0.3 * abs(math.sin(angle)))
        pts.append((x, y))
    for i in range(steps, -1, -1):
        t = i / steps
        angle = math.pi * t
        x = cx - r * 0.28 * math.cos(angle - math.pi / 2)
        y = cy + r * 0.85 * math.sin(angle - math.pi / 2) * (1 - 0.3 * abs(math.sin(angle)))
        pts.append((x, y))
    draw.polygon(pts, fill=color)


def draw_stem(draw, cx, cy, r, color, width):
    """Thin curved stem at the bottom of the leaf."""
    x0, y0 = cx, cy + r * 0.82
    x1, y1 = cx + r * 0.28, cy + r * 1.05
    draw.line([(x0, y0), (x1, y1)], fill=color, width=max(1, width))


def make_icon(size):
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s    = size
    pad  = max(1, s * 0.04)          # tiny padding so circle doesn't clip
    r    = s / 2 - pad

    cx, cy = s / 2, s / 2

    # ── 1. Forest background circle ───────────────────────────────
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=FOREST
    )

    # ── 2. Olive ring (subtle border) ─────────────────────────────
    ring_w = max(1, round(s * 0.055))
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=OLIVE, width=ring_w
    )

    if size == 16:
        # ── 16 px: just a small olive-pale dot (leaf unreadable at this size)
        dot_r = s * 0.22
        draw.ellipse(
            [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
            fill=OLIVE_PALE
        )

    elif size == 48:
        # ── 48 px: leaf + stem, no terracotta dot
        leaf_r = r * 0.52
        leaf_cx = cx - r * 0.04
        leaf_cy = cy - r * 0.06
        draw_leaf(draw, leaf_cx, leaf_cy, leaf_r, OLIVE_PALE)
        draw_stem(draw, leaf_cx, leaf_cy, leaf_r,
                  color=(200, 212, 168, 180), width=max(1, round(s * 0.04)))

    else:
        # ── 128 px: leaf + stem + small terracotta accent dot
        leaf_r = r * 0.52
        leaf_cx = cx - r * 0.04
        leaf_cy = cy - r * 0.06
        draw_leaf(draw, leaf_cx, leaf_cy, leaf_r, OLIVE_PALE)
        draw_stem(draw, leaf_cx, leaf_cy, leaf_r,
                  color=(200, 212, 168, 180), width=max(1, round(s * 0.025)))

        # Terracotta accent: small dot top-right inside circle
        dot_r  = r * 0.13
        dot_cx = cx + r * 0.52
        dot_cy = cy - r * 0.52
        draw.ellipse(
            [dot_cx - dot_r, dot_cy - dot_r,
             dot_cx + dot_r, dot_cy + dot_r],
            fill=TERRACOTTA
        )

    # ── 3. Anti-alias pass: downscale from 2× ─────────────────────
    # (PIL ellipse is aliased; we rendered at 1× which is fine for
    #  small icons, but for 128 we get a smoother result from 2× down)
    if size >= 128:
        big = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        big_draw = ImageDraw.Draw(big)
        scale = 2
        br = r * scale
        bcx, bcy = size, size  # centre of 2× canvas

        big_draw.ellipse(
            [bcx - br, bcy - br, bcx + br, bcy + br],
            fill=FOREST
        )
        big_draw.ellipse(
            [bcx - br, bcy - br, bcx + br, bcy + br],
            outline=OLIVE, width=ring_w * scale
        )
        blr  = br * 0.52
        blcx = bcx - br * 0.04
        blcy = bcy - br * 0.06
        draw_leaf(big_draw, blcx, blcy, blr, OLIVE_PALE)
        draw_stem(big_draw, blcx, blcy, blr,
                  color=(200, 212, 168, 180),
                  width=max(1, round(size * scale * 0.025)))
        bdr  = br * 0.13
        bdcx = bcx + br * 0.52
        bdcy = bcy - br * 0.52
        big_draw.ellipse(
            [bdcx - bdr, bdcy - bdr, bdcx + bdr, bdcy + bdr],
            fill=TERRACOTTA
        )
        img = big.resize((size, size), Image.LANCZOS)

    path = os.path.join(output_dir, f"icon{size}.png")
    img.save(path, "PNG")
    print(f"  ✓ icon{size}.png  ({size}×{size})")
    return img


if __name__ == "__main__":
    print("Generating icons — Olive Green Organic theme\n")
    for sz in sizes:
        make_icon(sz)
    print("\nDone. Icons saved to extension/icons/")