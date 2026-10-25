#!/usr/bin/env python3
"""Slice a long e-commerce detail image using guides or explicit parameters.

Guide coordinates are parsed straight from the PSD/PSB image-resources block
(resource id 1032), so Photoshop's 30000px canvas limit does not apply. Pixels
come from a flat exported PNG/JPG, or from psd-tools when the canvas is small
enough and no flat image is supplied.

Without guides or explicit parameters, horizontal slices are as even as
possible while every slice satisfies height / width < 2.

Requires: Pillow. Optional: psd-tools (only for the no-flat-image fallback).
"""
import argparse
import os
import struct

MAX_PSD_AXIS = 30000


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


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


def even_bounds(size, count):
    """Split into nearly equal integer lengths; put one remainder unit last."""
    if count < 1 or count > size:
        raise SystemExit("error: --count must be between 1 and the image axis length.")
    base, remainder = divmod(size, count)
    heights = [base] * count
    for i in range(remainder):
        heights[i] += 1
    if remainder:
        # Keep all lengths within 1px, with the last slice carrying one extra unit.
        heights[remainder - 1] -= 1
        heights[-1] += 1
    bounds = [0]
    for height in heights:
        bounds.append(bounds[-1] + height)
    return bounds


def default_bounds(size, cross_size):
    """Use the fewest nearly equal slices with size/cross_size strictly < 2."""
    max_slice_size = 2 * cross_size - 1
    count = (size + max_slice_size - 1) // max_slice_size
    return even_bounds(size, count)


def make_bounds(size, positions, slice_height=None, count=None, default_cross_size=None):
    if positions:
        bounds = [0] + sorted({max(0, min(size, round(p))) for p in positions}) + [size]
    elif slice_height is not None:
        bounds = list(range(0, size, slice_height)) + [size]
    elif count is not None:
        return even_bounds(size, count)
    elif default_cross_size is not None:
        return default_bounds(size, default_cross_size)
    else:
        return None
    # Drop zero-height duplicates at guide positions and at the image edge.
    return [b for i, b in enumerate(bounds) if i == 0 or b > bounds[i - 1]]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--psd", help="PSD/PSB file containing guides")
    ap.add_argument("--image", help="flat exported long image (PNG/JPG); omit only if canvas <= 30000px")
    ap.add_argument("--out", help="output dir (default: <image dir>/<image name>)")
    ap.add_argument("--format", choices=["png", "jpg"], default="png")
    ap.add_argument("--quality", type=int, default=90, help="JPEG quality (default 90)")
    ap.add_argument("--axis", choices=["auto", "h", "v"], default="auto",
                    help="h = rows, v = columns; default auto, falling back to h")
    parameters = ap.add_mutually_exclusive_group()
    parameters.add_argument("--slice-height", type=positive_int,
                            help="fixed slice height when guides are not used")
    parameters.add_argument("--count", type=positive_int,
                            help="nearly equal slice count when guides are not used")
    ap.add_argument("--ignore-guides", action="store_true",
                    help="ignore PSD/PSB guides; use parameters or the default ratio rule")
    args = ap.parse_args()

    if args.psd:
        canvas, guides = parse_psd(args.psd)
        h_pos = sorted(p for p, d in guides if d == 1)
        v_pos = sorted(p for p, d in guides if d == 0)
        print("canvas: %dx%d | horizontal guides: %d | vertical guides: %d"
              % (canvas[0], canvas[1], len(h_pos), len(v_pos)))
        if args.ignore_guides:
            print("note: ignoring PSD/PSB guides as requested")
            h_pos = v_pos = []
    else:
        canvas = None
        h_pos = v_pos = []

    if args.axis == "auto":
        axis = "h" if h_pos else ("v" if v_pos else "h")
    else:
        axis = args.axis
    has_guides = bool(h_pos or v_pos)
    if has_guides and (args.slice_height is not None or args.count is not None):
        print("note: guides take priority; ignoring --slice-height/--count")

    img = load_pixels(args.image, args.psd, canvas)
    src_path = os.path.abspath(args.image or args.psd)
    src_name = os.path.splitext(os.path.basename(src_path))[0]
    out_dir = args.out or os.path.join(os.path.dirname(src_path), src_name)
    os.makedirs(out_dir, exist_ok=True)

    from PIL import Image
    w, h = img.size
    if axis == "v":
        psd_size, img_size, positions = (canvas[0] if canvas else w), w, v_pos
        cross_size = h
    else:
        axis = "h"
        psd_size, img_size, positions = (canvas[1] if canvas else h), h, h_pos
        cross_size = w
    if positions:
        scale = img_size / psd_size
        if abs(scale - 1.0) > 1e-6:
            print("note: image axis %d != psd axis %d, scaling guides by %.4f"
                  % (img_size, psd_size, scale))
            positions = [p * scale for p in positions]

    default_mode = (
        not positions and axis == "h" and
        args.slice_height is None and args.count is None
    )
    bounds = make_bounds(
        img_size,
        positions,
        slice_height=args.slice_height,
        count=args.count,
        default_cross_size=cross_size if default_mode else None,
    )
    if bounds is None:
        raise SystemExit("error: vertical custom slicing requires --slice-height or --count.")
    if default_mode:
        heights = [b - a for a, b in zip(bounds, bounds[1:])]
        print("note: default near-even slicing; every height/width < 2; heights=%s" % heights)

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
            crop.save(os.path.join(out_dir, "%02d.jpg" % (i + 1)), quality=args.quality)
        else:
            crop.save(os.path.join(out_dir, "%02d.png" % (i + 1)))
        saved.append((i + 1, a, b))
        print("slice %02d: %d..%d  (%dpx)" % (i + 1, a, b, b - a))

    # Verify decoding, dimensions, full coverage, and the default strict ratio.
    total = 0
    for i, a, b in saved:
        p = os.path.join(out_dir, "%02d.%s" % (i, ext))
        with Image.open(p) as chk:
            chk.load()
            cw, ch = chk.size
        if (ch if axis == "h" else cw) != b - a or (cw if axis == "h" else ch) != (w if axis == "h" else h):
            raise SystemExit("VERIFY FAILED: %s dimensions %dx%d unexpected" % (p, cw, ch))
        if default_mode and ch >= 2 * cw:
            raise SystemExit("VERIFY FAILED: %s height/width must be strictly < 2" % p)
        total += b - a
    if total != img_size:
        raise SystemExit("VERIFY FAILED: slices cover %d of %d px" % (total, img_size))
    print("OK: %d slices, %s coverage %d/%d px -> %s"
          % (len(saved), axis, total, img_size, out_dir))


if __name__ == "__main__":
    main()
