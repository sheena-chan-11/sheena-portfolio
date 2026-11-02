"""Build a frame-locked comparison from equal-length edited working videos.

Requires ffmpeg, ffprobe, and Pillow. Input videos must already contain the
original/proposed terminology and identical black browser-chrome normalization.
Only the combined WebM/MP4/poster ship; no playback synchronization JS is needed.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path):
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames,r_frame_rate,width,height",
        "-of", "json", str(path),
    ])
    return json.loads(result)["streams"][0]


def prepare_frame(work):
    source = ROOT / "public/assets/ww-iphone-frame.png"
    frame = Image.open(source).convert("RGBA")
    scale = 8
    mask = Image.new("L", (395 * scale, 858 * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, 395 * scale - 1, 858 * scale - 1), radius=60 * scale, fill=255
    )
    mask = mask.resize((395, 858), Image.Resampling.LANCZOS)
    mask_path = work / "screen-mask.png"
    mask.save(mask_path)
    # Normalize only the retained display chrome, never the silver hardware.
    # White clock/home glyphs stay white; reference #202124 becomes black.
    background = (32, 33, 36)
    for y in list(range(23, 72)) + list(range(863, 881)):
        for x in range(22, 417):
            coverage = mask.getpixel((x - 22, y - 23)) / 255
            if not coverage:
                continue
            *rgb, alpha = frame.getpixel((x, y))
            normalized = [
                max(0, min(255, round((value - bg) * 255 / (255 - bg))))
                for value, bg in zip(rgb, background)
            ]
            result = [round(a * (1 - coverage) + b * coverage)
                      for a, b in zip(rgb, normalized)]
            frame.putpixel((x, y), (*result, alpha))
    frame_path = work / "black-status-frame.png"
    frame.save(frame_path)
    # Bake labels into the media too, so full-size playback stays self-labeled.
    header = Image.new("RGBA", (2000, 88), (0, 0, 0, 0))
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
    draw = ImageDraw.Draw(header)
    for x, text in ((240, "Original"), (760, "Proposed")):
        draw.text((x * 2, 16), text, font=font, fill="#08082c", anchor="mt")
    layer = Image.new("RGBA", (1000, 956), (0, 0, 0, 0))
    layer.alpha_composite(header.resize((1000, 44), Image.Resampling.LANCZOS))
    layer.alpha_composite(frame, (20, 44))
    layer.alpha_composite(frame, (540, 44))
    layer_path = work / "labeled-phone-layer.png"
    layer.save(layer_path)
    return source, frame_path, layer_path, mask_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("proposed", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--basename", default="ww-naming-comparison")
    parser.add_argument("--highlights-provenance", type=Path)
    args = parser.parse_args()
    work = args.work or Path(tempfile.mkdtemp(prefix="ww-naming-composite-"))
    work.mkdir(parents=True, exist_ok=True)
    left, right = probe(args.original), probe(args.proposed)
    frames = int(left["nb_read_frames"])
    assert frames == int(right["nb_read_frames"]), "Inputs must be frame-locked."
    assert Fraction(left["r_frame_rate"]) == Fraction(right["r_frame_rate"]) == 30
    source_frame, frame, layer, mask = prepare_frame(work)
    duration = frames / 30
    assets = ROOT / "public/assets"
    assert Path(args.basename).name == args.basename
    mp4 = assets / (args.basename + ".mp4")
    webm = assets / (args.basename + ".webm")
    poster = assets / (args.basename + "-poster.jpg")
    graph = (
        f"color=c=0xfaf9fd:s=1000x956:r=30:d={duration},format=rgba[bg];"
        "[0:v]setpts=PTS-STARTPTS,scale=395:858:flags=lanczos,format=rgba[left];"
        "[1:v]setpts=PTS-STARTPTS,scale=395:858:flags=lanczos,format=rgba[right];"
        "[3:v]format=gray,split=2[ml][mr];"
        "[left][ml]alphamerge[al];[right][mr]alphamerge[ar];"
        "[bg][al]overlay=x=42:y=67:format=rgb:shortest=1[a];"
        "[a][ar]overlay=x=562:y=67:format=rgb:shortest=1[b];"
        "[b][2:v]overlay=x=0:y=0:format=rgb:shortest=1,format=yuv420p,split=2[mp4][webm]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-filter_complex_threads", "1",
        "-i", str(args.original), "-i", str(args.proposed),
        "-loop", "1", "-framerate", "30", "-i", str(layer),
        "-loop", "1", "-framerate", "30", "-i", str(mask),
        "-filter_complex", graph,
        "-map", "[mp4]", "-frames:v", str(frames), "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-threads", "2", "-movflags", "+faststart", str(mp4),
        "-map", "[webm]", "-frames:v", str(frames), "-an",
        "-c:v", "libvpx-vp9", "-deadline", "good", "-cpu-used", "4",
        "-row-mt", "1", "-threads", "4", "-crf", "30", "-b:v", "0", str(webm),
    ], check=True)
    poster_time = 28 if duration >= 28.5 else min(0.25, duration / 2)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(poster_time), "-i", str(mp4), "-frames:v", "1", "-q:v", "2",
        str(poster),
    ], check=True)
    output = {
        "purpose": "Original / proposed terminology illustration, not a live or tested redesign.",
        "synchronization": "Both phones are rendered into each frame of ONE video. Zero playback drift is possible, including loops, seeks, and buffering.",
        "timing": {"fps": 30, "frames": frames, "duration_seconds": duration,
                   "poster_seconds": poster_time,
                   "speed": "1x, unchanged original recording pace"},
        "canvas": {"width": 1000, "height": 956, "background": "#faf9fd",
                   "phone_origins": [[20, 44], [540, 44]],
                   "phone_size": [440, 903], "display_offset": [22, 23],
                   "display_size": [395, 858]},
        "labels": ["Original", "Proposed"],
        "label_rendering": "Baked into each frame, including the poster and full-size media; DejaVu Sans Bold 28px, supersampled 2x.",
        "working_inputs": [
            {"name": p.name, "sha256": sha(p)} for p in (args.original, args.proposed)
        ],
        "phone_frame": {
            "source": str(source_frame.relative_to(ROOT)),
            "sha256": sha(source_frame),
            "normalization": "Only retained status/home display strips are normalized from #202124 to black; white glyphs and exterior silver hardware remain. Decorative 12:37 clock is not recording-time evidence.",
            "normalized_intermediate_sha256": sha(frame),
        },
        "outputs": [
            {"path": str(p.relative_to(ROOT)), "sha256": sha(p),
             "bytes": p.stat().st_size} for p in (mp4, webm, poster)
        ],
        "reproduction": "tools/compose_naming_comparison.py ORIGINAL_WORKING_VIDEO PROPOSED_WORKING_VIDEO",
    }
    if args.highlights_provenance:
        provenance = args.highlights_provenance.resolve()
        output["annotations"] = {
            "path": str(provenance.relative_to(ROOT)),
            "sha256": sha(provenance),
            "description": "Amber outlines identify only the newly updated Courses labels in the proposed view.",
        }
        output["reproduction"] += (
            " --basename " + args.basename +
            " --highlights-provenance " + str(provenance.relative_to(ROOT))
        )
    (ROOT / "content/sources/womens-wilderness-naming-comparison.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
