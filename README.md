# Sheena Chan — portfolio baseline

Static capture of https://sheenachan.webflow.io/, made October 31, 2026.
This preserves the existing design and content before internship/job-application updates.

## Preview

Serve `public/` with any static HTTP server:

```sh
python3 -m http.server 8000 --directory public
```

The VM preview runs as the `sheena-portfolio` systemd service on port 8000.

## Scope

Six pages: home, about, project listing, SARINC, Women's Wilderness, and PetPal.
Images, CSS, JavaScript, and CSS-referenced fonts are copied locally.
The original WebFont loader still loads Google Fonts externally.
Webflow interactions remain in place; this is a baseline, not a framework rewrite.

Intentional preview safeguards:

- Production Google Analytics is removed.
- Contact forms display an explicit preview-only message instead of submitting
  to the production Webflow service. Email and LinkedIn links remain available.
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
