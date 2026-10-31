"""Remove platform promotion while retaining the local interaction runtime."""
import base64
from hashlib import sha384
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).parent / "public"


def remove_branding(root=ROOT):
    for script in (root / "assets").glob("*.js"):
        text = script.read_text()
        # Disable the platform's branding and hosted-editor modules entirely.
        # Their public module names stay available so runtime imports still work.
        for start, end, name in (
            ('9461:function(e,t,n){', '322:function(e,t,n){', 'brand'),
            ('322:function(e,t,n){', '2338:function(e,t,n){', 'edit'),
        ):
            if start not in text or end not in text:
                continue
            begin = text.index(start)
            finish = text.index(end, begin)
            replacement = (
                start + '"use strict";n(3949).define("' + name
                + '",e.exports=function(){return {}})},'
            )
            text = text[:begin] + replacement + text[finish:]
        if text != script.read_text():
            script.write_text(text)

    for page in root.rglob("*.html"):
        soup = BeautifulSoup(page.read_text(), "html.parser")
        for attr in ("data-wf-domain", "data-wf-status"):
            soup.html.attrs.pop(attr, None)
        for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
            if "webflow" in str(comment).lower():
                comment.extract()
        for tag in soup.select('meta[name="generator"], .w-webflow-badge'):
            tag.decompose()
        for link in soup.select('link[rel="preconnect"]'):
            if "website-files.com" in link.get("href", ""):
                link.decompose()
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if src.startswith("/assets/") and script.get("integrity"):
                content = (root / urlsplit(src).path.lstrip("/")).read_bytes()
                script["integrity"] = "sha384-" + base64.b64encode(sha384(content).digest()).decode()
        page.write_text(str(soup))


if __name__ == "__main__":
    remove_branding()
