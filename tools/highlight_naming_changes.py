#!/usr/bin/env python3
"""Add tracked editorial highlights to the existing lossless proposed stream.

This is an annotation pass, not a website implementation or a second text
renderer. Requires the original renderer's tracking, cached font/source stream,
ffmpeg, numpy, OpenCV and Pillow; never modifies either input stream.
"""
import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SS = 600, 1298, 30, 4
AMBER, KEYLINE, WASH = (255, 202, 84), (88, 50, 0), (255, 217, 106)
SPECS = {
    "adult-nav": (115, 5, "COURSES"),
    "youth-nav": (124, 5, "COURSES"),
    "adult-all": (149, 5, "Courses"),
    "youth-all": (156, 6, "Courses"),
}
SAMPLES = {
    402, 405, 406, 407, 408, 414, 420, 429, 435, 450, 465, 473, 474,
    626, 627, 628, 629, 630, 631, 632, 633, 658, 659, 660, 661, 690,
    718, 719, 720, 742, 743, 744, 745, 746, 750, 751, 754, 756, 757,
    758, 759, 780, 791, 792, 793, 810, 818, 825, 830, 840, 842, 867,
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def bounds(mask):
    y, x = np.nonzero(mask > .015)
    return [int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1]


def glyph(text, font):
    # Identical supersampling, raster size and anchor as the original renderer.
    layer = Image.new("L", (150 * 16, 45 * 16))
    ImageDraw.Draw(layer).text((0, 0), text, font=font, fill=255, anchor="lt")
    return np.asarray(layer.resize((150, 45), Image.Resampling.LANCZOS),
                      dtype=np.float32) / 255


def annotate(im, ink_box, scale, clip, bg):
    """Draw a complete subpixel box first, then crop, never cap viewport edges."""
    ix0, iy0, ix1, iy1 = ink_box
    top, bottom = clip
    visible = max(0., min(iy1, bottom) - max(iy0, top))
    opacity = min(1., visible / min(12., iy1 - iy0))
    if not opacity:
        return None
    # The opening menu's vertical geometry, including padding/radius/stroke,
    # scales with its recorded scaleY rather than popping to full height.
    horizontal_pad = 5 if bg[0] == 255 else 3
    rect = [ix0 - horizontal_pad, iy0 - 5 * scale,
            ix1 + horizontal_pad, iy1 + 5 * scale]
    x0 = max(0, math.floor(rect[0] - 4))
    x1 = min(W, math.ceil(rect[2] + 4))
    y0 = max(top, math.floor(rect[1] - 4))
    y1 = min(bottom, math.ceil(rect[3] + 4))
    if y1 <= y0 or x1 <= x0:
        return None
    size = ((x1 - x0) * SS, (y1 - y0) * SS)
    # Oversample the local vertical coordinate by inverse scale, then compress
    # the complete annotation. This preserves the source scaleY opening.
    shape_scale = max(scale, .001)
    tall_size = (size[0], max(1, round(size[1] / shape_scale)))
    local = [(rect[0] - x0) * SS, (rect[1] - y0) * SS / shape_scale,
             (rect[2] - x0) * SS, (rect[3] - y0) * SS / shape_scale]
    fill = Image.new("L", tall_size)
    ImageDraw.Draw(fill).rounded_rectangle(local, radius=6 * SS, fill=255)
    edge = Image.new("L", tall_size)
    ImageDraw.Draw(edge).rounded_rectangle(local, radius=6 * SS,
                                          outline=255, width=round(2.5 * SS))
    shadow = edge.filter(ImageFilter.GaussianBlur(1.1 * SS))
    masks = [
        np.asarray(m.resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS),
                   dtype=np.float32) / 255
        for m in (fill, shadow, edge)
    ]
    patch = im[y0:y1, x0:x1]
    # Preserve glyph pixels including all AA; permit near-background recording
    # noise outside the word so the annotation's border is not stippled.
    exact_background = np.all(patch == bg, axis=2)
    clean_background = np.max(np.abs(patch.astype(float) - bg), axis=2) <= 12
    gx0, gy0 = max(x0, math.floor(ix0)), max(y0, math.floor(iy0))
    gx1, gy1 = min(x1, math.ceil(ix1)), min(y1, math.ceil(iy1))
    clean_background[gy0-y0:gy1-y0, gx0-x0:gx1-x0] = exact_background[
        gy0-y0:gy1-y0, gx0-x0:gx1-x0]
    result = patch.astype(np.float32)
    wash_alpha = .08 if bg[0] == 255 else 0.
    for n, (mask, color, alpha) in enumerate(
            zip(masks, (WASH, KEYLINE, AMBER), (wash_alpha, .90, 1.))):
        allowed = exact_background if n == 0 else clean_background
        a = (mask * alpha * opacity * allowed)[..., None]
        result = result * (1 - a) + np.array(color) * a
    patch[:] = np.clip(np.rint(result), 0, 255).astype(np.uint8)
    return {
        "ink_box": [round(v, 3) for v in ink_box],
        "highlight_box": [round(v, 3) for v in rect],
        "clip": [top, bottom],
        "opacity": round(opacity, 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working-dir", type=Path, default=Path("/tmp/ww-naming"))
    parser.add_argument("--tracking", type=Path,
                        default=Path("content/sources/womens-wilderness-naming-media.json"))
    parser.add_argument("--report", type=Path,
                        default=Path("content/sources/womens-wilderness-naming-highlights.json"))
    args = parser.parse_args()
    root = args.working_dir
    metadata = json.loads(args.tracking.read_text())
    source = root / "ww-naming-proposed.mkv"
    target = root / "ww-naming-proposed-highlighted.mkv"
    assert sha(source) == metadata["outputs"]["proposed"]["sha256"]
    font_path = root / "source-sans-pro.ttf"
    assert sha(font_path) == metadata["font"]["converted_ttf_sha256"]
    font = ImageFont.truetype(str(font_path), round(27.6923077 * 16))
    glyphs = {text: glyph(text, font) for text in ("COURSES", "Courses")}
    cap = cv2.VideoCapture(str(root / "source-30fps.mkv"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 240)
    ok, raw = cap.read()
    assert ok
    raw = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
    home = np.clip((255. - raw[662:714, :, 1]) / 255, 0, 1)
    home_box = bounds(home)
    cap.release()
    writer = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v",
         "ffv1", "-level", "3", "-y", str(target)], stdin=subprocess.PIPE)
    cap = cv2.VideoCapture(str(source))
    records, counts = [], Counter()
    preview_dir = root / "highlight-previews"
    preview_dir.mkdir(exist_ok=True)
    for track in metadata["tracking"]:
        ok, raw = cap.read()
        assert ok
        im = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
        before = im.copy()
        overlays = []
        for edit in track["edits"]:
            name, y = edit["name"], edit["y"]
            scale = edit.get("scale_y", 1.)
            if name == "homepage":
                box = [home_box[0], y + home_box[1],
                       home_box[2], y + home_box[3]]
                bg = [255, 255, 255]
            else:
                x, dy, text = SPECS[name]
                mask = glyphs[text]
                if scale != 1:
                    mask = cv2.warpAffine(
                        mask, np.array([[1, 0, 0], [0, scale, 0]], np.float32),
                        (mask.shape[1], int(np.ceil(mask.shape[0] * scale))))
                bb = bounds(mask)
                box = [x + bb[0], y + dy * scale + bb[1],
                       x + bb[2], y + dy * scale + bb[3]]
                bg = [0, 34, 74]
            clip = [track["top"],
                    edit.get("reveal_clip_bottom", track["bottom"])]
            overlay = annotate(im, box, scale, clip, bg)
            if overlay:
                overlays.append({"name": name, **overlay})
                counts[name] += 1
            # Every non-background pixel within the changed word is preserved.
            x0, y0 = max(0, math.floor(box[0])), max(clip[0], math.floor(box[1]))
            x1, y1 = min(W, math.ceil(box[2])), min(clip[1], math.ceil(box[3]))
            original = before[y0:y1, x0:x1]
            changed = im[y0:y1, x0:x1]
            non_bg = np.any(original != bg, axis=2)
            assert np.array_equal(original[non_bg], changed[non_bg])
        assert np.array_equal(im[:track["top"]], before[:track["top"]])
        assert np.array_equal(im[track["bottom"]:], before[track["bottom"]:])
        if not track["edits"]:
            assert np.array_equal(im, before)
        writer.stdin.write(im.tobytes())
        i = track["frame"]
        if i in SAMPLES:
            Image.fromarray(im).save(preview_dir / f"highlighted-{i:04}.png")
        records.append({"frame": i, "highlights": overlays})
    assert not cap.read()[0], "Input stream has untracked extra frames"
    cap.release()
    writer.stdin.close()
    assert writer.wait() == 0
    report = {
        "purpose": "Editorial highlights mark changed labels in the proposed terminology mockup; not a live website implementation, usability test, or measured result.",
        "script": "tools/highlight_naming_changes.py",
        "input_proposed": {"file": source.name, "sha256": sha(source)},
        "input_tracking": {"file": str(args.tracking), "sha256": sha(args.tracking)},
        "output": {"file": target.name, "bytes": target.stat().st_size,
                   "sha256": sha(target), **metadata["output"]},
        "style": {"name": "amber", "outline_rgb": AMBER, "outline_width_px": 2.5,
                  "soft_dark_keyline_rgb": KEYLINE, "background_wash_rgb": WASH,
                  "homepage_background_wash_opacity": .08,
                  "menu_background_wash_opacity": 0,
                  "text_preservation": "All non-background pixels within changed-word glyph bounds, including antialiased edges, remain byte-for-byte unchanged."},
        "geometry": "Changed word only. Original renderer's source glyph bounds, fractional per-frame y, scaleY and viewport/reveal clips. Full box is cropped at clips; no artificial border caps. Last partial-letter frames fade with visible height under 12px.",
        "invariants": {"original_input_unmodified": True, "proposed_input_unmodified": True,
                       "all_input_frames_retained": True, "audio": False,
                       "unchanged_frames_pixel_identical": True,
                       "browser_chrome_pixel_identical": True,
                       "changed_word_foreground_pixel_identical": True},
        "highlight_frames_by_label": dict(counts),
        "tracking": records,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "tracking"}, indent=2))


if __name__ == "__main__":
    main()
