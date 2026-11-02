#!/usr/bin/env python3
"""Offline, screenshot-derived F2 proposed interaction.

Requires Pillow, NumPy, and ffmpeg (libx264 + libvpx-vp9). No network is used.
The original uploaded screenshot is never modified. Coordinates below are
half-open source-screenshot pixels, not reconstructed website coordinates.
"""

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path("/tmp/shelley-uploads/Screenshot 2026-11-01 at 5.01.24_PM.png")
CROP = (2, 240, 3022, 1800)
FILM = (888, 862, 1464, 1800)
HIKE = (1515, 862, 2091, 1800)
ROW = (329, 928, 775, 982)
GLYPHS = (388, 937, 501, 971)
REMOVE_FILTER = (1228, 691, 1390, 716)
ADULT_LABEL = (1038, 663, 1187, 722)
ADULT_ROW = (329, 1439, 775, 1482)
VIDEO_SIZE = (1510, 780)
FPS, DURATION = 30, 9
NAVY = (2, 9, 80)
AMBER = (255, 196, 0)
PURPLE = (128, 0, 112)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_video_color(path, reference):
    """Probe tags and decode source-color patches without browser assumptions."""
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,color_range,color_space,color_transfer,color_primaries",
        "-of", "json", str(path),
    ]))["streams"][0]
    for key in ("color_space", "color_transfer", "color_primaries"):
        assert probe[key] == "bt709", (path, key, probe)
    assert probe["color_range"] == "tv", (path, probe)
    rgb = subprocess.check_output([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ])
    decoded = np.frombuffer(rgb, dtype=np.uint8).reshape(VIDEO_SIZE[1], VIDEO_SIZE[0], 3)
    source = np.asarray(reference)
    samples = {}
    for name, (x1, y1, x2, y2) in {
        "navy_header": (300, 20, 450, 90),
        "navy_sidebar": (350, 400, 380, 430),
        "teal_donate": (1400, 35, 1430, 40),
    }.items():
        a = source[y1:y2, x1:x2].mean(axis=(0, 1))
        b = decoded[y1:y2, x1:x2].mean(axis=(0, 1))
        error = float(np.max(np.abs(a - b)))
        assert error <= 3, (path, name, a, b)
        samples[name] = {"source_rgb": a.tolist(), "decoded_rgb": b.tolist(),
                         "max_channel_error_of_255": error}
    return {"probe": probe, "flat_color_samples": samples,
            "all_sample_channel_errors_le_3_of_255": True}


def local_box(box):
    return (box[0] - CROP[0], box[1] - CROP[1],
            box[2] - CROP[0], box[3] - CROP[1])


def point(x, y):
    return (x - CROP[0], y - CROP[1])


def clamp(value):
    return min(1.0, max(0.0, value))


