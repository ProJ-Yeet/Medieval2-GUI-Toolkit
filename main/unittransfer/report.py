"""A problem report: the user's notes, what the page logged, the model, and
the server's log, in one zip - kept in ``config/reports/`` and, where an
address is set, sent to the developer.

The tester's notes on Armory Studio asked for "a detailed log system, a button
to send it directly to you, with a box to write notes in". The page keeps the
log (``armlog.js``: every Armory request, error and message); this writes it
out with what the server knows.

Sending, the way the Pfadfinder (Oogway) campaign editor does it: the zip goes
to a relay (a Cloudflare Worker, ``dev/report-relay/``) that holds the GitHub
token, commits the zip to a private reports repository and opens an issue
there, labelled bug or idea; the reporter gets a number, and the author's
answers come back into the dialog's second tab by that number. No token is in
the toolkit. Everything is scrubbed first (:func:`scrub`): the Windows user
name, the computer's name, e-mail addresses, Steam IDs and IP addresses, and
any words the reporter adds.

The relay's address is ``report_relay`` in the settings, else the first line
of ``report_relay.txt`` beside this file, else :data:`RELAY`. The older
Discord webhook still works the same way (``report_webhook``,
``report_webhook.txt``, :data:`WEBHOOK`) and is used when no relay is set.
With neither the report is only saved, and the page says where.
"""
from __future__ import annotations

import base64
import getpass
import io
import json
import os
import platform
import re
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


#: the relay's address (a Cloudflare Worker, see ``dev/report-relay/``)
RELAY = "https://m2-gui-kit-reports.projyeet17.workers.dev"
RELAY_FILE = Path(__file__).with_name("report_relay.txt")
#: the relay takes reports from this tool only, by this prefix
USER_AGENT = f"M2-GUI-Kit/{__version__}"
#: what the relay accepts, as its ZIP_CAP
RELAY_ZIP = 4 * 1024 * 1024
#: the reports this copy sent, by number, so their answers can be asked for
SENT = REPORTS / "sent.json"
#: a game log's start and end lines kept whole when it is cut
GAME_LOG_EDGE = 300
#: how many of the newest transfer records ride along
HISTORY = 8


def relay() -> str:
    """The settings' ``report_relay``, else :data:`RELAY_FILE`, else :data:`RELAY`."""
    s = str(config.load_settings().get("report_relay") or "").strip()
    if not s and RELAY_FILE.is_file():
        s = RELAY_FILE.read_text(encoding="utf-8").strip()
    return (s or RELAY.strip()).rstrip("/")


def can_send() -> bool:
    return bool(relay() or webhook())


# ---------------------------------------------------------------------------
# what is taken out before anything leaves


def _private_words(extra: List[str]) -> List[Tuple[str, str]]:
    words: List[Tuple[str, str]] = []
    for who in {getpass.getuser(), Path.home().name, os.environ.get("USERNAME", "")}:
        if who and len(who) > 2:
            words.append((who, "<user>"))
    pc = os.environ.get("COMPUTERNAME") or socket.gethostname()
    if pc and len(pc) > 2:
        words.append((pc, "<pc>"))
    words += [(w.strip(), "<hidden>") for w in extra if w and len(w.strip()) > 1]
    # longest first, so a name inside another is not cut out of it first
    return sorted(words, key=lambda p: -len(p[0]))


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_STEAM = re.compile(r"\b7656119\d{10}\b")
_IP = re.compile(r"\b(?!127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}\b")


def scrub(text: str, extra: List[str] = ()) -> str:
    """The text without the Windows user name (in paths too), the computer's
    name, e-mail addresses, Steam IDs, IP addresses and the reporter's own
    words to hide. The loopback address stays: it is the toolkit's own."""
    for word, mark in _private_words(list(extra)):
        text = re.sub(re.escape(word), mark, text, flags=re.IGNORECASE)
    text = _EMAIL.sub("<email>", text)
    text = _STEAM.sub("<steamid>", text)
    return _IP.sub("<ip>", text)


# ---------------------------------------------------------------------------
# the pieces


def _server_log_tail() -> str:
    p = logutil.log_path()
    if not p or not Path(p).is_file():
        return ""
    data = Path(p).read_bytes()
    return data[-SERVER_LOG_TAIL:].decode("utf-8", "replace")


def cut_game_log(text: str, edge: int = GAME_LOG_EDGE) -> str:
    """A long ``system.log.txt`` made to fit, as the editor cuts it: its start
    (where the game reads the mod's files and says what it does not like),
    every error and warning line of the middle, and its end."""
    lines = text.splitlines()
    if len(lines) <= 2 * edge:
        return text
    middle = [ln for ln in lines[edge:-edge]
              if re.search(r"\b(error|warning|fatal|crash|assert)\b", ln, re.IGNORECASE)]
    return "\n".join(lines[:edge] + [f"... {len(lines) - 2 * edge} lines cut; their errors and warnings:"]
                     + middle + ["... the end:"] + lines[-edge:])


