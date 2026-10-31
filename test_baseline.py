"""Run with .venv/bin/python -m unittest -v (no running server required)."""
from pathlib import Path
from urllib.parse import urlsplit
import base64
from hashlib import sha384
import json
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent / "public"


class BaselineTests(unittest.TestCase):
    def test_all_six_pages_captured(self):
        self.assertEqual(len(list(ROOT.rglob("*.html"))), 6)

    def test_local_links_and_assets_exist(self):
        for page in ROOT.rglob("*.html"):
            soup = BeautifulSoup(page.read_text(), "html.parser")
            for tag in soup.find_all(True):
                urls = [tag.get("src", ""), tag.get("href", ""), tag.get("poster", "")]
                urls += [item.strip().split()[0] for item in tag.get("srcset", "").split(",") if item.strip()]
                if tag.name == "script" and tag.get("type") == "application/json":
                    urls += [item["url"] for item in json.loads(tag.string or "{}").get("items", []) if "url" in item]
                for url in urls:
                    if url.startswith("/") and not url.startswith("//"):
                        local = ROOT / urlsplit(url).path.lstrip("/")
                        self.assertTrue(local.is_file() or (local / "index.html").is_file(), f"{page}: {url}")

    def test_no_production_analytics_or_form_submission(self):
        for page in ROOT.rglob("*.html"):
            text = page.read_text()
            self.assertNotIn("googletagmanager.com", text)
            self.assertIn("event.preventDefault()", text)
            self.assertIn("Preview only:", text)

    def test_no_unresolved_capture_errors(self):
        manifest = json.loads((ROOT.parent / "capture-manifest.json").read_text())
        self.assertFalse([item for item in manifest["failures"] if "error" in item])

    def test_no_platform_branding_on_any_page(self):
        for page in ROOT.rglob("*.html"):
            text = page.read_text()
            soup = BeautifulSoup(text, "html.parser")
            self.assertNotIn("webflow", text.lower())
            self.assertFalse(soup.select('.w-webflow-badge, meta[name="generator"]'))
            self.assertNotIn("data-wf-status", soup.html.attrs)
            self.assertNotIn("data-wf-domain", soup.html.attrs)
        for script in (ROOT / "assets").glob("*.js"):
            text = script.read_text()
            self.assertNotIn("Made in Webflow", text)
            self.assertNotIn("utm_campaign=brandjs", text)
            self.assertNotIn("editor-api.webflow.com", text)

    def test_script_integrity_matches_local_files(self):
        for page in ROOT.rglob("*.html"):
            soup = BeautifulSoup(page.read_text(), "html.parser")
            for tag in soup.select("script[src][integrity]"):
                content = (ROOT / urlsplit(tag["src"]).path.lstrip("/")).read_bytes()
                expected = "sha384-" + base64.b64encode(sha384(content).digest()).decode()
                self.assertEqual(tag["integrity"], expected)