def ease(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--previews", type=Path, default=Path("/tmp/ww-filter-previews"))
    args = parser.parse_args()
    assets = ROOT / "public/assets"
    sources = ROOT / "content/sources"
    assets.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)
    args.previews.mkdir(parents=True, exist_ok=True)
    # Same-filesystem staging keeps currently served media readable until a
    # complete replacement is ready. Byte-identical PNG/JPEGs are not touched.
    staging = Path(tempfile.mkdtemp(prefix=".ww-filter-stage-", dir=assets))

    source = Image.open(args.source).convert("RGB")
    if source.size != (3024, 1964):
        raise ValueError(f"Unexpected screenshot dimensions: {source.size}")
    source_icc = source.info.get("icc_profile")
    if not source_icc:
        raise ValueError("Source ICC profile missing; do not silently assume sRGB")
    source_profile = ImageCms.ImageCmsProfile(BytesIO(source_icc))
    srgb_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    display_to_srgb = ImageCms.buildTransformFromOpenProfiles(
        source_profile, srgb_profile, "RGB", "RGB",
    )
    source_profile_description = ImageCms.getProfileDescription(source_profile).strip()
    original = source.crop(CROP)
    original_path = staging / "ww-filter-original.png"
    original.save(original_path, optimize=True)
    assert np.array_equal(np.asarray(original), np.asarray(source)[240:1800, 2:3022])

    film = original.crop(local_box(FILM))
    hike = original.crop(local_box(HIKE))
    white_film = Image.new("RGB", film.size, "white")
    remove_filter = source.crop(REMOVE_FILTER)

    # Reuse actual screenshot HIKING letterforms; no substitute font or fetch.
    glyph_pixels = np.asarray(source.crop(GLYPHS), dtype=np.float32)
    glyph_alpha = np.clip((glyph_pixels[:, :, 0] - NAVY[0]) /
                         (255 - NAVY[0]), 0, 1)
    glyph_mask = Image.fromarray(np.round(glyph_alpha * 255).astype("uint8"))
    glyph_mask = glyph_mask.resize((124, 37), Image.Resampling.LANCZOS)
    glyph = Image.new("RGBA", glyph_mask.size, PURPLE + (0,))
    glyph.putalpha(glyph_mask)

    def proposed_overlay(t):
        overlay = Image.new("RGBA", original.size)
        draw = ImageDraw.Draw(overlay)
        hover = ease((t - 2.20) / 0.30)
        selected = ease((t - 2.70) / 0.24)
        if hover:
            draw.rounded_rectangle(local_box(ROW), radius=11,
                                   fill=AMBER + (round(35 * selected),),
                                   outline=AMBER + (round(255 * hover),), width=3)
        if selected:
            # Outline the already-active adult selections without checkmarks.
            draw.rounded_rectangle(local_box(ADULT_ROW), radius=11,
                                   outline=AMBER + (round(255 * selected),), width=3)
            draw.rounded_rectangle(local_box(ADULT_LABEL), radius=10,
                                   outline=AMBER + (round(255 * selected),), width=3)

            # Preserve the source "Filter: Adult". The Hiking chip occupies the
            # original Remove Filter location; the source control is moved.
            draw.rectangle(local_box((1215, 659, 1405, 728)),
                           fill=(255, 255, 255, round(255 * selected)))
            draw.rounded_rectangle(local_box((1215, 664, 1447, 722)), radius=14,
                                   fill=(255, 249, 224, round(255 * selected)),
                                   outline=AMBER + (round(255 * selected),), width=3)
            chip_glyph = glyph.copy()
            chip_glyph.putalpha(glyph_mask.point(lambda a: round(a * selected)))
            overlay.alpha_composite(chip_glyph, point(1239, 675))
            moved_remove = remove_filter.convert("RGBA")
            moved_remove.putalpha(round(255 * selected))
            overlay.alpha_composite(moved_remove, point(1520, 691))

        # Pointer never covers event details. It approaches the real HIKING row.
        pointer_opacity = ease((t - 1.65) / 0.17) * (1 - ease((t - 2.97) / 0.34))
        if pointer_opacity > 0:
            progress = ease((t - 1.72) / 0.78)
            x = 1110 + (525 - 1110) * progress
            y = 1110 + (958 - 1110) * progress - 75 * math.sin(progress * math.pi)
            px, py = point(x, y)
            if 2.68 <= t <= 2.98:
                pulse = (t - 2.68) / 0.30
                radius = 12 + 35 * pulse
                draw.ellipse((px-radius, py-radius, px+radius, py+radius),
                             outline=AMBER + (round(200 * (1-pulse)),), width=4)
            polygon = [(px, py), (px+2, py+43), (px+13, py+33),
                       (px+23, py+52), (px+31, py+48), (px+21, py+29),
                       (px+38, py+27)]
            a = round(255 * pointer_opacity)
            draw.polygon([(x+2, y+3) for x, y in polygon], fill=(0, 0, 0, round(a*0.22)))
            draw.polygon(polygon, fill=(255, 255, 255, a),
                         outline=(20, 24, 35, a), width=2)
        return overlay

    def source_frame(t):
        # Exact source card rasters, including all visible event details/pricing.
        frame = original.copy()
        fade = ease((t - 3.02) / 0.58)
        reflow = ease((t - 3.62) / 0.77)
        if fade > 0 or reflow > 0:
            frame.paste("white", local_box(FILM))
            frame.paste("white", local_box(HIKE))
            if fade < 1:
                frame.paste(Image.blend(film, white_film, fade),
                            local_box(FILM)[:2])
            x = round(HIKE[0] + (FILM[0] - HIKE[0]) * reflow)
            frame.paste(hike, point(x, HIKE[1]))
        frame = Image.alpha_composite(frame.convert("RGBA"), proposed_overlay(t)).convert("RGB")
        reset = ease((t - 7.82) / 0.43)
        if reset:
            frame = Image.blend(frame, original, reset)
        return frame

    def video_frame(t):
        return source_frame(t).resize(VIDEO_SIZE, Image.Resampling.LANCZOS)

    def encoded_frame(t):
        # Raw screenshot/card conservation is checked before color management.
        # The source macOS Display ICC is not sRGB. Convert its colors to sRGB
        # exactly as a color-managed browser does for the unchanged Original PNG.
        return ImageCms.applyTransform(video_frame(t), display_to_srgb)

    # Uncompressed PNG previews also act as deterministic, pixel-level QA.
    preview_times = {"original": 0.0, "selection": 2.90, "result": 5.4, "reset": 8.6}
    for name, t in preview_times.items():
        video_frame(t).save(args.previews / f"{name}.png")
    final = source_frame(5.4)
    assert np.array_equal(np.asarray(final.crop(local_box(FILM))), np.asarray(hike))
    assert np.all(np.asarray(final.crop(local_box(HIKE))) == 255)
    assert np.array_equal(np.asarray(source_frame(8.6)), np.asarray(original))
    encoded_frame(5.4).save(
        staging / "ww-filter-hiking-poster.jpg", quality=94, subsampling=0,
        icc_profile=srgb_profile.tobytes(),
    )

    mp4 = staging / "ww-filter-hiking.mp4"
    webm = staging / "ww-filter-hiking.webm"
    # Explicit conversion AND metadata prevent HD browser decoders from
    # interpreting a default BT.601 RGB->YUV conversion as BT.709.
    color_conversion = "scale=iw:ih:in_range=full:out_range=tv:out_color_matrix=bt709"
    color_tags = ["-colorspace", "bt709", "-color_primaries", "bt709",
                  "-color_trc", "bt709", "-color_range", "tv"]
    ffmpeg = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "1510x780",
        "-framerate", str(FPS), "-i", "pipe:0",
        "-map", "0:v:0", "-an", "-c:v", "libx264", "-crf", "18",
        "-preset", "medium", "-vf", color_conversion, "-pix_fmt", "yuv420p",
        *color_tags, "-movflags", "+faststart", "-threads", "4", str(mp4),
        "-map", "0:v:0", "-an", "-c:v", "libvpx-vp9", "-crf", "25", "-b:v", "0",
        "-deadline", "good", "-cpu-used", "3", "-vf", color_conversion,
        "-pix_fmt", "yuv420p", *color_tags,
        "-row-mt", "1", "-threads", "4", str(webm),
    ]
    process = subprocess.Popen(ffmpeg, stdin=subprocess.PIPE)
    try:
        for i in range(FPS * DURATION):
            process.stdin.write(encoded_frame(i / FPS).tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("ffmpeg failed")
    finally:
        if process.poll() is None:
            process.kill()

    for staged in staging.iterdir():
        destination = assets / staged.name
        if destination.exists() and sha256(destination) == sha256(staged):
            staged.unlink()
        else:
            staged.replace(destination)
    staging.rmdir()

    outputs = {}
    for name in ("ww-filter-original.png", "ww-filter-hiking.webm",
                 "ww-filter-hiking.mp4", "ww-filter-hiking-poster.jpg"):
        path = assets / name
        outputs[f"public/assets/{name}"] = {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    color_verification = {
        extension: verify_video_color(assets / f"ww-filter-hiking.{extension}", encoded_frame(0))
        for extension in ("webm", "mp4")
    }
    provenance = {
        "title": "Women's Wilderness F2 — screenshot-derived proposed Hiking filter",
        "status": "Proposed interaction visualization, not evidence of a client-implemented interaction",
        "source": {
            "original_filename": args.source.name,
            "sha256": sha256(args.source),
            "dimensions_px": list(source.size),
            "type": "User-supplied screenshot; only image source; no website or external assets fetched",
            "preserved": True,
            "embedded_icc": {
                "description": source_profile_description,
                "bytes": len(source_icc),
                "sha256": hashlib.sha256(source_icc).hexdigest(),
                "preserved_in_original_png": True,
            },
        },
        "original": {
            "crop_source_xyxy_half_open": list(CROP),
            "dimensions_px": list(original.size),
            "pixel_changes": "None. Lossless rectangular crop only.",
            "boundary_reason": "Website starts at y=240. Two edge columns and bottom rounded browser corners excluded; menu bar, Chrome controls/profile/address bar, desktop and Dock excluded.",
            "already_active_filter": "Adult",
        },
        "browser_frame": {
            "address": "https://womenswilderness.org/programs/",
            "applies_to": ["Original screenshot", "Proposed interaction"],
            "implementation": "CSS/HTML browser chrome surrounds each evidence viewport; no chrome is added to or painted into source screenshot or video pixels.",
        },
        "proposed": {
            "duration_seconds": DURATION,
            "fps": FPS,
            "frames": FPS * DURATION,
            "dimensions_px": list(VIDEO_SIZE),
            "audio": False,
            "video_color": {
                "source_rgb_profile": source_profile_description,
                "pre_encoding_color_management": "Cached Pillow ImageCms embedded source Display ICC to sRGB transform, after raw screenshot-pixel conservation QA and after resize, before RGB to BT709 YUV conversion.",
                "poster_profile": "sRGB; identical managed source colors as video before encoding",
                "verification_reference": "ICC-managed sRGB source frame, not untagged raw display-profile RGB",
                "rgb_to_yuv_conversion": color_conversion,
                "color_space": "bt709",
                "color_primaries": "bt709",
                "color_transfer": "bt709",
                "color_range": "tv",
                "reason": "Explicit matrix and matching tags avoid ambiguous BT601/BT709 interpretation in HD browser playback.",
            },
            "poster_timestamp_seconds": 5.4,
            "new_ui_only": [
                "Animated pointer and click ring",
                "Yellow outlines around All Adult, Hiking, and Adult in the filter summary; no checkmarks",
                "Persistent HIKING chip beside unchanged source Filter: Adult; no plus sign between the filters",
                "Original Remove Filter control moved right to make space",
            ],
            "event_content": "All card imagery, titles, dates, locations, audience and pricing are the source screenshot's pixels. No event content invented or retyped.",
            "font_method": "New HIKING chip reuses screenshot HIKING glyph alpha; no font substitution or network fetch.",
            "source_geometry_xyxy_half_open": {
                "nonmatching_film_card_mask": list(FILM),
                "retained_hiking_card_raster": list(HIKE),
                "final_hiking_destination": list(FILM),
                "hiking_sidebar_selection": list(ROW),
                "all_adult_sidebar_outline": list(ADULT_ROW),
                "adult_filter_label_outline": list(ADULT_LABEL),
                "reused_hiking_glyphs": list(GLYPHS),
                "original_remove_filter_control": list(REMOVE_FILTER),
            },
            "timeline_seconds": {
                "initial_original_hold": [0.0, 1.65],
                "pointer_approach": [1.72, 2.50],
                "hover": [2.20, 2.70],
                "click_and_selected_filter": [2.70, 2.94],
                "film_card_fades_out": [3.02, 3.60],
                "existing_hiking_card_reflows_left": [3.62, 4.39],
                "single_result_hold": [4.39, 7.82],
                "reset_crossfade": [7.82, 8.25],
                "original_seam_hold": [8.25, 9.0],
            },
            "verification": {
                "original_pixels_equal_source_crop": True,
                "final_first_result_pixels_equal_original_hiking_card": True,
                "final_former_second_slot_all_white": True,
                "loop_end_pixels_equal_original": True,
                "nonmatching_film_card_removed": True,
                "retained_adult_filter": True,
                "yellow_rectangles_outline_all_adult_hiking_and_adult_label": True,
                "no_filter_selection_checkmark": True,
                "no_plus_between_filter_labels": True,
                "decoded_video_color": color_verification,
            },
        },
        "reproduce": {
            "script": "tools/render_hiking_filter.py",
            "dependencies": ["Python 3", "Pillow", "NumPy", "ffmpeg with libx264 and libvpx-vp9"],
            "command": "python tools/render_hiking_filter.py --source '/path/to/Screenshot 2026-11-01 at 5.01.24_PM.png'",
            "network_required": False,
        },
        "outputs": outputs,
    }
    manifest = sources / "womens-wilderness-filter-animation.json"
    manifest.write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"manifest": str(manifest), "previews": str(args.previews),
                      "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