def _game_logs(mods) -> Dict[str, str]:
    from . import gamelog
    out = {}
    for mod in mods:
        try:
            p = gamelog.find(mod)
        except Exception:                                    # noqa: BLE001
            p = None
        if p is None:
            continue
        data = p.read_bytes()[-gamelog.CAP:]
        out[f"game_log_{mod.name}.txt"] = cut_game_log(data.decode("utf-8", "replace"))
    return out


def _mod_picture(mod) -> str:
    """What the mod is, in counts and names: never its files."""
    rows = [f"name         {mod.name}", f"root         {mod.root}"]
    for label, p in (("EDU", mod.edu_path), ("modeldb", mod.modeldb_path),
                     ("export_units", mod.export_units_path),
                     ("export_units bin", Path(str(mod.export_units_path) + ".strings.bin")),
                     ("descr_mount", mod.descr_mount_path)):
        rows.append(f"{label:<17}{logutil._stat_line(p)}")
    try:
        rows.append(f"packs        {', '.join(sorted(p.name for p in (mod.data / 'packs').glob('*.pack'))) or '(none)'}")
    except OSError:
        pass
    for label, get in (("units", lambda: len(mod.edu.units)),
                       ("bmdb entries", lambda: len(mod.modeldb.entries))):
        try:
            rows.append(f"{label:<13}{get()}")
        except Exception as e:                               # noqa: BLE001
            rows.append(f"{label:<13}unreadable: {e}")
    try:
        from . import modflags
        rows.append(f"M2EX         {'yes' if modflags.is_m2ex(mod) else 'no'}")
    except Exception:                                        # noqa: BLE001
        pass
    return "\n".join(rows)


def _history(mod_names: List[str]) -> list:
    """The newest transfer records, the mods in view first; their summaries say
    what was asked and what was written."""
    entries = config.load_log()
    near = [e for e in entries if e.get("dest") in mod_names or e.get("source") in mod_names]
    keep = (near or entries)[-HISTORY:]
    return [{k: e.get(k) for k in ("id", "when", "source", "dest", "unit_type", "resolved_type",
                                   "action", "applied", "undone", "note", "summary", "warnings",
                                   "options")} for e in keep]


def _settings() -> dict:
    s = dict(config.load_settings())
    for k in list(s):
        if "webhook" in k or "relay" in k or "token" in k or k == "report_contact":
            s.pop(k)
    return s


def _picture(data_url: str) -> Optional[Tuple[str, bytes]]:
    m = re.match(r"data:image/(png|jpe?g|webp);base64,(.+)$", data_url or "", re.S)
    if not m:
        return None
    try:
        return ("jpg" if m.group(1).startswith("j") else m.group(1)), base64.b64decode(m.group(2))
    except ValueError:
        return None


def build(notes: str, page_log: list, project: Optional[dict], where: str = "",
          kind: str = "bug", contact: str = "", mods=(), pictures: List[str] = (),
          hide: List[str] = (), logs: bool = True) -> Tuple[str, bytes]:
    """The report as ``(file name, zip bytes)``, every text in it scrubbed.

    ``mods`` are the :class:`Mod` objects in view (the transfer's two, the
    editor's one): each gets a picture of itself and its newest game log.
    ``logs`` off sends an idea with the words and pictures alone.
    """
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = f"report-{stamp}.zip"
    hide = list(hide)

    def clean(t: str) -> str:
        return scrub(t, hide)
    about = {"version": __version__, "python": sys.version.split()[0], "os": platform.platform(),
             "kind": kind, "where": where, "mods": [m.name for m in mods],
             "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.txt", clean(f"[{kind}] {where}\n\n{notes or ''}\n\nContact: {contact or 'none'}\n"))
        z.writestr("about.json", json.dumps(about, indent=1))
        for i, url in enumerate(pictures or []):
            pic = _picture(url)
            if pic:
                z.writestr(f"screenshot_{i + 1}.{pic[0]}", pic[1])
        if logs:
            z.writestr("page_log.json", clean(json.dumps(page_log or [], indent=1, ensure_ascii=False)))
            if project:
                z.writestr("model.json", json.dumps(project, ensure_ascii=False))
            z.writestr("server_log_tail.txt", clean(_server_log_tail()))
            z.writestr("transfers.json", clean(json.dumps(_history([m.name for m in mods]),
                                                          indent=1, ensure_ascii=False)))
            z.writestr("settings.json", clean(json.dumps(_settings(), indent=1, ensure_ascii=False)))
            for m in mods:
                z.writestr(f"mod_{m.name}.txt", clean(_mod_picture(m)))
            for fname, text in _game_logs(mods).items():
                z.writestr(fname, clean(text))
    return name, buf.getvalue()


