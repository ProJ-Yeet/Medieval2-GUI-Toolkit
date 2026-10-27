"""A problem report: the user's notes, what the page logged, the model, and
the server's log, in one zip - kept in ``config/reports/`` and, where an
address is set, sent to the developer.

The tester's notes on Armory Studio asked for "a detailed log system, a button
to send it directly to you, with a box to write notes in". The page keeps the
log (``armlog.js``: every Armory request, error and message); this writes it
out with what the server knows.

Sending is a Discord webhook on the project server's forum channel: each
report a new post, titled with the first line of the notes, the notes as its
message and the zip attached.
The address is ``report_webhook`` in the settings, else the first line of
``report_webhook.txt`` beside this file (git ignores it: the repository is
public, the zip is not where a secret should live either, but a tester's copy
needs it to send), else :data:`WEBHOOK`; with none the report is only saved,
and the page says where.
"""
from __future__ import annotations

import io
import json
import platform
import sys
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from . import __version__, config, logutil
from . import i18n as _i18n

#: the developer's own address for reports, a webhook on the project Discord's
#: forum channel (each report a new post); empty sends nothing
WEBHOOK = ""
#: how much of the end of server.log rides along
SERVER_LOG_TAIL = 400_000
#: Discord takes 10 MB on a webhook without a boost; a model is far less
MAX_ZIP = 9_500_000
REPORTS = config.CONFIG_DIR / "reports"


class ReportError(Exception):
    pass


#: the address kept beside this file, out of git (the repository is public)
#: but copied into a release zip with the rest of the folder
WEBHOOK_FILE = Path(__file__).with_name("report_webhook.txt")


def webhook() -> str:
    """The settings' ``report_webhook``, else :data:`WEBHOOK_FILE`, else
    :data:`WEBHOOK`."""
    s = str(config.load_settings().get("report_webhook") or "").strip()
    if not s and WEBHOOK_FILE.is_file():
        s = WEBHOOK_FILE.read_text(encoding="utf-8").strip()
    return s or WEBHOOK.strip()


def _server_log_tail() -> str:
    p = logutil.log_path()
    if not p or not Path(p).is_file():
        return ""
    data = Path(p).read_bytes()
    return data[-SERVER_LOG_TAIL:].decode("utf-8", "replace")


def build(notes: str, page_log: list, project: Optional[dict], where: str = "") -> Tuple[str, bytes]:
    """The report as ``(file name, zip bytes)``."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = f"report-{stamp}.zip"
    about = {"version": __version__, "python": sys.version.split()[0], "os": platform.platform(),
             "where": where, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("notes.txt", notes or "")
        z.writestr("about.json", json.dumps(about, indent=1))
        z.writestr("page_log.json", json.dumps(page_log or [], indent=1, ensure_ascii=False))
        if project:
            z.writestr("model.json", json.dumps(project, ensure_ascii=False))
        z.writestr("server_log_tail.txt", _server_log_tail())
    return name, buf.getvalue()


def save(name: str, data: bytes) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / name
    out.write_bytes(data)
    return out


def send(name: str, data: bytes, notes: str, url: Optional[str] = None) -> None:
    """The zip posted to the webhook as an attachment."""
    url = url if url is not None else webhook()
    if not url:
        raise ReportError(_i18n.msg("eng.report.no_address", "no address to send reports to is set"))
    if len(data) > MAX_ZIP:
        raise ReportError(_i18n.msg("eng.report.too_big", "the report is {mb} MB, more than can be sent; it is saved",
                                    mb=round(len(data) / 1e6, 1)))
    head = (notes or "").strip().splitlines()
    # a forum channel makes each post a thread, and a thread needs a name
    title = (head[0].strip() if head else "") or "no notes"
    thread = f"{__version__}: {title}"[:100]
    text = f"Problem report, {__version__}\n\n" + (notes or "").strip()[:1800]
    boundary = uuid.uuid4().hex
    body = io.BytesIO()

    def part(headers: str, payload: bytes):
        body.write(f"--{boundary}\r\n{headers}\r\n\r\n".encode("utf-8"))
        body.write(payload)
        body.write(b"\r\n")
    part('Content-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json',
         json.dumps({"content": text, "thread_name": thread}).encode("utf-8"))
    part(f'Content-Disposition: form-data; name="files[0]"; filename="{name}"\r\nContent-Type: application/zip', data)
    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    req = urllib.request.Request(url, data=body.getvalue(), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                          "User-Agent": f"M2-GUI-Kit/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status >= 300:
                raise ReportError(f"HTTP {r.status}")
    except OSError as e:
        raise ReportError(_i18n.msg("eng.report.send_failed", "the report did not go: {why}; it is saved", why=e))
