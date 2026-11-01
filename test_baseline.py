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

    def test_no_production_analytics_or_contact_forms(self):
        for page in ROOT.rglob("*.html"):
            text = page.read_text()
            self.assertNotIn("googletagmanager.com", text)
            soup = BeautifulSoup(text, "html.parser")
            self.assertFalse(soup.select("form, input, textarea"))

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

    def test_homepage_contact_section_and_side_ctas_removed(self):
        soup = BeautifulSoup((ROOT / "index.html").read_text(), "html.parser")
        self.assertFalse(soup.select(".social-block, .social-link"))
        self.assertIsNone(soup.select_one("#contact"))
        self.assertNotIn("Got a project in mind?", soup.get_text())
        self.assertNotIn("Drop me a line!", soup.get_text())
        self.assertNotIn("Let's make something awesome together.", soup.get_text())
        self.assertIsNotNone(soup.select_one("footer"))

    def test_no_contact_navigation_or_dead_contact_links(self):
        for page in ROOT.rglob("*.html"):
            soup = BeautifulSoup(page.read_text(), "html.parser")
            self.assertEqual(
                [a.get_text(" ", strip=True) for a in soup.select(".nav-menu a")],
                ["Home", "About Me", "Projects"],
            )
            self.assertFalse(soup.select('a[href="/#contact"], a[href="#contact"], a[href="/contact"]'))

    def test_about_me_contact_links(self):
        soup = BeautifulSoup((ROOT / "aboutme/index.html").read_text(), "html.parser")
        links = soup.select_one(".column-paragraph .about-contact-links")
        self.assertIsNotNone(links)
        email = links.select_one('a[href="mailto:scyl182011@gmail.com"]')
        self.assertEqual(email.get_text(), "scyl182011@gmail.com")
        linkedin = links.select_one('a[href="https://www.linkedin.com/in/sheenachan11"]')
        self.assertIsNotNone(linkedin)
        self.assertEqual(linkedin["target"], "_blank")
        self.assertIn("noopener", linkedin["rel"])

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

    def test_project_overlay_content_and_stylesheet_version(self):
        version = hashlib.sha256((ROOT / "assets/step-by-step.css").read_bytes()).hexdigest()[:12]
        for name in ("index.html", "latestprojects/index.html", "aboutme/index.html"):
            soup = BeautifulSoup((ROOT / name).read_text(), "html.parser")
            self.assertFalse(soup.select(".step-card-label"))
            self.assertIsNotNone(soup.select_one(
                f'link[href="/assets/step-by-step.css?v={version}"]'
            ))
            for card in soup.select("a.project-img"):
                overlay = card.select_one(".project-img-overlay")
                for selector in (".project-title", ".product-description", ".project-type"):
                    self.assertTrue(overlay.select_one(selector).get_text(strip=True))
                self.assertFalse(card.select(".step-card-label"))
        soup = BeautifulSoup((ROOT / "project/step-by-step/index.html").read_text(), "html.parser")
        self.assertIsNotNone(soup.select_one(f'link[href="/assets/step-by-step.css?v={version}"]'))

    def test_womens_wilderness_revised_case_study(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        text = soup.get_text(" ", strip=True)
        for phrase in (
            "girls, women, and LGBTQ+ people in Colorado since 1998",
            "collaborated with four other UX researchers",
            "User Interviews with six potential participants",
            "Clarify program labels",
            "Improve program filtering",
            "Communicate registration availability clearly",
            "searching for a specific program and event",
            "price, date, and location",
            "6 potential participants",
            "FAQ – Adult Courses",
            "consistent terminology",
            "activity, age, and program-type filters",
            "cancellation waitlist",
            "completed events or passed deadlines",
            "notifications about future dates",
            "Client response",
            "Kriste + Women’s Wilderness",
            "We did not conduct follow-up usability testing",
        ):
            self.assertIn(phrase, text)
        self.assertEqual(len(soup.select(".ww-comparison > li")), 3)
        self.assertEqual(len(soup.select("#challenge .ww-copy > ol > li")), 3)
        self.assertEqual(len(soup.select(".ww-copy h4")), 3)
        self.assertEqual(soup.select_one("#challenge h2").get_text(strip=True), "Limitations")
        self.assertIsNotNone(soup.h1)
        for obsolete in ("85%", "Age Range:", "Cost Clarity", "Number of Participants", "Involvement - Volunteering"):
            self.assertNotIn(obsolete, text)
        self.assertNotIn("***", text)
        self.assertNotIn("Graphics/ video??", text)
        self.assertNotIn("GIF to", text)
        self.assertTrue((ROOT.parent / "content/sources/womens-wilderness-case-study.pdf").is_file())

    def test_womens_wilderness_evidence_and_links(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        version = hashlib.sha256((ROOT / "assets/womens-wilderness.css").read_bytes()).hexdigest()[:12]
        self.assertIsNotNone(soup.select_one(f'link[href="/assets/womens-wilderness.css?v={version}"]'))
        self.assertEqual(len(soup.select(".ww-evidence")), 5)
        for figure in soup.select(".ww-evidence"):
            self.assertTrue(figure.figcaption.get_text(strip=True))
            for image in figure.select("img"):
                self.assertTrue(image["alt"])
                self.assertIn("width", image.attrs)
                self.assertIn("height", image.attrs)
        captions = " ".join(f.get_text() for f in soup.select(".ww-evidence figcaption"))
        self.assertIn("not a tested outcome", captions)
        self.assertIn("not evidence of implementation", captions)
        for link in soup.select('a[target="_blank"]'):
            self.assertIn("noopener", link.get("rel", []))
        visit = next(a for a in soup.select("a") if "Visit Website" in a.get_text())
        self.assertEqual(visit["href"], "https://womenswilderness.org/")
        previous = next(a for a in soup.select(".project-page a") if a.get_text(strip=True) == "Prev Project")
        self.assertEqual(previous["href"], "/project/step-by-step")

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
