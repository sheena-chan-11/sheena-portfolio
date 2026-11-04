"""Update static head metadata without reserializing Webflow markup or scripts."""
from pathlib import Path
import hashlib
import html
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
ORIGIN = "https://sheenachan.com"
IMAGE = PUBLIC / "assets/sheena-chan-social-preview.jpg"
IMAGE_URL = ORIGIN + "/assets/" + IMAGE.name + "?v=" + hashlib.sha256(IMAGE.read_bytes()).hexdigest()[:12]
PAGES = {
    "index.html": (
        "Sheena Chan | UX Design & Research Portfolio",
        "Explore Sheena Chan’s UX design and research projects, creating thoughtful, human-centered digital experiences.",
    ),
    "aboutme/index.html": (
        "About Sheena Chan | UX Design & Research",
        "Meet Sheena Chan, a designer with a background in digital campaigns and a passion for human-centered design.",
    ),
    "latestprojects/index.html": (
        "UX Projects | Sheena Chan",
        "Explore Step by Step, Women’s Wilderness, and Small Angel Rescue: UX design and research projects by Sheena Chan.",
    ),
    "project/step-by-step/index.html": (
        "Step by Step — Coming Soon | Sheena Chan",
        "A UX project helping U.S. college students build quick movement breaks into their routine. Full case study coming soon.",
    ),
    "project/womens-wilderness/index.html": (
        "Women’s Wilderness | Sheena Chan",
        "A UX research case study exploring program discovery, navigation, filtering, and registration on an outdoor recreation website.",
    ),
    "project/sarinc/index.html": (
        "Small Angel Rescue | Sheena Chan",
        "A UX design case study on driving traffic to pet-care resources through a mobile-first nonprofit homepage redesign.",
    ),
    "project/petpal/index.html": (
        "Petpal | Sheena Chan",
        "Explore Sheena Chan’s Petpal design project.",
    ),
}


def apply():
    for relative, (title, description) in PAGES.items():
        path = PUBLIC / relative
        text = path.read_text()
        head, body = text.split("</head>", 1)
        head = re.sub(r"<title>.*?</title>", "", head, flags=re.DOTALL)
        # Remove only the metadata we own; leave styles, vendor scripts, SRI,
        # Webflow interaction hooks, and body content byte-for-byte unchanged.
        head = re.sub(
            r'<meta\b[^>]*(?:name|property)=["\'](?:description|og:[^"\']+|twitter:[^"\']+)["\'][^>]*>',
            "", head, flags=re.IGNORECASE,
        )
        head = re.sub(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', "", head, flags=re.IGNORECASE)
        url = ORIGIN + ("/" if relative == "index.html" else "/" + relative.removesuffix("index.html"))
        tags = ["<title>" + html.escape(title) + "</title>"]
        values = [
            ("name", "description", description),
            ("property", "og:type", "website"),
            ("property", "og:site_name", "Sheena Chan"),
            ("property", "og:title", title),
            ("property", "og:description", description),
            ("property", "og:url", url),
            ("property", "og:image", IMAGE_URL),
            ("property", "og:image:secure_url", IMAGE_URL),
            ("property", "og:image:type", "image/jpeg"),
            ("property", "og:image:width", "1200"),
            ("property", "og:image:height", "630"),
            ("property", "og:image:alt", "Sheena Chan — UX Design & Research, pictured among books. sheenachan.com"),
            ("name", "twitter:card", "summary_large_image"),
            ("name", "twitter:title", title),
            ("name", "twitter:description", description),
            ("name", "twitter:image", IMAGE_URL),
            ("name", "twitter:image:alt", "Sheena Chan — UX Design & Research, pictured among books. sheenachan.com"),
        ]
        tags.extend(f'<meta {attribute}="{key}" content="{html.escape(value, quote=True)}"/>' for attribute, key, value in values)
        tags.append(f'<link rel="canonical" href="{url}"/>')
        # Keeping the generated block inline makes repeated runs idempotent.
        path.write_text(head + "".join(tags) + "</head>" + body)


if __name__ == "__main__":
    apply()
