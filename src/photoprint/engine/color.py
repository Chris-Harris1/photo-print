"""ICC colour management: sRGB working space -> paper profile, plus soft proofing.

Rule: colour is converted exactly once, here. The Canon driver must be set to
"No colour correction" whenever a paper profile is used.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageCms

_INTENTS = {
    "perceptual": ImageCms.Intent.PERCEPTUAL,
    "relative": ImageCms.Intent.RELATIVE_COLORIMETRIC,
    "saturation": ImageCms.Intent.SATURATION,
    "absolute": ImageCms.Intent.ABSOLUTE_COLORIMETRIC,
}


@lru_cache(maxsize=1)
def srgb_profile() -> ImageCms.ImageCmsProfile:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))


@lru_cache(maxsize=16)
def _profile(path: str) -> ImageCms.ImageCmsProfile:
    return ImageCms.ImageCmsProfile(path)


def _flags(bpc: bool) -> ImageCms.Flags:
    return ImageCms.Flags.BLACKPOINTCOMPENSATION if bpc else ImageCms.Flags.NONE


@lru_cache(maxsize=16)
def output_transform(icc_path: str, intent: str, bpc: bool) -> ImageCms.ImageCmsTransform:
    return ImageCms.buildTransform(
        srgb_profile(),
        _profile(icc_path),
        "RGB",
        "RGB",
        renderingIntent=_INTENTS[intent],
        flags=_flags(bpc),
    )


def to_paper(img: Image.Image, icc_path: str | Path | None, intent: str = "relative", bpc: bool = True) -> Image.Image:
    """Convert an sRGB page to printer/paper RGB. No profile = return unchanged."""
    if not icc_path:
        return img
    return ImageCms.applyTransform(img, output_transform(str(icc_path), intent, bpc))


def soft_proof(
    img: Image.Image,
    icc_path: str | Path,
    monitor_icc: str | Path | None = None,
    intent: str = "relative",
    bpc: bool = True,
    gamut_warning: bool = False,
) -> Image.Image:
    """Simulate the print on screen: sRGB -> paper -> monitor."""
    monitor = _profile(str(monitor_icc)) if monitor_icc else srgb_profile()
    flags = _flags(bpc) | ImageCms.Flags.SOFTPROOFING
    if gamut_warning:
        flags |= ImageCms.Flags.GAMUTCHECK
    transform = ImageCms.buildProofTransform(
        srgb_profile(),
        monitor,
        _profile(str(icc_path)),
        "RGB",
        "RGB",
        renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
        proofRenderingIntent=_INTENTS[intent],
        flags=flags,
    )
    return ImageCms.applyTransform(img, transform)
