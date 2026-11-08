"""How the browser may keep the page and its scripts.

After an update replaces web/, a browser that kept yesterday's scripts ran them
against today's index.html and stopped partway through start-up (Brave,
2026-11-08: only a hard refresh brought the toolkit back). Fetching all ~110
scripts on every load instead made a script cut off mid-transfer likely, which
fails as "ARM is not defined" (same day). So:

* index.html is never stored, and names every script with the build's stamp
  (js/x.js?v=...);
* a stamped script may be kept for good: a new build has a new stamp;
* an unstamped script, and the language catalogue, are never stored.
"""
import os
import re
import threading
import unittest
import urllib.request

os.environ.setdefault("UT_NO_BROWSER", "1")


class WebCaching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from unittransfer.server import Handler, _Server
        cls.server = _Server(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        url = f"http://127.0.0.1:{self.server.server_port}{path}"
        with urllib.request.urlopen(url) as r:
            self.assertEqual(r.status, 200, path)
            return r.read().decode("utf-8"), ", ".join(r.headers.get_all("Cache-Control") or [])

    def test_page_is_never_stored_and_stamps_every_script(self):
        html, cache = self.get("/")
        self.assertIn("no-store", cache)
        scripts = re.findall(r'<script src="(js/[^"]+)"', html)
        self.assertGreater(len(scripts), 50)
        stamps = {re.search(r"\?v=([0-9a-f]+)$", s).group(1) for s in scripts}
        self.assertEqual(len(stamps), 1, "one build, one stamp")
        self.assertIn('src="i18n/catalogue.js"', html, "the catalogue is per language, never stamped")

    def test_stamped_scripts_are_kept_unstamped_are_not(self):
        html, _ = self.get("/")
        stamped = re.search(r'<script src="(js/core\.js\?v=[0-9a-f]+)"', html).group(1)
        _, cache = self.get("/" + stamped)
        self.assertIn("immutable", cache)
        self.assertNotIn("no-store", cache)
        for path in ("/js/core.js", "/i18n/catalogue.js"):
            with self.subTest(path=path):
                self.assertIn("no-store", self.get(path)[1])

    def test_stamp_follows_the_files(self):
        from unittransfer import server
        before = server.web_stamp()
        js = server.WEB_DIR / "js" / "core.js"
        st = js.stat()
        try:
            os.utime(js, (st.st_atime, st.st_mtime + 5))
            self.assertNotEqual(server.web_stamp(), before)
        finally:
            os.utime(js, (st.st_atime, st.st_mtime))


if __name__ == "__main__":
    unittest.main()
