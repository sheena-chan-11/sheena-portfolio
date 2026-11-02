# Sheena Chan — portfolio baseline

Static capture of https://sheenachan.webflow.io/, made October 31, 2026.
This preserves the existing design and content before internship/job-application updates.

## Preview

Serve `public/` with a static HTTP server that supports byte ranges for video
seeking. The VM uses BusyBox:

```sh
busybox httpd -f -p 8000 -h "$PWD/public" -c "$PWD/deploy/httpd.conf"
```

The VM preview runs as the `sheena-portfolio` systemd service on port 8000.
Its checkout is `/home/exedev/sheena-portfolio`.
The service definition is tracked in `deploy/sheena-portfolio.service`.
`deploy/httpd.conf` supplies explicit video/font MIME types.

## Verify

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest -v
```

## Scope

Seven pages: home, about, project listing, SARINC, Women's Wilderness, PetPal,
and Step by Step (coming soon).
Images, CSS, JavaScript, and CSS-referenced fonts are copied locally.
The original WebFont loader still loads Google Fonts externally.
Webflow interactions remain in place; this is a baseline, not a framework rewrite.
All original vendor JavaScript is unchanged from commit `320f0ca`. The platform
sticker is hidden using a small CSS rule, without editing the runtime or its
integrity hashes.

## Current portfolio

- Top navigation stays visible while scrolling on every page.
- Homepage side LinkedIn/Email CTAs, bottom contact copy/form, and Contact
  navigation links are removed. About Me now includes direct email and
  LinkedIn links beneath the biography.
- Home, Projects, and About's Latest Work list show Step by Step, Women's
  Wilderness, and Small Angel Rescue, in that order.
- Step by Step's thumbnail has no permanent text label. All three cards share
  the same padded purple hover/keyboard-focus overlay with wrapping text
  (22px title, 18px description, 16px project type; 21/17/15px on narrow phones).
- PetPal is unlisted, not access-restricted: `/project/petpal/` remains available.
  Its original YouTube embed URL is restored instead of the captured `.bin`.
- `/project/step-by-step/` is a coming-soon page; it makes no claims about
  completed research or outcomes. Stock-image provenance is in `IMAGE_CREDITS.md`.
- Women's Wilderness uses the owner's revised case-study copy, archived at
  `content/sources/womens-wilderness-case-study.pdf`. Relevant original research
  screenshots are reused/cropped, with recommendations explicitly labeled as
  proposals rather than implemented results. The supplied homepage recording is
  embedded in a Chrome-style browser frame below Desk Research, autoplaying
  muted in a loop without a
  visible caption, playback button, or timeline. Unprovided draft
  GIF/video notes are not published as content; remaining media is tracked in
  GitHub issue #8.
- Competitive-analysis point 1 includes the supplied Women's Wilderness
  program-navigation and Backcountry Beauties trips-list recordings; point 2
  includes the Backcountry Beauties waitlist flow. They autoplay muted in
  reference-matched silver-rimmed iPhone frames on pale backgrounds, labeled by
  organization, side by side on desktop and stacked on mobile. Reference device
  chrome covers the red recording badges without changing the media files or
  website interactions. There are no playback buttons or duration displays.
- Women's Wilderness interview topics link directly to their corresponding
  findings and recommendations, with an explanatory note and smooth scrolling
  that clears the sticky header. URL fragments and heading focus are preserved;
  reduced-motion users get an immediate jump. The Background summary focuses on
  opportunities rather than repeating the overview's research-methods list.
- “User Interview and Analysis” includes a parenthesized, italic navigation
  note. The color-coded synthesis and data-trends table share one evidence
  panel; the table is capped at 520px wide. The first caption explains how the
  coding identified participants with similar thoughts, actions, or feelings.
  Both images open full-size.
- The two competitive program-preview screenshots use exterior-transparent
  phone derivatives. White website UI inside the phones is retained; original
  green annotation rectangles are retained in full, including their sides
  outside the hardware. Reference screenshots remain unchanged. Mask geometry
  and integrity checks are in
  `content/sources/womens-wilderness-transparent-previews.json`.
- The first finding uses the owner's additional homepage/navigation recording
  as an “Original” / “Proposed” terminology comparison. Both framed phones and
  labels are baked into one video, so playback, seeking, buffering, and looping
  cannot drift. Both views use black browser chrome; prominent yellow
  rectangles identify only the updated “Courses” words in the proposed view,
  not existing FAQ labels. WebM is offered before MP4, with a full-size
  comparison link for closer inspection.
- Finding 2 pairs the owner's original desktop screenshot with a proposed
  filter animation, each inside a browser frame showing
  `womenswilderness.org/programs/`. Yellow rectangles outline “All Adult,”
  “Hiking,” and the existing “Adult” filter label with a consistent color and
  outline style. The already-selected Adult label and All Adult row are
  highlighted from the first frame. Adult and Hiking use the source page's
  Windsor Roman 500, 24px typography and each has an × close affordance inside
  its highlight. The proposal removes “(Remove Filter)” while the Original
  screenshot stays untouched; no selection checkmark or plus sign appears
  between filters. The pointer
  selects Hiking, the film event disappears, and the original adult hiking
  event reflows into the first results position. Browser controls/profile and
  desktop Dock from the source capture are cropped out. Source pixels, event
  details, animation timing, and verification are recorded in
  `content/sources/womens-wilderness-filter-animation.json`.

Intentional preview safeguards:

- Production Google Analytics is removed.
- Contact forms have been removed entirely; contacting Sheena uses the direct
  email and LinkedIn links on About Me instead.
- One inaccessible Webflow stock placeholder (HTTP 403 at capture time) is
  replaced by a neutral SVG; details are in `capture-manifest.json`.
- No domain or DNS changes have been made. `sheenachan.com` can be connected
  after deployment is chosen.

## Capture

`capture.py` records page/asset provenance in `capture-manifest.json`.
It overwrites the baseline, so do not rerun it over later design changes.
Reproduction dependencies are pinned in `requirements.txt`.

Project tasks, decisions, and changes are to be tracked through GitHub issues,
commits, and pull requests in `sheena-chan-11/sheena-portfolio`.
