"""Load a photo and bring it into the sRGB working space."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

from .color import srgb_profile


def load_photo(path: str | Path) -> Image.Image:
    """Open a JPEG/TIFF, apply EXIF orientation, and convert to 8-bit sRGB.

    v1 limitation: the working space is sRGB, so wide-gamut (Adobe RGB) files
    are clipped to sRGB. Fine for D7200 sRGB JPEGs; revisit if that changes.
    """
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    icc = img.info.get("icc_profile")

    if img.mode not in ("RGB", "RGBA", "L", "CMYK"):
        img = img.convert("RGB")

    if icc:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        out_mode = "RGB"
        img = ImageCms.profileToProfile(
            img if img.mode != "RGBA" else img.convert("RGB"),
            src,
            srgb_profile(),
            renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
            outputMode=out_mode,
        )
    else:
        img = img.convert("RGB")  # untagged: assume sRGB

    return img
