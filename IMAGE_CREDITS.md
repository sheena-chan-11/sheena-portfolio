# Step by Step image

- Source: Pexels photo 4422911 — close-up of sneakers taking a step up stairs.
- Photo page: https://www.pexels.com/photo/4422911/
- Original download: https://images.pexels.com/photos/4422911/pexels-photo-4422911.jpeg?auto=compress&cs=tinysrgb&w=1600
- License: https://www.pexels.com/license/
- License checked October 31, 2026: free use and modification, including website
  use; attribution is not required. The license's restrictions still apply.
- Local copy: `public/assets/step-by-step-movement.jpg`, resized and compressed
  for the portfolio. No hotlinking or paid image service is used at runtime.

The photograph is illustrative stock imagery, not project research or a claim
that the photographed person or footwear brand endorses this project.

## Women’s Wilderness research screenshots

The revised case study reuses the owner’s existing portfolio research artifacts.
The following PNGs are lossless crops of the archived originals in
`public/assets/`; no new interface content or research results were generated.

| Cropped asset | Archived source |
| --- | --- |
| `ww-program-preview.png` | `b6560a2547215e0672c4.png` |
| `ww-competitor-preview.png` | `b6560a2547215e0672c4.png` |
| `ww-adult-programs-label.png` | `f0e8a0efff1ab7ee78c7.png` |
| `ww-courses-label.png` | `24ed8d0e0636eb0b5b6a.png` |
| `ww-filter-proposal.png` | `0b3cb56e974af9c81932.png` |
| `ww-registration-original.png` | `8d2049c5837d6846bace.png` |
| `ww-registration-proposal.png` | `8d2049c5837d6846bace.png` |

Exact crop coordinates and dimensions are recorded in
`content/sources/womens-wilderness-image-crops.json`.
The color-coded synthesis artifact, `ec39ef7f8915abbdd94e.png`, is reused
unchanged. Original full research boards remain available in the repository.

Captions distinguish original interfaces from proposed filtering and availability
changes. The proposals are not presented as implemented or evaluated outcomes.
The owner’s source copy is archived at
`content/sources/womens-wilderness-case-study.pdf`. Its GIF/video notes describe
media not included in the supplied PDF; no animations have been fabricated.

### Desk Research screen recording

- Supplied by the owner: `Screen Recording 2026-10-30 at 4.34.50_PM.mov`.
- Original SHA-256:
  `9737695238bd8dafe00506e7d737d847373ecc50e471d395a8fa46f0da0e7375`.
- Original: 3.1 seconds, 2988×1720, 120 fps, H.264, no audio.
- Website copy: `public/assets/ww-desk-research.mp4`, H.264/yuv420p,
  1494×860, 30 fps, fast-start MP4, approximately 1.4 MB. The complete
  duration is retained with no cropping, additional content, or audio.
- A VP9/WebM version, `public/assets/ww-desk-research.webm`, is offered first
  for browsers without H.264 support, with MP4 as a compatibility fallback.
  Both versions use the same dimensions, duration, and 30 fps.
- Poster: `public/assets/ww-desk-research-poster.jpg`, taken at 0.25 seconds
  from the website video.
- Embedded immediately after the Desk Research paragraph, autoplaying muted
  and looping inline, with no visible caption, pause/play button, native
  controls, or duration display. An accessible video label identifies the
  recording and its lack of audio.
- Playback has a decorative HTML/CSS Chrome-style browser frame matching
  `ww-registration-original.png`, including window dots, a tab, and an address
  bar. Its small favicon is an 18×18 crop from that reference, not an external
  asset. The chrome is noninteractive and hidden from screen readers; the
  video and its existing accessible label are unchanged.

### Mobile competitive-analysis recordings

The owner supplied these three recordings for the comparison points:

| Supplied file | Website asset basename | Placement |
| --- | --- | --- |
| `ww-list.MP4` | `ww-program-list` | Point 1: Women’s Wilderness adult-program navigation |
| `bb-tirps-list.mov` | `bb-trips-list` | Point 1: Backcountry Beauties trips list |
| `bb-waitlist.mov` | `bb-waitlist` | Point 2: Backcountry Beauties trip-to-waitlist flow |

