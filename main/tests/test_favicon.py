"""The toolkit's icon (2026-11-26): the browser tab shows it.

The icon is Jopero's, at web/img/guitoolkit.ico. The page links it, and
/favicon.ico answers too, because a browser asks for that on its own.
"""
from __future__ import annotations

import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import config  # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

from unittransfer.server import Handler, Registry, _Server  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def get(path):
    try:
        with urllib.request.urlopen(base + path, timeout=30) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, "", b""


ico = (ROOT / "web" / "img" / "guitoolkit.ico").read_bytes()
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
base = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()
try:
    check("the icon is a Windows .ico", ico[:4] == b"\x00\x00\x01\x00")
    for path in ("/img/guitoolkit.ico", "/favicon.ico"):
        st, ct, body = get(path)
        check(f"{path} serves the icon as image/x-icon", st == 200 and ct == "image/x-icon" and body == ico)
    st, _, page = get("/")
    check("the page links the icon", b'<link rel="icon" href="img/guitoolkit.ico"' in page)
finally:
    httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
