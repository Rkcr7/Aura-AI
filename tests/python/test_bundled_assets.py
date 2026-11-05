"""The UI must load without the internet: everything index.html pulls in is bundled.

Run from the repo root:  python -m unittest discover -s tests/python
"""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
# src/href values on <script> and <link> tags
ASSET_REFS = re.findall(r"<(?:script|link)\b[^>]*\b(?:src|href)=\"([^\"]+)\"", INDEX)


class BundledAssetTests(unittest.TestCase):
    def test_index_loads_nothing_from_the_internet(self):
        external = [ref for ref in ASSET_REFS if re.match(r"(https?:)?//", ref)]
        self.assertEqual(external, [])

    def test_every_static_reference_exists(self):
        static = [ref for ref in ASSET_REFS if ref.startswith("/static/")]
        self.assertGreater(len(static), 5)
        missing = [ref for ref in static if not (WEB / ref[len("/static/"):]).is_file()]
        self.assertEqual(missing, [])

    def test_bundled_css_points_at_bundled_files(self):
        for css in (WEB / "vendor").rglob("*.css"):
            text = css.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"url\((['\"]?)(https?:)?//", f"{css.name} reaches out to the network")
            for url in re.findall(r"url\(['\"]?([^)'\"]+)['\"]?\)", text):
                if url.startswith("data:"):
                    continue
                # KaTeX lists .woff and .ttf fallbacks after .woff2; WebView2 only fetches the .woff2
                if url.endswith((".woff", ".ttf")):
                    continue
                self.assertTrue((css.parent / url).is_file(), f"{css.name}: {url} is missing")

    def test_prism_has_the_languages_its_autoloader_fetches(self):
        components = WEB / "vendor" / "prism" / "components"
        for language in ("python", "javascript", "java", "cpp", "c", "clike", "go", "rust", "sql", "typescript"):
            self.assertTrue((components / f"prism-{language}.min.js").is_file(), language)


if __name__ == "__main__":
    unittest.main()
