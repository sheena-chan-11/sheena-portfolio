"""Run with .venv/bin/python -m unittest -v (no running server required)."""
from pathlib import Path
from urllib.parse import urlsplit
import json
import base64
import hashlib
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent / "public"


class BaselineTests(unittest.TestCase):
    def test_all_seven_pages_available(self):
        self.assertEqual(len(list(ROOT.rglob("*.html"))), 7)

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

    def test_sticker_is_hidden_with_css_only(self):
        for page in ROOT.rglob("*.html"):
            soup = BeautifulSoup(page.read_text(), "html.parser")
            style = soup.select_one("#portfolio-branding")
            self.assertIsNotNone(style, str(page))
            self.assertIn(".w-webflow-badge", style.get_text())
            self.assertIn("display: none !important", style.get_text())

    def test_homepage_side_ctas_removed_but_contact_kept(self):
        soup = BeautifulSoup((ROOT / "index.html").read_text(), "html.parser")
        self.assertFalse(soup.select(".social-block, .social-link"))
        self.assertIsNotNone(soup.select_one("#contact"))
        self.assertIsNotNone(soup.select_one("form"))

    def test_petpal_unlisted_but_details_remain(self):
        for name in ("index.html", "latestprojects/index.html", "aboutme/index.html"):
            soup = BeautifulSoup((ROOT / name).read_text(), "html.parser")
            self.assertFalse(soup.select('a.project-img[href="/project/petpal"]'))
        soup = BeautifulSoup((ROOT / "project/petpal/index.html").read_text(), "html.parser")
        self.assertIn("Petpal", soup.get_text())
        self.assertEqual(soup.select_one("iframe")["src"], "https://www.youtube.com/embed/n8pjDvbowCI")

    def test_new_project_available_in_all_lists(self):
        for name in ("index.html", "latestprojects/index.html", "aboutme/index.html"):
            soup = BeautifulSoup((ROOT / name).read_text(), "html.parser")
            links = soup.select('a.project-img[href="/project/step-by-step"]')
            self.assertEqual(len(links), 1)
            self.assertTrue(links[0].select_one("img")["alt"])
            self.assertNotIn("height", links[0].select_one("img").attrs)
            self.assertIn("Step by Step", links[0].get_text())
        soup = BeautifulSoup((ROOT / "project/step-by-step/index.html").read_text(), "html.parser")
        self.assertEqual(soup.h1.get_text(), "Step by Step")
        for phrase in ("coming soon", "U.S. college students", "quick movement breaks"):
            self.assertIn(phrase, soup.get_text())
        self.assertEqual(soup.select_one(".step-back")["href"], "/latestprojects")

    def test_requested_project_order(self):
        expected = ["/project/step-by-step", "/project/womens-wilderness", "/project/sarinc"]
        for name in ("index.html", "latestprojects/index.html", "aboutme/index.html"):
            soup = BeautifulSoup((ROOT / name).read_text(), "html.parser")
            self.assertEqual([a["href"] for a in soup.select("a.project-img")], expected)

    def test_script_integrity_still_matches(self):
        for page in ROOT.rglob("*.html"):
            soup = BeautifulSoup(page.read_text(), "html.parser")
            for script in soup.select("script[src][integrity]"):
                content = (ROOT / urlsplit(script["src"]).path.lstrip("/")).read_bytes()
                algorithm = script["integrity"].split("-", 1)[0]
                expected = algorithm + "-" + base64.b64encode(hashlib.new(algorithm, content).digest()).decode()
                self.assertEqual(script["integrity"], expected)

    def test_original_interaction_runtime_is_untouched(self):
        # The known-working runtime from the owner's selected commit 320f0ca.
        content = (ROOT / "assets/29133ca8abc58af805e3.js").read_bytes()
        self.assertEqual(
            hashlib.sha256(content).hexdigest(),
            "75b351485c3eaf585a3ad997c032aad52d0775f8189c9638a0ad93401933bec8",
        )