def show(data: bytes) -> List[Dict]:
    """Every file in the zip as it will go: the text ones whole, the rest by size."""
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            raw = z.read(info)
            text = (raw.decode("utf-8", "replace")
                    if info.filename.endswith((".txt", ".json")) else None)
            out.append({"name": info.filename, "bytes": len(raw), "text": text})
    return out


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


# ---------------------------------------------------------------------------
# the relay: a report filed as a GitHub issue, and the author's answers back


def _relay_post(path: str, body: dict, timeout: int = 60) -> dict:
    url = relay()
    if not url:
        raise ReportError(_i18n.msg("eng.report.no_address", "no address to send reports to is set"))
    req = urllib.request.Request(url + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            why = json.loads(e.read().decode("utf-8")).get("error") or f"HTTP {e.code}"
        except (ValueError, OSError):
            why = f"HTTP {e.code}"
        raise ReportError(_i18n.msg("eng.report.send_failed", "the report did not go: {why}; it is saved", why=why))
    except (OSError, ValueError) as e:
        raise ReportError(_i18n.msg("eng.report.send_failed", "the report did not go: {why}; it is saved", why=e))


def sent_list() -> List[Dict]:
    try:
        return json.loads(SENT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _keep_sent(items: List[Dict]) -> None:
    SENT.parent.mkdir(parents=True, exist_ok=True)
    SENT.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")


def send_relay(data: bytes, notes: str, kind: str, contact: str, where: str,
               mods: List[str], hide: List[str] = ()) -> Dict:
    """File the report through the relay: ``{id, issue}``, kept in :data:`SENT`."""
    if len(data) > RELAY_ZIP:
        raise ReportError(_i18n.msg("eng.report.too_big", "the report is {mb} MB, more than can be sent; it is saved",
                                    mb=round(len(data) / 1e6, 1)))
    info = {"kind": "idea" if kind == "idea" else "bug", "version": __version__,
            "os": platform.platform(), "where": where, "mods": ", ".join(mods)}
    out = _relay_post("/", {"kind": info["kind"], "message": scrub(notes or "", list(hide)),
                            "contact": contact or "", "info": info,
                            "zip": base64.b64encode(data).decode("ascii")})
    if not out.get("id"):
        raise ReportError(_i18n.msg("eng.report.send_failed", "the report did not go: {why}; it is saved",
                                    why=out.get("error") or "no report number came back"))
    items = sent_list()
    items.append({"id": out["id"], "issue": out.get("issue") or 0, "kind": info["kind"],
                  "title": (notes or "").strip().splitlines()[0][:80] if (notes or "").strip() else "",
                  "when": time.strftime("%Y-%m-%d %H:%M"), "seen": 0})
    _keep_sent(items)
    return out


def answers() -> List[Dict]:
    """Every report this copy sent, each with its state and the talk so far;
    ``new`` counts the author's messages not yet seen."""
    items = sent_list()
    if not items:
        return []
    got = _relay_post("/answers", {"reports": [{"id": i["id"], "issue": i.get("issue") or 0}
                                               for i in items[-30:]]}, timeout=30).get("answers") or {}
    for i in items:
        a = got.get(i["id"])
        if a:
            i.update(issue=a.get("issue") or i.get("issue"), state=a.get("state", ""),
                     reason=a.get("reason", ""), messages=a.get("messages") or [])
        mine = [m for m in i.get("messages") or [] if m.get("from") == "author"]
        i["new"] = max(0, len(mine) - int(i.get("seen") or 0))
    _keep_sent([{k: v for k, v in i.items() if k != "new"} for i in items])
    return items


def mark_seen(report_id: str) -> None:
    items = sent_list()
    for i in items:
        if i["id"] == report_id:
            i["seen"] = len([m for m in i.get("messages") or [] if m.get("from") == "author"])
    _keep_sent(items)


def reply(report_id: str, message: str, data: Optional[bytes] = None) -> None:
    """The reporter's answer, a comment on the same issue, with new files if any."""
    item = next((i for i in sent_list() if i["id"] == report_id), None)
    if item is None:
        raise ReportError(_i18n.msg("eng.report.no_such_report", "this copy sent no report {id}", id=report_id))
    body = {"id": report_id, "issue": item.get("issue") or 0, "message": scrub(message or "")}
    if data:
        if len(data) > RELAY_ZIP:
            raise ReportError(_i18n.msg("eng.report.too_big", "the report is {mb} MB, more than can be sent; it is saved",
                                        mb=round(len(data) / 1e6, 1)))
        body["zip"] = base64.b64encode(data).decode("ascii")
    out = _relay_post("/reply", body)
    if not out.get("ok"):
        raise ReportError(_i18n.msg("eng.report.send_failed", "the report did not go: {why}; it is saved",
                                    why=out.get("error") or "?"))
