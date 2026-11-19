"""Test targets for checking geometry and colour on paper."""

from __future__ import annotations

from PIL import Image, ImageDraw


def geometry_target(width_in: float, height_in: float, ppi: int = 300) -> Image.Image:
    """Grid with 1/4 in minor and 1 in major lines, a border rectangle and centre cross.

    Print it as the 'photo' at exact image size and check with a ruler:
    every major square should measure exactly 1 inch.
    """
    w, h = round(width_in * ppi), round(height_in * ppi)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    step = ppi // 4
    for i, x in enumerate(range(0, w, step)):
        d.line([(x, 0), (x, h)], fill=(0, 0, 0) if i % 4 == 0 else (170, 170, 170), width=3 if i % 4 == 0 else 1)
    for i, y in enumerate(range(0, h, step)):
        d.line([(0, y), (w, y)], fill=(0, 0, 0) if i % 4 == 0 else (170, 170, 170), width=3 if i % 4 == 0 else 1)
    d.rectangle([0, 0, w - 1, h - 1], outline=(220, 0, 0), width=4)
    cx, cy = w // 2, h // 2
    d.line([(cx - ppi // 2, cy), (cx + ppi // 2, cy)], fill=(220, 0, 0), width=3)
    d.line([(cx, cy - ppi // 2), (cx, cy + ppi // 2)], fill=(220, 0, 0), width=3)
    d.text((ppi // 8, ppi // 8), f'{width_in} x {height_in} in @ {ppi} ppi', fill=(0, 0, 0))
    return img


def colour_target(width_in: float = 4, height_in: float = 6, ppi: int = 300) -> Image.Image:
    """Hue sweep, neutral grey ramp and primaries: quick visual check for colour casts."""
    w, h = round(width_in * ppi), round(height_in * ppi)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    band = h // 4
    # Hue sweep
    import colorsys

    for x in range(w):
        r, g, b = colorsys.hsv_to_rgb(x / w, 1.0, 1.0)
        d.line([(x, 0), (x, band)], fill=(int(r * 255), int(g * 255), int(b * 255)))
    # 21-step grey ramp
    steps = 21
    for i in range(steps):
        v = round(255 * i / (steps - 1))
        d.rectangle([i * w // steps, band, (i + 1) * w // steps, 2 * band], fill=(v, v, v))
    # Primaries and secondaries
    swatches = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0)]
    for i, c in enumerate(swatches):
        d.rectangle([i * w // 6, 2 * band, (i + 1) * w // 6, 3 * band], fill=c)
    # Skin-ish tones and near-white/near-black detail
    tones = [(241, 194, 167), (224, 172, 138), (198, 134, 100), (141, 85, 60), (250, 250, 250), (6, 6, 6)]
    for i, c in enumerate(tones):
        d.rectangle([i * w // 6, 3 * band, (i + 1) * w // 6, h], fill=c)
    return img
