"""Regression checks for crawler-readable link previews."""
from pathlib import Path
import hashlib
import unittest
from bs4 import BeautifulSoup

PUBLIC = Path(__file__).parent / "public"


class LinkPreviewTests(unittest.TestCase):
    def test_every_page_has_complete_absolute_preview_metadata(self):
        image = PUBLIC / "assets/sheena-chan-social-preview.jpg"
        digest = hashlib.sha256(image.read_bytes()).hexdigest()[:12]
        image_url = "https://sheenachan.com/assets/" + image.name + "?v=" + digest
        for page in PUBLIC.rglob("*.html"):
            with self.subTest(page=str(page)):
                soup = BeautifulSoup(page.read_text(), "html.parser")
                relative = page.relative_to(PUBLIC).as_posix()
                url = "https://sheenachan.com" + (
                    "/" if relative == "index.html" else "/" + relative.removesuffix("index.html")
                )
                self.assertEqual(len(soup.select("title")), 1)
                self.assertIn("Sheena Chan", soup.title.get_text())
                for selector in (
                    'meta[name="description"]', 'meta[property="og:description"]',
                    'meta[name="twitter:description"]',
                ):
                    self.assertEqual(len(soup.select(selector)), 1)
                    self.assertGreater(len(soup.select_one(selector)["content"]), 25)
                for selector in ('meta[property="og:title"]', 'meta[name="twitter:title"]'):
                    self.assertEqual(soup.select_one(selector)["content"], soup.title.get_text())
                for selector in ('meta[property="og:image"]', 'meta[property="og:image:secure_url"]',
                                 'meta[name="twitter:image"]'):
                    self.assertEqual(soup.select_one(selector)["content"], image_url)
                self.assertEqual(soup.select_one('meta[property="og:image:width"]')["content"], "1200")
                self.assertEqual(soup.select_one('meta[property="og:image:height"]')["content"], "630")
                self.assertEqual(soup.select_one('meta[property="og:image:type"]')["content"], "image/jpeg")
                self.assertEqual(soup.select_one('meta[name="twitter:card"]')["content"], "summary_large_image")
                self.assertEqual(soup.select_one('meta[property="og:url"]')["content"], url)
                self.assertEqual(soup.select_one('link[rel="canonical"]')["href"], url)
                self.assertNotIn("A Brand New Domain!", soup.head.get_text())


if __name__ == "__main__":
    unittest.main()
