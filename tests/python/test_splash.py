"""Tests for the startup splash.

Run from the repo root:  python -m unittest discover -s tests/python
"""
import re
import unittest
from pathlib import Path
from unittest import mock

from core import splash

REPO_ROOT = Path(__file__).resolve().parents[2]


class SplashTests(unittest.TestCase):
    def test_needs_no_network_or_server(self):
        # It paints before the server is up, so it can't fetch anything
        self.assertNotRegex(splash.SPLASH_HTML, r"https?://")
        self.assertNotIn("/static/", splash.SPLASH_HTML)
        self.assertNotRegex(splash.SPLASH_HTML, r"<script[^>]*\bsrc=|<link")

    def test_can_report_a_failed_start(self):
        # main.py calls this when the server can't start, instead of leaving it spinning
        self.assertIn("window.showStartupError = function", splash.SPLASH_HTML)
        self.assertIn('id="status" hidden', splash.SPLASH_HTML)

    def test_embeds_the_logo_inline(self):
        self.assertIn('src="data:image/png;base64,', splash.SPLASH_HTML)

    def test_still_renders_without_the_logo_file(self):
        with mock.patch.object(splash, "LOGO_PATH", REPO_ROOT / "does-not-exist.png"):
            self.assertEqual(splash._logo_markup(), "")

    def test_shows_the_product_name(self):
        self.assertIn(">AURA AI<", splash.SPLASH_HTML)

    def test_background_matches_the_app_theme(self):
        css = (REPO_ROOT / "web" / "css" / "main.css").read_text(encoding="utf-8")
        bg_primary = re.search(r"--bg-primary:\s*(#[0-9a-fA-F]{6})", css).group(1)

        self.assertEqual(splash.WINDOW_BACKGROUND.lower(), bg_primary.lower())
        self.assertIn(splash.WINDOW_BACKGROUND, splash.SPLASH_HTML)
        self.assertNotIn("__BACKGROUND__", splash.SPLASH_HTML)
        self.assertNotIn("__LOGO__", splash.SPLASH_HTML)


if __name__ == "__main__":
    unittest.main()