Each website recording has a VP9/WebM version and an H.264/fast-start MP4
fallback at 600×1298 and 30 fps, plus a JPEG poster taken from that recording.
The complete visual recordings are preserved without trimming or cropping.
The original audio tracks are omitted from these silent web copies; playback
is muted, automatic, looping, and inline, with no native controls or pause button.

Organization labels sit above reference-matched iPhone frames on pale
backgrounds. Exact source hashes,
metadata, output filenames, and poster times are recorded in
`content/sources/womens-wilderness-mobile-media.json`.

`ww-iphone-frame.png` is a transparent decorative overlay extracted from the
owner's `ww-program-preview.png`. It retains that reference's silver rim,
black bezel, camera, normal white `12:37` clock, signal/battery icons, and home
indicator. The reference status bar covers the red recording badges on all
three videos. These normalized device details are decoration, **not capture
timestamps or research evidence**. The website/browser display remains live
through the transparent window; the underlying media files are unchanged.

The reference's turquoise annotation crossings were removed only from the
decorative rim using adjacent clean pixels. No website UI or research result
was redrawn. Frame geometry, source hashes, alpha-mask details, and the minimal
retained status/home strips are documented in
`content/sources/womens-wilderness-video-frames.json`.

### Data-trends synthesis table

- Owner-supplied Webflow image:
  `https://cdn.prod.website-files.com/60beeb75072e337b4bc61933/687800752955607047fa01e6_data-trend.png`.
- Local copy: `public/assets/ww-data-trends.png`, 1007×617, preserved
  byte-for-byte. No table entries, participant counts, or interpretations were
  regenerated. The supplied source itself ends partway through its final row.
- SHA-256:
  `94884cf7759dfbc3413055250fae7a0198a05e730f66e73754425ed9644d2b74`.
- Shown immediately below the color-coded synthesis figure, with a local
  full-size link rather than a runtime dependency on Webflow's CDN.
  Source metadata is in `content/sources/womens-wilderness-data-trends.json`.

### Transparent program-preview phones

- `ww-program-preview-transparent.png` and
  `ww-competitor-preview-transparent.png` are 440×903 RGBA derivatives of the
  corresponding original preview screenshots.
- Only exterior white matte and exterior annotation segments were removed.
  Enclosed website/browser UI, including white areas and existing annotations,
  is preserved pixel-for-pixel. Original reference files are unchanged.
- Source/output hashes, crop geometry, edge-alpha method, white-pixel integrity
  checks, and limitations are archived in
  `content/sources/womens-wilderness-transparent-previews.json`.
  Optional reproduction helper: `tools/prepare_transparent_previews.py`
  (Pillow 13.0.0; not a website/runtime dependency).

### Original / proposed terminology walkthrough

- Owner recording: `ScreenRecording_11-01-2026 16-47-16_1.MP4`.
  The full recording is retained at its original pace, normalized to 30fps
  with audio omitted from the published media.
- Both versions use the same black browser-chrome treatment. “Original”
  describes the unchanged website wording, not unmodified browser chrome.
- The clearly labeled proposed illustration changes homepage
  “PARTNERSHIP & CUSTOM PROGRAMS” to “PARTNERSHIP & CUSTOM COURSES,” plus the
  Adult/Youth menu headings and “All Adult/Youth Programs” submenu labels to
  “Courses.” Existing Courses FAQ labels and other website content remain.
  This is not evidence of a live implementation or follow-up usability test.
- `ww-naming-comparison.webm`, `.mp4`, and `-poster.jpg` include both phones
  and their labels in one 1000×956 canvas. Every frame holds both views at the
  same point in the recording; they cannot drift independently.
- Hardware comes from the unchanged `ww-iphone-frame.png` reference overlay.
  Only its retained status/home display strips are normalized to black.
  The decorative 12:37 status clock is not recording-time evidence.
- Final output hashes, timing, geometry, and working-input hashes are in
  `content/sources/womens-wilderness-naming-comparison.json`.
  Source hash, font URL/hash, per-frame edit tracking, and pixel-conservation
  checks are in `content/sources/womens-wilderness-naming-media.json`.
  Reproduction uses `content/sources/render-womens-wilderness-naming.py`
  for the edited pair and `tools/compose_naming_comparison.py` for the
  single frame-locked comparison. These are offline tools, not runtime scripts.
