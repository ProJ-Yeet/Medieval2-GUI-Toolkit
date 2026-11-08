"""The page and its scripts must never be kept by the browser.

After an update replaces web/, a browser that kept yesterday's scripts runs
them against today's index.html and stops partway through start-up (seen in
Brave on 2026-11-08: only a hard refresh brought the toolkit back). So every
file the UI is built from is sent with Cache-Control: no-store.
"""
import os
import threading
import unittest
import urllib.request

os.environ.setdefault("UT_NO_BROWSER", "1")


class WebFilesAreNotStored(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from unittransfer.server import Handler, _Server
        cls.server = _Server(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def cache_control(self, path):
        url = f"http://127.0.0.1:{self.server.server_port}{path}"
        with urllib.request.urlopen(url) as r:
            self.assertEqual(r.status, 200, path)
            return ", ".join(r.headers.get_all("Cache-Control") or [])

    def test_page_scripts_and_catalogue(self):
        for path in ("/", "/js/core.js", "/js/builder.js", "/i18n/catalogue.js"):
            with self.subTest(path=path):
                self.assertIn("no-store", self.cache_control(path))


if __name__ == "__main__":
    unittest.main()
