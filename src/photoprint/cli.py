"""Command line for the engine and the print spike.

  photoprint render PHOTO --preset P.json [--edits E.json] --out page.tif
  photoprint target geometry|colour --preset P.json --out page.tif [--print]
  photoprint printers
  photoprint capture-devmode --printer "Canon PRO-100 series" --out presets/x.devmode.json
  photoprint print PHOTO --preset P.json [--edits E.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine.load import load_photo
from .engine.render import render_page
from .engine.targets import colour_target, geometry_target
from .models import Edits, Preset


def _edits(path: str | None, photo: str | None = None) -> Edits:
    if path:
        return Edits.load(Path(path))
    if photo:
        sidecar = Path(photo).with_suffix(Path(photo).suffix + ".photoprint.json")
        if sidecar.exists():
            return Edits.load(sidecar)
    return Edits()


def _save(result, out: str, preset: Preset) -> None:
    result.page.save(out, dpi=(preset.ppi, preset.ppi))
    print(f"wrote {out}  page {result.page.size[0]}x{result.page.size[1]} px  "
          f"margins {json.dumps({k: round(v, 3) for k, v in result.layout.margins_in.items()})}  "
          f"source {result.effective_ppi:.0f} ppi")


def _print(result, preset: Preset) -> None:
    if not preset.devmode:
        sys.exit("preset has no devmode; run capture-devmode first")
    from .printing.windows import print_page

    info = print_page(result.page, result.layout, preset.devmode, preset.ppi)
    print(json.dumps(info, indent=2))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="photoprint")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="render a print-ready page to a file")
    r.add_argument("photo")
    r.add_argument("--preset", required=True)
    r.add_argument("--edits")
    r.add_argument("--out", required=True)

    t = sub.add_parser("target", help="render (and optionally print) a test target")
    t.add_argument("kind", choices=["geometry", "colour"])
    t.add_argument("--preset", required=True)
    t.add_argument("--out")
    t.add_argument("--print", action="store_true")

    sub.add_parser("printers", help="list installed printers (Windows)")

    c = sub.add_parser("capture-devmode", help="open the driver dialog and save its settings")
    c.add_argument("--printer", required=True)
    c.add_argument("--out", required=True)

    pr = sub.add_parser("print", help="render and print a photo")
    pr.add_argument("photo")
    pr.add_argument("--preset", required=True)
    pr.add_argument("--edits")

    a = p.parse_args(argv)

    if a.cmd == "render":
        preset = Preset.load(Path(a.preset))
        _save(render_page(load_photo(a.photo), _edits(a.edits, a.photo), preset), a.out, preset)
    elif a.cmd == "target":
        preset = Preset.load(Path(a.preset))
        make = geometry_target if a.kind == "geometry" else colour_target
        img = make(preset.image_w, preset.image_h, preset.ppi)
        result = render_page(img, Edits(sharpen=0), preset)
        if a.out:
            _save(result, a.out, preset)
        if a.print:
            _print(result, preset)
    elif a.cmd == "printers":
        from .printing.windows import list_printers

        print("\n".join(list_printers()))
    elif a.cmd == "capture-devmode":
        from .printing.windows import capture_devmode

        print(f"saved {capture_devmode(a.printer, a.out)}")
    elif a.cmd == "print":
        preset = Preset.load(Path(a.preset))
        _print(render_page(load_photo(a.photo), _edits(a.edits, a.photo), preset), preset)


if __name__ == "__main__":
    main()
