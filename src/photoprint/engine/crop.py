"""Rotation and aspect-locked cropping."""

from __future__ import annotations

from PIL import Image

from ..models import Crop

_ROTATE = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180, 270: Image.Transpose.ROTATE_90}


def rotate(img: Image.Image, degrees: int) -> Image.Image:
    """Rotate clockwise by 0/90/180/270 degrees."""
    degrees %= 360
    if degrees not in (0, 90, 180, 270):
        raise ValueError("rotate must be a multiple of 90")
    return img.transpose(_ROTATE[degrees]) if degrees else img


def centre_crop(img_w: int, img_h: int, aspect: float) -> Crop:
    """Largest centred crop with the given w/h aspect, in normalised coordinates."""
    img_aspect = img_w / img_h
    if img_aspect > aspect:  # image too wide: trim the sides
        w = aspect / img_aspect
        return Crop(x=(1 - w) / 2, y=0.0, w=w, h=1.0)
    h = img_aspect / aspect  # image too tall: trim top and bottom
    return Crop(x=0.0, y=(1 - h) / 2, w=1.0, h=h)


def orient_aspect(portrait_aspect: float, img_w: int, img_h: int) -> float:
    """Pick the print aspect that matches the photo's orientation."""
    return portrait_aspect if img_h >= img_w else 1.0 / portrait_aspect


def apply_crop(img: Image.Image, crop: Crop) -> Image.Image:
    w, h = img.size
    box = (
        round(crop.x * w),
        round(crop.y * h),
        round((crop.x + crop.w) * w),
        round((crop.y + crop.h) * h),
    )
    return img.crop(box)
