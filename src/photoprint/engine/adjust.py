"""Global tone and colour adjustments, done in float32.

Exposure and white balance are applied in linear light; contrast and
saturation in gamma-encoded sRGB, which is how they feel to a photographer.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from ..models import Edits


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _is_identity(e: Edits) -> bool:
    return not any((e.exposure, e.contrast, e.temperature, e.tint, e.saturation))


def apply_adjustments(img: Image.Image, e: Edits) -> Image.Image:
    """Apply exposure, white balance, contrast and saturation. Sharpening is separate."""
    if _is_identity(e):
        return img

    a = np.asarray(img, dtype=np.float32) / 255.0

    # Linear-light operations
    lin = srgb_to_linear(a)
    lin *= 2.0 ** e.exposure
    # White balance: temperature trades red against blue, tint trades green against magenta.
    wb = np.array(
        [1.0 + 0.15 * e.temperature, 1.0 - 0.10 * e.tint, 1.0 - 0.15 * e.temperature],
        dtype=np.float32,
    )
    lin *= wb
    a = linear_to_srgb(lin)

    # Contrast: positive blends towards a normalised S-curve (endpoints fixed),
    # negative flattens towards mid-grey.
    if e.contrast > 0:
        k = 6.0
        s = 1.0 / (1.0 + np.exp(-k * (a - 0.5)))
        s0, s1 = 1.0 / (1.0 + np.exp(k / 2)), 1.0 / (1.0 + np.exp(-k / 2))
        s = (s - s0) / (s1 - s0)
        a = a + (s - a) * e.contrast
    elif e.contrast < 0:
        a = 0.5 + (a - 0.5) * (1.0 + 0.5 * e.contrast)

    # Saturation: blend with Rec.709 luma
    if e.saturation:
        luma = (a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32))[..., None]
        a = luma + (a - luma) * (1.0 + e.saturation)

    a = np.clip(a, 0.0, 1.0)
    return Image.fromarray((a * 255.0 + 0.5).astype(np.uint8), "RGB")


def output_sharpen(img: Image.Image, amount: float, ppi: int = 300) -> Image.Image:
    """Light unsharp mask for print, applied after resampling to print size."""
    if amount <= 0:
        return img
    radius = 1.0 * ppi / 300
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=int(40 + 120 * amount), threshold=2))
