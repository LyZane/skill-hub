#!/usr/bin/env python3
"""Slice a long e-commerce detail image at guide positions stored in a PSD/PSB.

Guide coordinates are parsed straight from the PSD/PSB image-resources block
(resource id 1032, "grid and guides"), so this works regardless of Photoshop's
30000px canvas limit. Pixels are taken from a flat exported image (PNG/JPG),
because Pillow cannot open PSB and psd-tools refuses merged images taller than
30000px. If no flat image is supplied and the canvas is within 30000px, the
script falls back to reading the merged image via psd-tools (optional dep).

Requires: Pillow. Optional: psd-tools (only for the no-flat-image fallback).
"""
import argparse
import os
import struct
import sys

MAX_PSD_AXIS = 30000


def parse_psd(path):
    """Return ((width, height), [(position_px, direction), ...]).

    direction: 0 = vertical guide, 1 = horizontal guide (Adobe spec).
    """
    guides = []
    with open(path, "rb") as f:
        if f.read(4) != b"8BPS":
            raise SystemExit("error: %s is not a PSD/PSB file" % path)
        f.read(2)  # version (1=PSD, 2=PSB) - layout below is identical here
        f.read(6)
        _ch, height, width, _depth, _mode = struct.unpack(">HIIHH", f.read(14))
        (n,) = struct.unpack(">I", f.read(4))
        f.seek(n, 1)  # color mode data
        (n,) = struct.unpack(">I", f.read(4))  # image resources length
        end = f.tell() + n
        while f.tell() < end:
            if f.read(4) != b"8BIM":
                break
            (rid,) = struct.unpack(">H", f.read(2))
            nlen = f.read(1)[0]
            f.read(nlen)
            if (1 + nlen) % 2:
                f.read(1)
            (rl,) = struct.unpack(">I", f.read(4))
            data = f.read(rl)
            if rl % 2:
                f.read(1)
            if rid == 1032:  # grid and guides resource
                (count,) = struct.unpack(">I", data[12:16])
                off = 16
                for _ in range(count):
                    pos, direction = struct.unpack(">IB", data[off:off + 5])
                    off += 5
                    guides.append((pos / 32.0, direction))  # stored in 1/32 px
    return (width, height), guides


def load_pixels(image_path, psd_path, canvas):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    if image_path:
        return Image.open(image_path)
    if not psd_path:
        raise SystemExit("error: nothing to read - pass --image and/or --psd.")
    w, h = canvas
    if max(w, h) > MAX_PSD_AXIS:
        raise SystemExit(
            "error: canvas %dx%d exceeds %dpx; the merged image cannot be read "
            "from the PSD/PSB. Export a flat PNG/JPG from Photoshop and pass it "
            "via --image." % (w, h, MAX_PSD_AXIS))
    try:
        from psd_tools import PSDImage
    except ImportError:
        raise SystemExit(
            "error: no --image given and psd-tools is not installed. Either "
            "pass a flat exported image via --image, or `pip install psd-tools`.")
    return PSDImage.open(psd_path).topil()


def make_bounds(size, positions, slice_height):
    if positions:
        bounds = [0] + sorted({max(0, min(size, round(p))) for p in positions}) + [size]
    elif slice_height:
        bounds = list(range(0, size, slice_height)) + [size]
    else:
        return None
    # drop zero-height duplicates
    return [b for i, b in enumerate(bounds) if i == 0 or b > bounds[i - 1]]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--psd", help="PSD/PSB file containing the guides (omit when using --slice-height on a flat image)")
    ap.add_argument("--image", help="flat exported long image (PNG/JPG); omit only if canvas <= 30000px")
    ap.add_argument("--out", help="output dir (default: <image dir>/切片)")
    ap.add_argument("--format", choices=["png", "jpg"], default="png")
    ap.add_argument("--quality", type=int, default=90, help="JPEG quality (default 90)")
    ap.add_argument("--axis", choices=["auto", "h", "v"], default="auto",
                    help="h = cut at horizontal guides (rows), v = vertical guides (columns)")
    ap.add_argument("--slice-height", type=int,
                    help="fallback: equal-height slices when the file has no guides")
    args = ap.parse_args()

    if args.psd:
        canvas, guides = parse_psd(args.psd)
        h_pos = sorted(p for p, d in guides if d == 1)
        v_pos = sorted(p for p, d in guides if d == 0)
        print("canvas: %dx%d | horizontal guides: %d | vertical guides: %d"
              % (canvas[0], canvas[1], len(h_pos), len(v_pos)))
    else:
        canvas, guides = None, []
        h_pos = v_pos = []

    if args.axis == "auto":
        axis = "h" if h_pos else ("v" if v_pos else None)
    else:
        axis = args.axis
    if axis is None and not args.slice_height:
        raise SystemExit("error: no guides found in %s. Re-check in Photoshop, or "
                         "use --slice-height N for equal-height slicing." % args.psd)
    if axis is not None and args.slice_height:
        print("note: guides found; ignoring --slice-height")

    img = load_pixels(args.image, args.psd, canvas)
    src_name = os.path.splitext(os.path.basename(args.image or args.psd))[0]
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.image or args.psd)), "切片")
    os.makedirs(out_dir, exist_ok=True)

    from PIL import Image
    w, h = img.size
    if axis == "v":
        psd_size, img_size, positions = (canvas[0] if canvas else w), w, v_pos
    else:
        axis = "h"
        psd_size, img_size, positions = (canvas[1] if canvas else h), h, h_pos
    scale = img_size / psd_size
    if abs(scale - 1.0) > 1e-6:
        print("note: image axis %d != psd axis %d, scaling guides by %.4f" % (img_size, psd_size, scale))
        positions = [p * scale for p in positions]

    bounds = make_bounds(img_size, positions, args.slice_height)
    ext = args.format
    saved = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        crop = img.crop((0, a, w, b) if axis == "h" else (a, 0, b, h))
        if ext == "jpg":
            if crop.mode not in ("RGB", "L"):
                bg = Image.new("RGB", crop.size, (255, 255, 255))
                bg.paste(crop, mask=crop.convert("RGBA").split()[3])
                crop = bg
            crop.save(os.path.join(out_dir, "%s_%02d.jpg" % (src_name, i + 1)), quality=args.quality)
        else:
            crop.save(os.path.join(out_dir, "%s_%02d.png" % (src_name, i + 1)))
        saved.append((i + 1, a, b))
        print("slice %02d: %d..%d  (%dpx)" % (i + 1, a, b, b - a))

    # ---- verify: every file decodes, dimensions consistent, no gap/overlap ----
    total = 0
    for i, a, b in saved:
        p = os.path.join(out_dir, "%s_%02d.%s" % (src_name, i, ext))
        with Image.open(p) as chk:
            chk.load()
            cw, ch = chk.size
        if (ch if axis == "h" else cw) != b - a or (cw if axis == "h" else ch) != (w if axis == "h" else h):
            raise SystemExit("VERIFY FAILED: %s dimensions %dx%d unexpected" % (p, cw, ch))
        total += b - a
    if total != img_size:
        raise SystemExit("VERIFY FAILED: slices cover %d of %d px" % (total, img_size))
    print("OK: %d slices, %s coverage %d/%d px -> %s" % (len(saved), axis, total, img_size, out_dir))


if __name__ == "__main__":
    main()
