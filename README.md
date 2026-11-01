# Sheena Chan — portfolio baseline

Static capture of https://sheenachan.webflow.io/, made October 31, 2026.
This preserves the existing design and content before internship/job-application updates.

## Preview

Serve `public/` with any static HTTP server:

```sh
python3 -m http.server 8000 --directory public
```

The VM preview runs as the `sheena-portfolio` systemd service on port 8000.
Its checkout is `/home/exedev/sheena-portfolio`.

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

- Homepage side LinkedIn/Email CTAs, bottom contact copy/form, and Contact
  navigation links are removed. About Me now includes direct email and
  LinkedIn links beneath the biography.
- Home, Projects, and About's Latest Work list show Step by Step, Women's
  Wilderness, and Small Angel Rescue, in that order.
- Step by Step's thumbnail has no permanent text label. All three cards share
  the same padded purple hover/keyboard-focus overlay with wrapping text.
- PetPal is unlisted, not access-restricted: `/project/petpal/` remains available.
  Its original YouTube embed URL is restored instead of the captured `.bin`.
- `/project/step-by-step/` is a coming-soon page; it makes no claims about
  completed research or outcomes. Stock-image provenance is in `IMAGE_CREDITS.md`.
- Women's Wilderness uses the owner's revised case-study copy, archived at
  `content/sources/womens-wilderness-case-study.pdf`. Relevant original research
  screenshots are reused/cropped, with recommendations explicitly labeled as
  proposals rather than implemented results. Draft GIF/video notes are not
  published as content; those media files were not included in the PDF.

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
