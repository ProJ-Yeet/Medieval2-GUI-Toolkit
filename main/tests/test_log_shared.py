"""server.log keeps being written while another process holds it open.

Two toolkit processes (a second launch, a restart's replacement, a test
server) share config/server.log. On Windows a file another process has open
cannot be renamed, so once it reached its size limit every log line tried to
rotate it, failed, printed a "--- Logging error ---" traceback and was lost:
seen 2026-11-25, nothing logged for half an hour. A rotation that fails now
leaves the file as it is, writes the line, and is tried again a minute later.

    python -m tests.test_log_shared
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _tmp  # noqa: E402
from unittransfer import logutil  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


print("\n-- a log another process holds open --")
check("logutil has the shared-file handler", hasattr(logutil, "SharedRotatingFileHandler"))
if hasattr(logutil, "SharedRotatingFileHandler"):
    tmp = Path(_tmp.mkdtemp(prefix="ut_logshare_"))
    path = tmp / "server.log"
    errors = []
    h = logutil.SharedRotatingFileHandler(path, maxBytes=300, backupCount=2, encoding="utf-8")
    h.handleError = lambda record: errors.append(record)
    h.setFormatter(logging.Formatter("%(message)s"))
    other = open(path, "a", encoding="utf-8")       # the other process
    rec = lambda i: logging.LogRecord("t", logging.INFO, __file__, 1, f"line {i:03d} " + "x" * 40, None, None)
    for i in range(30):
        h.emit(rec(i))
    h.flush()
    text = path.read_text(encoding="utf-8")
    held = sys.platform == "win32"
    check(f"every line written while held ({sum(f'line {i:03d}' in text for i in range(30))}/30)",
          all(f"line {i:03d}" in text for i in range(30)))
    check(f"no logging errors ({len(errors)})", not errors)
    if held:
        check("the file was not rotated while held", not (tmp / "server.log.1").exists())
    other.close()
    h._retry_at = 0.0                                # the minute has passed
    h.emit(rec(99))
    h.close()
    check("once let go, it rotates again", (tmp / "server.log.1").exists())

print()
print(f"{sum(ok)}/{len(ok)} checks - " + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
