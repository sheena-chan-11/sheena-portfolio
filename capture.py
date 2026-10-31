"""Capture the owner's public Webflow site without changing its design."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import json
import re
import requests
from bs4 import BeautifulSoup

ORIGIN = "https://sheenachan.webflow.io"
ROOT = Path(__file__).parent / "public"
ROOT.mkdir(exist_ok=True)
session = requests.Session()
assets = {}
failures = []
pages = {}


def fetch(url):
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response


def asset(url):
    url = url.split("#")[0]
    if url not in assets:
        suffix = Path(unquote(urlsplit(url).path)).suffix
        if not re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", suffix):
            suffix = ".bin"
        assets[url] = "/assets/" + sha256(url.encode()).hexdigest()[:20] + suffix
    return assets[url]


pending = deque(["/"])
while pending:
    path = pending.popleft()
    if path in pages:
        continue
    response = fetch(ORIGIN + path)
    soup = BeautifulSoup(response.text, "html.parser")
    pages[path] = soup
    for tag in soup.find_all("a", href=True):
        url = urlsplit(urljoin(ORIGIN + path, tag["href"]))
        if url.netloc == urlsplit(ORIGIN).netloc:
            target = url.path.rstrip("/") or "/"
            if not Path(target).suffix:
                if target not in pages and target not in pending:
                    pending.append(target)
                tag["href"] = target + (("#" + url.fragment) if url.fragment else "")
    print("Page:", path, flush=True)

css_pattern = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)


def localize_css(text, base):
    def replace(match):
        value = match.group(2)
        if value.startswith(("data:", "#")):
            return match.group(0)
        return 'url("' + asset(urljoin(base, value)) + '")'
    return css_pattern.sub(replace, text)


for path, soup in pages.items():
    # Analytics belongs to the live site, not development previews.
    for tag in list(soup.find_all("script")):
        if "googletagmanager" in tag.get("src", "") or "gtag(" in tag.get_text():
            tag.decompose()
    for tag in soup.find_all(True):
        if tag.name == "a" and tag.get("href", "").startswith("https://cdn.prod.website-files.com/"):
            tag["href"] = asset(tag["href"])
        if tag.name == "script" and tag.get("type") == "application/json":
            # Webflow lightboxes keep full-resolution image URLs in JSON.
            data = json.loads(tag.string or "{}")
            for item in data.get("items", []):
                for key in ("url", "thumbnailUrl"):
                    if item.get(key):
                        item[key] = asset(urljoin(ORIGIN + path, item[key]))
            tag.string = json.dumps(data)
        for attr in ("src", "poster"):
            if tag.get(attr) and not tag[attr].startswith("data:"):
                tag[attr] = asset(urljoin(ORIGIN + path, tag[attr]))
        if tag.name == "link" and tag.get("href"):
            if any(x in tag.get("rel", []) for x in ("stylesheet", "shortcut", "icon", "apple-touch-icon")):
                tag["href"] = asset(urljoin(ORIGIN + path, tag["href"]))
                # CSS font URLs are localized, changing its original SRI hash.
                tag.attrs.pop("integrity", None)
        if tag.get("srcset"):
            tag["srcset"] = ", ".join(
                asset(urljoin(ORIGIN + path, parts[0])) + (" " + " ".join(parts[1:]) if len(parts) > 1 else "")
                for item in tag["srcset"].split(",") if (parts := item.strip().split())
            )
        if tag.get("style"):
            tag["style"] = localize_css(tag["style"], ORIGIN + path)
        if tag.name == "style":
            tag.string = localize_css(tag.get_text(), ORIGIN + path)
    # Preserve the form UI, but never send preview submissions to production.
    script = soup.new_tag("script")
    script.string = """
document.addEventListener('submit', function(event) {
  if (!event.target.closest('.w-form')) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  const form = event.target.closest('.w-form');
  const error = form.querySelector('.w-form-fail');
  if (error) {
    error.textContent = 'Preview only: this form is not connected. Please email scyl182011@gmail.com.';
    error.style.display = 'block';
    error.setAttribute('role', 'alert');
  }
}, true);
"""
    soup.body.append(script)
    output = ROOT / ("index.html" if path == "/" else path.lstrip("/") + "/index.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(str(soup))

completed = set()
while batch := [(url, name) for url, name in assets.items() if url not in completed]:
    def download(item):
        url, name = item
        try:
            response = fetch(url)
            if "text/css" in response.headers.get("Content-Type", "") or urlsplit(url).path.endswith(".css"):
                content = localize_css(response.text, url).encode()
            else:
                content = response.content
            output = ROOT / name.lstrip("/")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
            return None
        except Exception as exc:
            if url.endswith("/plugins/Basic/assets/placeholder.60f9b1840c.svg"):
                output = ROOT / name.lstrip("/")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="150"><rect width="150" height="150" fill="#eee"/></svg>')
                return {"url": url, "fallback": "Neutral placeholder; original Webflow placeholder returns HTTP 403."}
            return {"url": url, "error": str(exc)}
    with ThreadPoolExecutor(max_workers=12) as pool:
        failures.extend(error for error in pool.map(download, batch) if error)
    completed.update(url for url, _ in batch)
    print("Assets:", len(completed), flush=True)

(ROOT.parent / "capture-manifest.json").write_text(json.dumps({
    "source": ORIGIN,
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "pages": list(pages),
    "assets": assets,
    "failures": failures,
}, indent=2))
if any("error" in failure for failure in failures):
    raise SystemExit("Downloads failed; see capture-manifest.json")
