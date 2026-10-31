"""Remove platform promotion while retaining the local interaction runtime."""
import base64
from hashlib import sha256, sha384
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).parent / "public"


def remove_branding(root=ROOT):
    for page in root.rglob("*.html"):
        soup = BeautifulSoup(page.read_text(), "html.parser")
        for attr in ("data-wf-domain", "data-wf-status"):
            soup.html.attrs.pop(attr, None)
        for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
            if "webflow" in str(comment).lower():
                comment.extract()
        for tag in soup.select('meta[name="generator"], .w-webflow-badge'):
            tag.decompose()
        # Never gate portfolio access on a load animation or third-party font.
        for tag in soup.select(".loading-page"):
            tag.decompose()
        if not soup.select_one("#portfolio-availability"):
            style = soup.new_tag("style", id="portfolio-availability")
            style.string = ".page-wrapper { opacity: 1 !important; }"
            soup.head.append(style)
        for link in soup.select('link[rel="preconnect"]'):
            if "website-files.com" in link.get("href", ""):
                link.decompose()
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if src.startswith("/assets/") and script.get("integrity"):
                content = (root / urlsplit(src).path.lstrip("/")).read_bytes()
                # A changed script must not reuse an old browser cache entry.
                script["src"] = urlsplit(src).path + "?v=" + sha256(content).hexdigest()[:16]
                script["integrity"] = "sha384-" + base64.b64encode(sha384(content).digest()).decode()
        page.write_text(str(soup))


if __name__ == "__main__":
    remove_branding()
