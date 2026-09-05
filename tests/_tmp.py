"""Scratch directories that sweep themselves up when the run ends.

Every suite here builds its fixtures in a real folder under ``%TEMP%`` and most
of them called :func:`tempfile.mkdtemp` and left it there. Ninety-eight of the
173 call sites removed the folder by hand; the other seventy-five did not, and
one suite that copied a whole mod put eight gigabytes in ``%TEMP%`` per run. By
2026-09-05 the pile was about 37 GB.

So the folder is registered the moment it is made and removed on the way out -
including when a suite exits early through ``_realmod.pick``'s SKIPPED path, and
when one dies on a traceback, both of which still run ``atexit`` handlers. Set
``UT_KEEP_TEMP=1`` to keep the folders when you need to look inside one after a
failure.
"""
import atexit
import os
import shutil
import tempfile

_made = []


def mkdtemp(prefix="ut_", **kw) -> str:
    """:func:`tempfile.mkdtemp`, but the folder is removed when the run ends."""
    made = tempfile.mkdtemp(prefix=prefix, **kw)
    _made.append(made)
    return made


def sweep() -> int:
    """Remove every folder handed out so far. Returns how many went."""
    gone = 0
    while _made:
        made = _made.pop()
        if os.path.isdir(made):
            shutil.rmtree(made, ignore_errors=True)
            gone += 1
    return gone


@atexit.register
def _sweep_at_exit():
    if os.environ.get("UT_KEEP_TEMP"):
        if _made:
            print(f"  (kept {len(_made)} temp folders, UT_KEEP_TEMP is set)")
        return
    sweep()
