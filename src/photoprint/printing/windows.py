"""Windows printing via GDI with saved driver settings (DEVMODE).

STATUS: milestone 1 spike, written without access to Windows. Every pywin32
call here needs verifying on the real machine with the PRO-100 attached.
Known things to check are marked VERIFY.

How it works
------------
1. capture_devmode(): opens the Canon driver's own Properties dialog. You set
   media type, quality, paper source and *No colour correction* (when using a
   paper ICC profile). The returned DEVMODE is saved to a JSON file: public
   fields plus the driver-private blob (DriverData), where Canon keeps
   settings like media type.
2. print_page(): recreates that DEVMODE, opens a printer DC with it, and draws
   only the image area of the rendered page at its exact physical position,
   compensating for the printer's unprintable offset.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from PIL import Image

from ..models import PageLayout

# Public DEVMODE fields worth persisting. Driver-specific settings live in DriverData.
_FIELDS = [
    "Fields", "Orientation", "PaperSize", "PaperLength", "PaperWidth", "Scale", "Copies",
    "DefaultSource", "PrintQuality", "Color", "Duplex", "YResolution", "TTOption",
    "FormName", "MediaType", "DitherType", "ICMMethod", "ICMIntent",
]

# GetDeviceCaps indices (win32con has these too)
LOGPIXELSX, LOGPIXELSY = 88, 90
PHYSICALWIDTH, PHYSICALHEIGHT = 110, 111
PHYSICALOFFSETX, PHYSICALOFFSETY = 112, 113
HORZRES, VERTRES = 8, 10


def _win():
    import pywintypes  # noqa: F401
    import win32con
    import win32gui
    import win32print
    import win32ui

    return win32con, win32gui, win32print, win32ui


def list_printers() -> list[str]:
    _, _, win32print, _ = _win()
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [p[2] for p in win32print.EnumPrinters(flags)]


def _devmode_to_dict(dm) -> dict:
    data = {f: getattr(dm, f) for f in _FIELDS if hasattr(dm, f)}
    data["DriverData"] = base64.b64encode(bytes(dm.DriverData or b"")).decode()  # VERIFY: DriverData is bytes
    return data


def _dict_to_devmode(printer: str, data: dict):
    """Start from the printer's current DEVMODE (right size/version) and overlay the saved one."""
    _, _, win32print, _ = _win()
    h = win32print.OpenPrinter(printer)
    try:
        dm = win32print.GetPrinter(h, 2)["pDevMode"]
    finally:
        win32print.ClosePrinter(h)
    for f in _FIELDS:
        if f in data:
            try:
                setattr(dm, f, data[f])
            except (AttributeError, TypeError):
                pass  # read-only or unsupported on this driver
    blob = base64.b64decode(data.get("DriverData", ""))
    if blob:
        dm.DriverData = blob  # VERIFY: size must equal dm.DriverExtra
    return dm


def capture_devmode(printer: str, out_path: str | Path) -> Path:
    """Show the driver's Properties dialog and save what the user chose."""
    win32con, _, win32print, _ = _win()
    h = win32print.OpenPrinter(printer)
    try:
        dm = win32print.GetPrinter(h, 2)["pDevMode"]
        mode = win32con.DM_IN_PROMPT | win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER
        ret = win32print.DocumentProperties(0, h, printer, dm, dm, mode)  # VERIFY: signature
        if ret != win32con.IDOK:
            raise RuntimeError("Driver dialog cancelled")
    finally:
        win32print.ClosePrinter(h)
    data = {"printer": printer, "devmode": _devmode_to_dict(dm)}
    out = Path(out_path)
    out.write_text(json.dumps(data, indent=2))
    return out


def _to_portrait(page: Image.Image, layout: PageLayout) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Driver always gets portrait; rotate landscape pages 90 deg counter-clockwise."""
    left, top, w, h = layout.image_box
    if not layout.landscape:
        return page, (left, top, w, h)
    page_w = page.width
    rotated = page.transpose(Image.Transpose.ROTATE_90)
    return rotated, (top, page_w - (left + w), h, w)


def print_page(
    page: Image.Image,
    layout: PageLayout,
    devmode_path: str | Path,
    ppi: int = 300,
    doc_name: str = "photoprint",
) -> dict:
    """Print the image area of a rendered page at its exact physical position.

    Returns diagnostics (printer dpi, offsets, target rect) for the spike log.
    """
    win32con, win32gui, _, win32ui = _win()
    from PIL import ImageWin

    saved = json.loads(Path(devmode_path).read_text())
    printer = saved["printer"]
    dm = _dict_to_devmode(printer, saved["devmode"])
    dm.Orientation = win32con.DMORIENT_PORTRAIT
    dm.Scale = 100

    page, (left, top, w, h) = _to_portrait(page, layout)
    image = page.crop((left, top, left + w, top + h))

    hdc_handle = win32gui.CreateDC("WINSPOOL", printer, dm)  # VERIFY: accepts PyDEVMODE
    dc = win32ui.CreateDCFromHandle(hdc_handle)
    try:
        dpi_x, dpi_y = dc.GetDeviceCaps(LOGPIXELSX), dc.GetDeviceCaps(LOGPIXELSY)
        off_x, off_y = dc.GetDeviceCaps(PHYSICALOFFSETX), dc.GetDeviceCaps(PHYSICALOFFSETY)
        printable_w, printable_h = dc.GetDeviceCaps(HORZRES), dc.GetDeviceCaps(VERTRES)

        # Page pixels (ppi) -> device pixels, measured from the physical paper corner,
        # then shifted into the printable area's coordinate system.
        x0 = round(left / ppi * dpi_x) - off_x
        y0 = round(top / ppi * dpi_y) - off_y
        x1 = x0 + round(w / ppi * dpi_x)
        y1 = y0 + round(h / ppi * dpi_y)

        info = {
            "printer": printer,
            "dpi": (dpi_x, dpi_y),
            "physical_offset": (off_x, off_y),
            "printable": (printable_w, printable_h),
            "target_rect": (x0, y0, x1, y1),
        }
        if x0 < 0 or y0 < 0 or x1 > printable_w or y1 > printable_h:
            raise RuntimeError(f"Image falls outside the printable area: {info}")

        dc.StartDoc(doc_name)
        dc.StartPage()
        ImageWin.Dib(image).draw(dc.GetHandleOutput(), (x0, y0, x1, y1))
        dc.EndPage()
        dc.EndDoc()
        return info
    finally:
        dc.DeleteDC()
