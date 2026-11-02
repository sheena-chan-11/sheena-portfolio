"""Rebuild exterior-transparent annotated previews. Requires Pillow.

Run from any directory; optional --preview-dir writes pale/dark visual checks.
Original reference images are read-only. The complete green rectangles are kept.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path

from PIL import Image, __version__ as pillow_version

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "public/assets"
NAMES = ("program", "competitor")
ANNOTATIONS = {
    "program": (2, 147, 528, 688),
    "competitor": (2, 255, 528, 796),
}
STROKE_WIDTH = 4
ANNOTATION_RGB = (2, 195, 154)
HARDWARE_X = (46, 486)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def horizontal_annotation(name, y):
    _, top, _, bottom = ANNOTATIONS[name]
    return top <= y < top + STROKE_WIDTH or bottom - STROKE_WIDTH <= y < bottom


def annotation_points(name):
    left, top, right, bottom = ANNOTATIONS[name]
    for y in range(top, bottom):
        for x in range(left, right):
            if (x < left + STROKE_WIDTH or x >= right - STROKE_WIDTH
                    or y < top + STROKE_WIDTH or y >= bottom - STROKE_WIDTH):
                yield x, y


def coverage(rgb, foreground):
    shade = round(sum(rgb) / 3)
    edge = round(sum(foreground) / 3)
    return max(0, min(255, round(255 * (255 - shade) / max(1, 255 - edge))))


def build(name, originals, preview_dir):
    source_path = ASSETS / f"ww-{name}-preview.png"
    source_sha = sha(source_path)
    src = originals[name]
    alternate = originals[NAMES[1 - NAMES.index(name)]]
    out = src.convert("RGBA")
    spans = {}
    for y in range(src.height):
        # The other screenshot has clean hardware at these horizontal crossings.
        clean = alternate if horizontal_annotation(name, y) else src
        core = [x for x in range(*HARDWARE_X) if min(clean.getpixel((x, y))) < 220]
        if core:
            spans[y] = (core[0], core[-1], clean)

    for y in range(src.height):
        if y not in spans:
            # Source y902 has faint gray antialias but no dark hardware core.
            nearby = min(spans, key=lambda yy: abs(yy - y))
            left, right, _ = spans[nearby]
            for x in range(src.width):
                rgb = src.getpixel((x, y))
                if left <= x <= right and min(rgb) < 255 and max(rgb) - min(rgb) < 3:
                    foreground = src.getpixel((x, nearby))
                    out.putpixel((x, y), (*foreground, coverage(rgb, foreground)))
                else:
                    out.putpixel((x, y), (0, 0, 0, 0))
            continue
        left, right, clean = spans[y]
        for x in range(src.width):
            if left <= x <= right:
                continue  # All enclosed screenshot/hardware RGB stays exact and opaque.
            if not HARDWARE_X[0] <= x < HARDWARE_X[1]:
                out.putpixel((x, y), (0, 0, 0, 0))
                continue
            edge = left if x < left else right
            foreground = clean.getpixel((edge, y))
            alpha = coverage(clean.getpixel((x, y)), foreground)
            color = src.getpixel((x, y)) if horizontal_annotation(name, y) else foreground
            out.putpixel((x, y), (*color, alpha))

    # Union the ENTIRE original rectangle with the phone silhouette, including
    # both vertical sides and horizontal portions outside the physical hardware.
    points = list(annotation_points(name))
    for point in points:
        assert src.getpixel(point) == ANNOTATION_RGB, (name, point)
        out.putpixel(point, (*src.getpixel(point), 255))
    assert all(out.getpixel(p) == (*src.getpixel(p), 255) for p in points)

    retained = white_count = 0
    for y, (left, right, _) in spans.items():
        for x in range(left, right + 1):
            rgb = src.getpixel((x, y))
            assert out.getpixel((x, y)) == (*rgb, 255)
            retained += 1
            white_count += rgb == (255, 255, 255)
    corners = ((0, 0), (src.width - 1, 0), (0, src.height - 1),
               (src.width - 1, src.height - 1))
    assert all(out.getpixel(p)[3] == 0 for p in corners)
    assert out.mode == "RGBA" and out.size == src.size
    assert out.getchannel("A").getextrema() == (0, 255)
    assert sha(source_path) == source_sha

    output_path = ASSETS / f"ww-{name}-preview-transparent.png"
    out.save(output_path, optimize=True)
    if preview_dir:
        for label, background in (("lavender", "#faf9fd"), ("dark", "#393445")):
            composite = Image.new("RGBA", out.size, background)
            composite.alpha_composite(out)
            composite.convert("RGB").save(preview_dir / f"ww-{name}-transparent-{label}.png")
    alpha_values = out.getchannel("A").histogram()
    return {
        "source": str(source_path.relative_to(ROOT)),
        "source_sha256": source_sha,
        "output": str(output_path.relative_to(ROOT)),
        "output_sha256": sha(output_path),
        "source_dimensions": list(src.size),
        "output_dimensions": list(out.size),
        "output_mode": out.mode,
        "crop_source_half_open": [0, 0, src.width, src.height],
        "nontransparent_bbox_output_half_open": list(out.getbbox()),
        "nontransparent_bbox_source_half_open": list(out.getbbox()),
        "annotation_source_bbox_half_open": list(ANNOTATIONS[name]),
        "annotation_stroke_width_pixels": STROKE_WIDTH,
        "annotation_rgb": list(ANNOTATION_RGB),
        "checks": {
            "all_four_corner_alpha": 0,
            "alpha_extrema": [0, 255],
            "enclosed_pixels_retained_exactly": retained,
            "enclosed_original_pure_white_pixels_retained_opaque": white_count,
            "complete_original_annotation_pixels_retained_exactly": len(points),
            "all_annotation_pixels_opaque": True,
            "partially_transparent_pixel_count": sum(alpha_values[1:255]),
            "original_source_unchanged": True,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", type=Path, help="Optional pale/dark composite directory")
    args = parser.parse_args()
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
    originals = {name: Image.open(ASSETS / f"ww-{name}-preview.png").convert("RGB")
                 for name in NAMES}
    outputs = [build(name, originals, args.preview_dir) for name in NAMES]
    provenance = {
        "purpose": "Remove exterior white around annotated mobile screenshots while preserving the physical phones AND complete original green annotation rectangles. Original reference PNGs are untouched.",
        "reproducibility_script": "tools/prepare_transparent_previews.py",
        "method": {
            "software": f"Python {platform.python_version()} with Pillow {pillow_version}",
            "silhouette": "For each source y, first and last pixel with minimum RGB component <220 within hardware x range [46,486) define the fully opaque phone interval. Every enclosed RGB pixel stays unchanged and opaque. No global white key is applied to the website/browser UI.",
            "annotation_crossings": "Use the alternate original screenshot for unannotated hardware silhouette samples on each four-pixel horizontal green rule. Its vertical annotation sides are outside the hardware detection range.",
            "annotation_union": "After preparing the phone alpha silhouette, restore the complete original 4px rectangle perimeter as exact original RGB (2,195,154), alpha 255. This includes both vertical sides and all horizontal portions outside the phone. Explicit per-asset bounding rectangles select only the original annotation strokes, not similarly colored screenshot content.",
            "edge_antialias": "Outside the opaque phone interval, nearest core hardware edge RGB estimates foreground. Alpha = clamp(round(255 * (255 - mean(exterior RGB)) / max(1,255 - mean(edge RGB))),0,255). Fully white exterior becomes alpha zero. Original annotation strokes then override phone-edge coverage and remain opaque.",
            "faint_bottom_edge": "Source y902 contains faint neutral gray antialias. Recover its coverage against the matching source x in nearest core row y901, restricted to that row's opaque interval. Other no-core rows become transparent.",
            "canvas": "Keep the complete original 530x905 canvas, half-open source rectangle [0,0,530,905], with no cropping or resampling. This retains the full annotations at x2 through x527.",
            "interior_integrity": "No blur, resampling, screen erasure, screenshot replacement, UI recoloring, rim interpolation, or hardware repainting. All enclosed screenshot/hardware RGB pixels and every original green annotation pixel are exact and opaque.",
        },
        "caveats": [
            "The flattened white-matte originals do not uniquely determine original subpixel foreground colors/coverage. Only exterior phone fringe pixels use the documented nearest-edge estimate; enclosed hardware, screenshot UI, and complete annotations remain exact.",
            "The green rectangles intentionally extend outside the hardware. Their interiors outside the hardware remain transparent, not white-filled.",
            "The full original 530x905 canvas replaces the earlier cropped 440x903 derivatives; consumer image dimensions/aspect ratio should use the current geometry.",
        ],
        "assets": outputs,
    }
    target = ROOT / "content/sources/womens-wilderness-transparent-previews.json"
    target.write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
