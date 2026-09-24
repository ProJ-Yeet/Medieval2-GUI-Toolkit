"""Run the test suites in the background: no browser tab, no console window.

    python main/dev/checks/run_suites.py                  # every suite
    python main/dev/checks/run_suites.py test_cas test_edbimport
    run_suites.bat                                        # the same, hidden

Six at once (the suite is CPU-bound; one full pass is about ten minutes on
this machine), each under a 900 s limit, each with ``UT_NO_BROWSER=1`` so a
suite that launches the real app (``test_startup`` does, twice) opens no tab
in the default browser. Each suite runs with no console window of its own.

The report is written next to this file as ``suite_report.txt``, one line per
failed suite with its first failing checks, and ``suite_report.json`` with
every suite. ``suite_report.txt`` says RUNNING until the pass is done, so a
glance tells whether it has finished.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[1]
REPORT = HERE / "suite_report.txt"
WORKERS = 6
LIMIT = 900
#: No console window for a suite, nor for anything a suite starts in turn.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _python() -> str:
    """python.exe beside whichever interpreter runs this, pythonw.exe included:
    a suite's own output has to come back through a pipe, and pythonw has none."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").is_file():
        return str(exe.parent / "python.exe")
    return str(exe)


def run(name: str) -> dict:
    t = time.time()
    env = {**os.environ, "UT_NO_BROWSER": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run([_python(), "-m", f"tests.{name}"], cwd=MAIN, env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=LIMIT, creationflags=NO_WINDOW)
        text, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        text, code = f"TIMEOUT after {LIMIT} s", -1
    lines = text.strip().splitlines()
    fails = [ln.strip() for ln in lines
             if "[FAIL]" in ln or re.match(r"^\w+(\.\w+)*(Error|Exception):", ln.strip())
             or ln.startswith("TIMEOUT")]
    return {"suite": name, "code": code, "secs": round(time.time() - t),
            "fails": fails[:8], "last": lines[-1] if lines else ""}


def main(argv) -> int:
    names = argv or sorted(p.stem for p in (MAIN / "tests").glob("test_*.py"))
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    REPORT.write_text(f"RUNNING since {started}: {len(names)} suite(s)\n", encoding="utf-8")
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        results = list(ex.map(run, names))
    bad = [r for r in results if r["code"] != 0]
    out = [f"{len(results)} suite(s), {len(bad)} failed, {round(time.time() - t0)} s "
           f"(started {started}, finished {time.strftime('%H:%M:%S')})", ""]
    for r in bad:
        out.append(f"{r['suite']} ({r['secs']} s): {r['last']}")
        out += [f"    {f[:200]}" for f in r["fails"][:4]]
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8")
    (HERE / "suite_report.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(out[0])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
