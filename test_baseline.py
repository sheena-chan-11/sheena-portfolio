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

    def test_sticky_navigation_stylesheet_on_all_pages(self):
        css = ROOT / "assets/portfolio.css"
        version = hashlib.sha256(css.read_bytes()).hexdigest()[:12]
        self.assertIn("position: sticky", css.read_text())
        for page in ROOT.rglob("*.html"):
            soup = BeautifulSoup(page.read_text(), "html.parser")
            self.assertIsNotNone(soup.select_one(".navbar.w-nav"))
            self.assertIsNotNone(soup.select_one(f'link[href="/assets/portfolio.css?v={version}"]'))

    def test_about_me_contact_links(self):
        soup = BeautifulSoup((ROOT / "aboutme/index.html").read_text(), "html.parser")
        links = soup.select_one(".column-paragraph .about-contact-links")
        self.assertIsNotNone(links)
        email = links.select_one('a[href="mailto:scyl182011@gmail.com"]')
        self.assertEqual(email.get_text(), "Email")
        self.assertNotIn("scyl182011@gmail.com", links.get_text())
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

    def test_small_angel_rescue_case_study_graphics_and_original_homepage(self):
        page = ROOT / "project/sarinc/index.html"
        soup = BeautifulSoup(page.read_text(), "html.parser")
        text = soup.get_text(" ", strip=True)
        for phrase in (
            "Maryland area",
            "Quantitative and qualitative research",
            "In my previous job, I used Google Analytics(GA) to pull site reports. I thought I could do the same for Small Angel Rescue to monitor user behavior, so I set it up on their site and started collecting and analyzing user data.",
            "I’ve also interviewed the volunteers",
            "After receiving all the responses, I gathered and analyzed the data through affinity mapping",
            "It is a great technique for stakeholders to digest complex data in an easy-to-understand overview.",
            "Original Small Angels Rescue homepage.",
            "The responses gave me background details of our users, and I created Marissa to represent the user group.",
            "I've also uncovered the user pain point:",
            "As I was new to the animal rescue platform, I conducted a competitive analysis",
            "After I had some basic understanding of the animal rescue platforms, I brainstormed different potential solutions to address the user pain points",
            "How might we make it easier for first-time pet owners",
            "more than 68% of visitors browsed on mobile",
            "pet-care page views had doubled",
            "engagement time was 5% longer",
            "transparent desktop navigation",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("How we worked together", text)
        infographic = soup.select_one('img[src="/assets/82f4e85c35d74c5103d7.png"]')
        summary_figure = infographic.find_parent("figure")
        self.assertEqual(
            summary_figure.figcaption.get_text(strip=True),
            "It is a great technique for stakeholders to digest complex data in an easy-to-understand overview.",
        )
        analysis = soup.find("h5", string="Exploring solutions")
        first = analysis.find_next_sibling("p")
        table = first.find_next_sibling("figure").select_one("img")
        self.assertEqual(table["src"], "/assets/4bb2262b74a8b8255b70.png")
        self.assertIn("competitive analysis table", table["alt"].lower())
        self.assertIn("sarinc-competitive-analysis", table.find_parent("figure")["class"])
        self.assertEqual(table.find_parent("a")["href"], "/assets/4fd5c673d0a40210130b.png")
        self.assertIn("After I had some basic understanding", table.find_parent("figure").find_next_sibling("p").get_text())
        hmw = soup.select_one("p.sarinc-hmw")
        self.assertIn("How might we make it easier for first-time pet owners", hmw.get_text())
        usability = soup.find("h5", string="Usability testing")
        self.assertIn("more than 68% of visitors browsed on mobile", usability.find_previous_sibling("p").get_text())
        self.assertEqual(usability.find_next_sibling().name, "ul")
        showcase = soup.select_one(".sarinc-device-showcase")
        self.assertEqual(showcase.find_previous_sibling("p").get_text().strip().split(".")[0], "The site was managed by stakeholders who were unfamiliar with WordPress")
        self.assertIn("Scroll or swipe", showcase.select_one(".sarinc-device-instruction").get_text())
        self.assertEqual(showcase.select_one(".sarinc-desktop-frame .sarinc-browser-address").get_text(strip=True), "www.smallangelsrescue.org")
        for device, width, height in (("desktop", 475, 1144), ("tablet", 488, 1238), ("mobile", 129, 1376)):
            screen = showcase.select_one(f".sarinc-device-{device} .sarinc-device-screen")
            self.assertEqual(screen.get("role"), "region")
            self.assertEqual(screen.get("tabindex"), "0")
            self.assertIn("scroll", screen.get("aria-label"))
            image = screen.select_one("img")
            self.assertEqual(image["src"], f"/assets/sarinc-redesign-{device}.png")
            self.assertTrue(image.get("alt"))
            self.assertEqual((ROOT / image["src"].lstrip("/")).read_bytes()[16:24], width.to_bytes(4, "big") + height.to_bytes(4, "big"))
            self.assertIn("Scroll inside", showcase.select_one(f".sarinc-device-{device} .sarinc-scroll-hint").get_text())
        homepage = soup.select_one(".sarinc-browser-figure")
        self.assertIsNotNone(homepage)
        self.assertEqual(homepage.select_one(".sarinc-browser-address").get_text(strip=True), "www.smallangelsrescue.org")
        image_url = homepage.select_one("img")["src"]
        self.assertEqual(urlsplit(image_url).path, "/assets/sarinc-original-homepage-window.png")
        self.assertEqual(homepage.figcaption.get_text(strip=True), "Original Small Angels Rescue homepage.")
        self.assertEqual(homepage.figcaption["class"], ["sarinc-centered-caption"])
        image = ROOT / "assets/sarinc-original-homepage-window.png"
        self.assertEqual(image.read_bytes()[16:24], (2080).to_bytes(4, "big") + (1380).to_bytes(4, "big"))
        self.assertIn("?v=" + hashlib.sha256(image.read_bytes()).hexdigest()[:12], image_url)
        provenance = json.loads((ROOT.parent / "content/sources/sarinc-original-homepage.json").read_text())
        self.assertEqual(provenance["archive_timestamp_utc"], "2020-02-14T11:30:09Z")
        self.assertEqual(provenance["asset_sha256"], hashlib.sha256(image.read_bytes()).hexdigest())
        source = ROOT.parent / provenance["reference_source_copy"]
        self.assertEqual(provenance["reference_source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        capture = ROOT.parent / provenance["rendered_screenshot"]
        self.assertEqual(provenance["rendered_screenshot_sha256"], hashlib.sha256(capture.read_bytes()).hexdigest())
        css = ROOT / "assets/sarinc.css"
        version = hashlib.sha256(css.read_bytes()).hexdigest()[:12]
        self.assertIsNotNone(soup.select_one(f'link[href="/assets/sarinc.css?v={version}"]'))
        self.assertIn("height: auto", css.read_text())
        self.assertIn("max-width: 640px", css.read_text())
        self.assertIn("figure.sarinc-competitive-analysis", css.read_text())
        self.assertIn("border-left: 3px solid #4830e6", css.read_text())
        self.assertIn("overflow-y: auto", css.read_text())
        self.assertIn("/assets/ww-iphone-frame.png?v=670717c1ac7d", css.read_text())

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
            "Colorado nonprofit organization",
            "girls, women, and LGBTQ+ people find their voice in the outdoors since 1998",
            "collaborated with four other UX researchers",
            "Our research highlighted three opportunities to improve program discovery and registration:",
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
            if "ww-program-previews" in figure.get("class", []):
                self.assertIsNone(figure.figcaption)
                self.assertEqual(len(figure.select("img")), 2)
            else:
                self.assertTrue(figure.figcaption.get_text(strip=True))
            for image in figure.select("img"):
                if image.find_parent(attrs={"aria-hidden": "true"}):
                    continue
                self.assertTrue(image["alt"])
                self.assertIn("width", image.attrs)
                self.assertIn("height", image.attrs)
        captions = " ".join(f.get_text() for f in soup.select(".ww-evidence figcaption"))
        self.assertIsNotNone(soup.select_one(".ww-filter-comparison .ww-filter-proposed"))
        self.assertNotIn("This is a recommendation concept, not evidence of implementation.", captions)
        for link in soup.select('a[target="_blank"]'):
            self.assertIn("noopener", link.get("rel", []))
        visit = next(a for a in soup.select("a") if "Visit Website" in a.get_text())
        self.assertEqual(visit["href"], "https://womenswilderness.org/")
        previous = next(a for a in soup.select(".project-page a") if a.get_text(strip=True) == "Prev Project")
        self.assertEqual(previous["href"], "/project/step-by-step")

    def test_womens_wilderness_registration_screens_are_stacked_at_matching_size(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        figure = soup.select_one(".ww-registration-comparison")
        self.assertIsNotNone(figure)
        screens = figure.select(".ww-registration-screens > .ww-registration-screen")
        self.assertEqual(len(screens), 2)
        self.assertEqual(
            [screen.select_one(".ww-evidence-label").get_text(strip=True) for screen in screens],
            ["Original program cards", "Proposed availability label"],
        )
        self.assertIsNone(figure.select_one(".ww-evidence-grid"))
        hashes = (
            "9ed660d118d7a6119b37c7f7cc2427bd7860d96792f0fcad3224348a4fd1f4bc",
            "eb1828e433788789cb656f4c44ba23f039189c2f7c514057b05c3f6d69e8f2f8",
        )
        dimensions = []
        for screen, filename, digest in zip(
            screens,
            ("ww-registration-original.png", "ww-registration-proposal.png"),
            hashes,
        ):
            self.assertIsNone(screen.select_one(".ww-browser-frame"))
            image = screen.select_one("img.ww-registration-image")
            self.assertEqual(Path(image["src"].split("?")[0]).name, filename)
            self.assertEqual(image.parent["href"], image["src"])
            self.assertEqual((image["width"], image["height"]), ("1440", "800"))
            source = ROOT / "assets" / filename
            self.assertEqual(source.read_bytes()[16:24], (1440).to_bytes(4, "big") + (800).to_bytes(4, "big"))
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)
            dimensions.append((image["width"], image["height"]))
        self.assertEqual(dimensions[0], dimensions[1])
        css = (ROOT / "assets/womens-wilderness.css").read_text()
        self.assertRegex(
            css,
            r"\.ww-registration-screens\s*\{\s*display:\s*flex;\s*flex-direction:\s*column;\s*gap:\s*32px;",
        )
        self.assertIn(".ww-copy .ww-evidence .ww-registration-screen img", css)
        self.assertRegex(css, r"\.ww-copy \.ww-evidence \.ww-registration-screen img\s*\{[^}]*width:\s*100%;[^}]*max-height:\s*none;")
        self.assertIn("proposed “Full - Waitlist Only” label", figure.figcaption.get_text())
        self.assertNotIn("This is a recommendation concept, not evidence of implementation.", figure.figcaption.get_text())

    def test_womens_wilderness_background_refinements(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        background = soup.select(".ww-copy")[0]
        paragraphs = background.find_all("p", recursive=False)
        self.assertEqual(
            paragraphs[1].get_text(),
            "Women’s Wilderness is a Colorado nonprofit organization that has helped girls, women, and LGBTQ+ people find their voice in the outdoors since 1998.",
        )
        self.assertEqual([strong.get_text() for strong in paragraphs[2].select("strong")], ["discovered", "registered"])
        self.assertEqual(
            paragraphs[4].get_text(),
            "Our research highlighted three opportunities to improve program discovery and registration:",
        )
        self.assertNotIn("The process involved", background.get_text())
        self.assertNotIn(
            "Program previews captured during the competitive review.",
            soup.get_text(),
        )

    def test_womens_wilderness_interview_topic_links(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        topics = soup.select_one("#user-interviews").find_next_sibling("ol")
        expected = [
            ("Site navigation and other information exploration", "finding-site-navigation"),
            ("Activities and programs discovery", "finding-program-discovery"),
            ("Activity Registration", "finding-activity-registration"),
        ]
        self.assertEqual(len(topics.select("a")), 3)
        for link, (label, target) in zip(topics.select("a"), expected):
            self.assertEqual(link.get_text(), label)
            self.assertEqual(link["href"], "#" + target)
            headings = soup.find_all(id=target)
            self.assertEqual(len(headings), 1)
            self.assertEqual(headings[0].name, "h4")
            self.assertEqual(headings[0]["tabindex"], "-1")
            self.assertTrue(headings[0].get_text().endswith(label))
        note = topics.find_previous_sibling()
        self.assertIn("ww-topic-note", note.get("class", []))
        self.assertEqual(
            note.get_text(),
            "(Select a topic below to scroll to the corresponding findings and recommendations.)",
        )
        self.assertEqual(note.em.get_text(), note.get_text())
        self.assertEqual(soup.select_one("#user-interviews").get_text(), "User Interview and Analysis")
        # Scoped native smooth scrolling honors sticky-header scroll padding.
        script = soup.select_one("#ww-topic-navigation").get_text()
        self.assertIn("stopPropagation", script)
        self.assertIn("preventDefault", script)
        self.assertIn("scrollIntoView", script)
        self.assertIn("'smooth'", script)
        self.assertIn("prefers-reduced-motion: reduce", script)
        self.assertIn("preventScroll: true", script)
        self.assertIn("history.pushState", script)
        self.assertIn("event.ctrlKey", script)

    def test_womens_wilderness_data_trends_synthesis(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        color = soup.select_one(".ww-color-coded")
        trends = soup.select_one(".ww-data-trends")
        self.assertIs(color.find_next_sibling(), trends)
        group = soup.select_one(".ww-synthesis")
        self.assertIs(color.parent, group)
        self.assertIs(trends.parent, group)
        self.assertEqual(group.find_next_sibling()["id"], "findings")
        self.assertEqual(len(group.select(":scope > figure")), 2)
        self.assertEqual(len(group.select(".ww-evidence")), 0)
        self.assertEqual(
            color.figcaption.get_text(),
            "The color-coded interview responses and category legend helped us identify participants who expressed similar thoughts, actions, or feelings.",
        )
        image = trends.img
        self.assertEqual((image["width"], image["height"]), ("1007", "617"))
        self.assertEqual(image["loading"], "lazy")
        self.assertTrue(image["alt"])
        self.assertEqual(image.parent["href"], image["src"])
        self.assertEqual(image.parent["target"], "_blank")
        metadata = json.loads((ROOT.parent / "content/sources/womens-wilderness-data-trends.json").read_text())
        asset = ROOT.parent / metadata["asset"]
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        self.assertEqual(digest, metadata["sha256"])
        self.assertEqual(digest, "94884cf7759dfbc3413055250fae7a0198a05e730f66e73754425ed9644d2b74")
        self.assertEqual(image["src"], "/assets/ww-data-trends.png?v=" + digest[:12])
        self.assertTrue(trends.figcaption.get_text(strip=True))

    def test_womens_wilderness_transparent_phone_previews(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        metadata = json.loads((ROOT.parent / "content/sources/womens-wilderness-transparent-previews.json").read_text())
        images = soup.select(".ww-program-previews img")
        self.assertEqual(len(images), 2)
        for image, entry in zip(images, metadata["assets"]):
            source = ROOT.parent / entry["source"]
            output = ROOT.parent / entry["output"]
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), entry["source_sha256"])
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["output_sha256"])
            self.assertEqual(image["src"], "/assets/" + output.name + "?v=" + digest[:12])
            self.assertEqual(image.parent["href"], image["src"])
            self.assertEqual((image["width"], image["height"]), ("530", "905"))
            self.assertEqual(output.read_bytes()[25], 6)  # PNG RGBA, not a white matte.
            self.assertEqual(entry["checks"]["all_four_corner_alpha"], 0)
            self.assertGreater(entry["checks"]["enclosed_original_pure_white_pixels_retained_opaque"], 10000)
            self.assertEqual(entry["checks"]["complete_original_annotation_pixels_retained_exactly"], 8472)

    def test_womens_wilderness_naming_comparison(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        figure = soup.select_one("#finding-site-navigation").find_next("figure")
        self.assertIn("ww-naming-comparison", figure["class"])
        self.assertEqual(len(figure.select("video")), 1)  # One shared playback clock.
        self.assertEqual(figure.find_next_sibling()["id"], "finding-program-discovery")
        video = figure.video
        self.assertEqual((video["width"], video["height"]), ("1000", "956"))
        for attribute in ("autoplay", "muted", "loop", "playsinline"):
            self.assertIn(attribute, video.attrs)
        self.assertNotIn("controls", video.attrs)
        self.assertEqual(video["preload"], "metadata")
        self.assertEqual(video["aria-describedby"], figure.figcaption["id"])
        self.assertIn("Original", video["aria-label"])
        self.assertIn("proposed", video["aria-label"])
        self.assertNotIn("Not implemented or usability-tested.", soup.get_text())
        self.assertIn("Proposed terminology", figure.figcaption.get_text())
        metadata = json.loads((ROOT.parent / "content/sources/womens-wilderness-naming-comparison.json").read_text())
        self.assertEqual(metadata["labels"], ["Original", "Proposed"])
        self.assertEqual(metadata["timing"]["frames"], 868)
        self.assertEqual(metadata["timing"]["fps"], 30)
        self.assertEqual(metadata["canvas"]["phone_size"], [440, 903])
        self.assertEqual(metadata["canvas"]["phone_origins"], [[20, 44], [540, 44]])
        outputs = {}
        for item in metadata["outputs"]:
            path = ROOT.parent / item["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, item["sha256"])
            outputs[path.suffix] = "/assets/" + path.name + "?v=" + digest[:12]
        sources = video.select("source")
        self.assertEqual([source["type"] for source in sources], ["video/webm", "video/mp4"])
        self.assertEqual([source["src"] for source in sources], [outputs[".webm"], outputs[".mp4"]])
        self.assertEqual(video["poster"], outputs[".jpg"])
        self.assertEqual(figure.figcaption.a["href"], outputs[".mp4"])
        media = json.loads((ROOT.parent / "content/sources/womens-wilderness-naming-media.json").read_text())
        self.assertEqual(media["changes"], {
            "PARTNERSHIP & CUSTOM PROGRAMS": "PARTNERSHIP & CUSTOM COURSES",
            "ADULT PROGRAMS": "ADULT COURSES",
            "YOUTH PROGRAMS": "YOUTH COURSES",
            "All Adult Programs": "All Adult Courses",
            "All Youth Programs": "All Youth Courses",
        })
        self.assertEqual(media["validation"]["frames_compared"], 868)
        for key in ("original_website_changed_frames", "proposed_pixels_outside_changed_labels", "faq_changed_frames"):
            self.assertEqual(media["validation"][key], [])
        renderer = ROOT.parent / "content/sources/render-womens-wilderness-naming.py"
        self.assertEqual(hashlib.sha256(renderer.read_bytes()).hexdigest(), media["renderer_sha256"])
        annotation = ROOT.parent / metadata["annotations"]["path"]
        self.assertEqual(hashlib.sha256(annotation.read_bytes()).hexdigest(), metadata["annotations"]["sha256"])
        highlights = json.loads(annotation.read_text())
        self.assertEqual(highlights["output"]["frames"], 868)
        self.assertEqual(highlights["style"]["outline_width_px"], 6)
        self.assertEqual(highlights["style"]["outline_rgb"], [255, 218, 0])
        for key in ("original_input_unmodified", "proposed_input_unmodified", "all_input_frames_retained",
                    "unchanged_frames_pixel_identical", "browser_chrome_pixel_identical",
                    "changed_word_foreground_pixel_identical"):
            self.assertTrue(highlights["invariants"][key])
        self.assertEqual(len(highlights["highlight_frames_by_label"]), 5)
        self.assertIn("yellow rectangles", figure.figcaption.get_text())

    def test_womens_wilderness_hiking_filter_animation(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        figure = soup.select_one(".ww-filter-comparison")
        self.assertEqual(figure.find_previous("h4")["id"], "finding-program-discovery")
        self.assertEqual([x.get_text() for x in figure.select(".ww-filter-view > figcaption")],
                         ["Original", "Proposed interaction"])
        metadata = json.loads((ROOT.parent / "content/sources/womens-wilderness-filter-animation.json").read_text())
        self.assertEqual(metadata["source"]["sha256"],
                         "d114ef437e0ff8a22e1d8ccb1dfd033ce735f654f5ecd4cb8e5730fd56c9796c")
        self.assertEqual(metadata["original"]["crop_source_xyxy_half_open"], [2, 240, 3022, 1800])
        self.assertEqual(metadata["browser_frame"]["address"], "https://womenswilderness.org/programs/")
        self.assertEqual(metadata["browser_frame"]["applies_to"], ["Original screenshot", "Proposed interaction"])
        self.assertTrue(all(metadata["proposed"]["verification"].values()))
        self.assertEqual(metadata["proposed"]["frames"], 270)
        self.assertEqual(metadata["proposed"]["duration_seconds"], 9)
        verification = metadata["proposed"]["verification"]
        for key in (
            "adult_selection_highlight_visible_from_first_frame",
            "adult_close_affordance_inside_highlight",
            "original_adult_text_unchanged",
            "font_family_and_settings_match_original",
            "matching_filter_label_typeface_and_highlight",
            "hiking_close_affordance_inside_highlight",
            "remove_filter_text_removed_from_proposed",
            "original_screenshot_unmodified",
            "remove_filter_region_white_at_proposed_start_and_end",
            "close_x_rendered_inside_hiking_highlight",
            "no_plus_between_filter_labels",
        ):
            self.assertTrue(verification[key])
        typography = metadata["proposed"]["chip_typography"]
        self.assertEqual((typography["text"], typography["font_family"], typography["weight"],
                          typography["size_css_px"], typography["line_height_css_px"]),
                         ("Hiking", "Windsor Roman", 500, 24, 24))
        self.assertEqual((typography["style"], typography["letter_spacing"],
                          typography["text_transform"]), ("normal", "normal", "none"))
        self.assertEqual(typography["source_ink_rgb"], [120, 21, 98])
        self.assertEqual(
            typography["selection_highlight"],
            "No fill; matching #FFDA00 outline, 3px stroke, and 10px radius for Adult and Hiking",
        )
        font_source = metadata["font_source"]
        self.assertEqual(font_source["font_resource_url"],
                         "https://womenswilderness.org/wp-content/uploads/2025/10/Windsor-BT-Roman.ttf")
        self.assertEqual(font_source["family"], "Windsor Roman")
        self.assertEqual(font_source["computed_css"], {
            "weight": "500",
            "font_size": "24px",
            "line_height": "24px",
            "font_style": "normal",
            "letter_spacing": "normal",
            "text_transform": "none",
        })
        self.assertEqual(font_source["adult_reference_ink_bbox_xyxy"], [1045, 677, 1175, 712])
        self.assertEqual(font_source["browser_canvas_adult_metrics"], {
            "advance_width_px": 128,
            "actual_bounding_box_left_px": 0,
            "actual_bounding_box_right_px": 130,
            "actual_bounding_box_ascent_px": 35,
            "actual_bounding_box_descent_px": 0,
        })
        label = ROOT.parent / font_source["hiking_label_raster"]["file"]
        self.assertEqual(hashlib.sha256(label.read_bytes()).hexdigest(),
                         font_source["hiking_label_raster"]["sha256"])
        self.assertEqual(font_source["hiking_label_raster"]["dimensions_px"], [154, 43])
        self.assertTrue(font_source["hiking_label_raster"]["font_file_not_redistributed"])
        urls = {}
        for name, entry in metadata["outputs"].items():
            asset = ROOT.parent / name
            self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), entry["sha256"])
            urls[asset.name] = "/assets/" + asset.name + "?v=" + entry["sha256"][:12]
        image = figure.select_one(".ww-filter-original-image")
        self.assertEqual(image["src"], urls["ww-filter-original.png"])
        self.assertEqual(image.parent["href"], image["src"])
        self.assertEqual(image.parent.parent["class"], ["ww-browser-frame"])
        self.assertEqual((image["width"], image["height"]), ("3020", "1560"))
        self.assertIn(b"iCCP", (ROOT / "assets/ww-filter-original.png").read_bytes())
        self.assertIn(b"ICC_PROFILE\x00", (ROOT / "assets/ww-filter-hiking-poster.jpg").read_bytes())
        video = figure.video
        self.assertEqual(video.parent["class"], ["ww-browser-frame"])
        self.assertEqual(len(figure.select(".ww-browser-url-text")), 2)
        self.assertEqual(
            [x.get_text(strip=True) for x in figure.select(".ww-browser-url-text")],
            ["womenswilderness.org/programs/"] * 2,
        )
        self.assertIn("highlighted from the first frame", metadata["proposed"]["new_ui_only"][1])
        self.assertIn("Adult has its own ×", metadata["proposed"]["new_ui_only"][2])
        self.assertIn("identical CSS font settings", metadata["proposed"]["new_ui_only"][3])
        self.assertIn("removed throughout the Proposed view", metadata["proposed"]["new_ui_only"][4])
        self.assertEqual(metadata["proposed"]["source_geometry_xyxy_half_open"]["all_adult_sidebar_outline"],
                         [329, 1439, 775, 1482])
        self.assertEqual(metadata["proposed"]["source_geometry_xyxy_half_open"]["adult_filter_label_outline"],
                         [1038, 663, 1208, 722])
        self.assertEqual(metadata["proposed"]["source_geometry_xyxy_half_open"]["adult_close_x"],
                         [1186, 686, 1202, 702])
        self.assertEqual(metadata["proposed"]["source_geometry_xyxy_half_open"]["hiking_chip"],
                         [1220, 664, 1414, 722])
        self.assertEqual(metadata["proposed"]["source_geometry_xyxy_half_open"]["hiking_text_origin"],
                         [1227, 677])
        self.assertEqual(metadata["proposed"]["source_geometry_xyxy_half_open"]["hiking_close_x"],
                         [1392, 686, 1408, 702])
        for attribute in ("autoplay", "muted", "loop", "playsinline"):
            self.assertTrue(video.has_attr(attribute))
        self.assertFalse(video.has_attr("controls"))
        self.assertEqual((video["width"], video["height"]), ("1510", "780"))
        self.assertEqual(video["poster"], urls["ww-filter-hiking-poster.jpg"])
        self.assertEqual([x["type"] for x in video.select("source")], ["video/webm", "video/mp4"])
        for source in video.select("source"):
            self.assertEqual(source["src"], urls["ww-filter-hiking." + source["type"].split("/")[1]])
        caption = figure.select_one("#ww-filter-caption")
        self.assertEqual(video["aria-describedby"], caption["id"])
        self.assertEqual(
            caption.find(string=True, recursive=False).strip(),
            "Multi-select “Adult” and “Hiking” in the filter to show only the adult hiking event.",
        )
        self.assertEqual(caption.a["href"], urls["ww-filter-hiking.webm"])
        self.assertEqual(caption.a.get_text(strip=True), "View full-size animation (WebM)")

    def test_womens_wilderness_desk_research_recording(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        figure = soup.select_one(".ww-desk-recording")
        desk_text = soup.select_one("#desk-research").find_next_sibling("p")
        self.assertIs(desk_text.find_next_sibling(), figure)
        self.assertEqual(figure.find_next_sibling()["id"], "competitive-analysis")
        video = figure.video
        self.assertNotIn("controls", video.attrs)
        self.assertIn("playsinline", video.attrs)
        for attribute in ("autoplay", "loop", "muted"):
            self.assertIn(attribute, video.attrs)
        self.assertEqual(video["preload"], "metadata")
        self.assertEqual([source["type"] for source in video.select("source")], ["video/webm", "video/mp4"])
        self.assertTrue(video["aria-label"])
        self.assertNotIn("aria-describedby", video.attrs)
        self.assertIsNone(figure.figcaption)
        self.assertNotIn("ww-evidence", figure["class"])
        self.assertFalse(figure.select("button"))
        self.assertIsNone(soup.select_one("#ww-video-controls"))
        for url in [source["src"] for source in video.select("source")] + [video["poster"]]:
            asset = ROOT / urlsplit(url).path.lstrip("/")
            self.assertTrue(asset.is_file())
            self.assertIn("?v=" + hashlib.sha256(asset.read_bytes()).hexdigest()[:12], url)

    def test_womens_wilderness_mobile_walkthroughs(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        points = soup.select(".ww-comparison > li")
        self.assertEqual(
            [f["data-recording"] for f in points[0].select(".ww-phone-recording")],
            ["ww-program-list", "bb-trips-list"],
        )
        self.assertEqual(
            [f.figcaption.get_text(strip=True) for f in points[0].select(".ww-phone-recording")],
            ["Women’s Wilderness", "Backcountry Beauties"],
        )
        self.assertEqual(
            [f["data-recording"] for f in points[1].select(".ww-phone-recording")],
            ["bb-waitlist"],
        )
        self.assertIsNotNone(points[1].select_one(".ww-phone-single"))
        self.assertFalse(points[2].select("video"))
        self.assertEqual(len(soup.select(".ww-phone-recording")), 3)
        for figure in soup.select(".ww-phone-recording"):
            self.assertEqual(figure.find_all(recursive=False)[0].name, "figcaption")
            video = figure.select_one(".ww-phone-frame video")
            self.assertIsNotNone(video)
            for attribute in ("autoplay", "loop", "muted", "playsinline"):
                self.assertIn(attribute, video.attrs)
            self.assertNotIn("controls", video.attrs)
            self.assertFalse(figure.select("button"))
            self.assertTrue(video["aria-label"])
            self.assertEqual([source["type"] for source in video.select("source")], ["video/webm", "video/mp4"])
            for url in [source["src"] for source in video.select("source")] + [video["poster"]]:
                asset = ROOT / urlsplit(url).path.lstrip("/")
                self.assertTrue(asset.is_file())
                self.assertIn("?v=" + hashlib.sha256(asset.read_bytes()).hexdigest()[:12], url)

    def test_womens_wilderness_browser_video_frame(self):
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        frame = soup.select_one(".ww-desk-recording .ww-browser-frame")
        self.assertIsNotNone(frame)
        self.assertIsNotNone(frame.select_one("video"))
        chrome = frame.select_one(".ww-browser-chrome")
        self.assertEqual(chrome["aria-hidden"], "true")
        self.assertEqual(len(chrome.select(".ww-window-dots > span")), 3)
        self.assertEqual(chrome.select_one(".ww-browser-url-text").get_text(), "womenswilderness.org")
        self.assertEqual(chrome.select_one(".ww-browser-tab-title").get_text(), "Women’s Wilderness")
        self.assertFalse(chrome.select("button, a, input"))
        icon = chrome.select_one("img")
        self.assertEqual(icon["alt"], "")
        asset = ROOT / urlsplit(icon["src"]).path.lstrip("/")
        self.assertIn("?v=" + hashlib.sha256(asset.read_bytes()).hexdigest()[:12], icon["src"])

    def test_womens_wilderness_reference_phone_frame(self):
        metadata = json.loads((ROOT.parent / "content/sources/womens-wilderness-video-frames.json").read_text())
        phone = metadata["phone_overlay"]
        frame = ROOT.parent / phone["asset"]
        content = frame.read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), phone["overlay_sha256"])
        self.assertEqual(content[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(
            (int.from_bytes(content[16:20], "big"), int.from_bytes(content[20:24], "big")),
            (440, 903),
        )
        self.assertEqual(content[25], 6)  # RGBA, including the transparent live screen.
        reference = ROOT.parent / phone["reference"]
        self.assertEqual(hashlib.sha256(reference.read_bytes()).hexdigest(), phone["reference_sha256"])
        self.assertEqual(phone["clock"]["text"], "12:37")
        self.assertIn("not recording-time evidence", phone["normalization"])
        css = ROOT / "assets/womens-wilderness.css"
        self.assertIn("/assets/ww-iphone-frame.png?v=" + phone["overlay_sha256"][:12], css.read_text())
        soup = BeautifulSoup((ROOT / "project/womens-wilderness/index.html").read_text(), "html.parser")
        self.assertIn(
            "?v=" + hashlib.sha256(css.read_bytes()).hexdigest()[:12],
            soup.select_one('link[href^="/assets/womens-wilderness.css"]')["href"],
        )

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
