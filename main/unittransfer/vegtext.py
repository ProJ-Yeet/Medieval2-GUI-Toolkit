"""M2EX's text vegetation: ``data/descr_vegetation.txt``, written by the game.

``vegetation.db`` is binary and only the game reads it, so unlike the battle
models (modeltext.convert) the toolkit cannot turn it into text itself. M2EX
can: started with ``--util.vegetation_decompile`` it writes
``data/descr_vegetation_decompiled.txt`` while it loads, which is what the
user's ``M2EX_txt_convert`` batch file does (``M2EX.exe @<mod's cfg>
--util.modeldb_decompile --util.vegetation_decompile`` from the game folder,
the .cfg as a relative path because the engine cannot read one with a space
in it).

So here: :func:`start` runs the game that way for one mod and returns; the
player gets to the main menu and quits; :func:`status`, asked by the page,
sees the game gone and :func:`finish` takes the file. A new
``descr_vegetation.txt`` gets ``vegetation_source text`` in the mod's
``descr_caps_ex.txt``, both in one Undo. A ``descr_vegetation.txt`` the mod
already has is never overwritten: the game's file stays beside it as
``descr_vegetation_decompiled.txt``, as the batch file leaves it, and the caps
file is not touched.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from . import config
from . import keyblock as kb
from . import modeltext
from . import i18n as _i18n
from .logutil import file_op, log

EXE = "M2EX.exe"
TEXT_REL = "descr_vegetation.txt"
OUT_REL = "descr_vegetation_decompiled.txt"
KEY = "vegetation_source"
SWITCH = "--util.vegetation_decompile"

#: mod name -> the run under way: {proc, started, data}
_RUNS: Dict[str, dict] = {}


class VegError(Exception):
    pass


def _game_and_cfg(mod) -> tuple:
    root = Path(mod.root)
    if root.parent.name.lower() != "mods":
        raise VegError(_i18n.msg("eng.vegtext.not_in_mods", "{name} is not in the game's mods folder", name=mod.name))
    game = root.parent.parent
    if not (game / EXE).is_file():
        raise VegError(_i18n.msg("eng.vegtext.no_m2ex", "{exe} is not in the game folder {game}", exe=EXE, game=str(game)))
    cfgs = sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".cfg")
    if not cfgs:
        raise VegError(_i18n.msg("eng.vegtext.no_cfg", "{name} has no .cfg file, so the game cannot load it", name=mod.name))
    return game, "mods\\%s\\%s" % (root.name, cfgs[0].name)


def command(mod) -> tuple:
    """``(game folder, the command line)`` a run starts."""
    game, cfg = _game_and_cfg(mod)
    return game, [str(game / EXE), "@" + cfg, SWITCH]


def start(mod, popen=subprocess.Popen) -> dict:
    """Start the game on this mod with the vegetation switch; returns at once."""
    run = _RUNS.get(mod.name)
    if run and run["proc"].poll() is None:
        raise VegError(_i18n.msg("eng.vegtext.running", "the game is already running for {name}", name=mod.name))
    game, cmd = command(mod)
    data = Path(mod.data)
    old = data / OUT_REL
    if old.is_file():
        # a decompiled file from an earlier run is not mistaken for this one's
        old.unlink()
    proc = popen(cmd, cwd=str(game))
    _RUNS[mod.name] = {"proc": proc, "started": time.time(), "data": data}
    log.info("VEG    %s: started %s", mod.name, " ".join(cmd))
    return {"running": True}


def status(mod) -> dict:
    """``running`` while the game is up; once it is gone, what :func:`finish`
    made of it (``{"done": ...}``)."""
    run = _RUNS.get(mod.name)
    if not run:
        return {"running": False, "idle": True}
    if run["proc"].poll() is None:
        return {"running": True, "since": int(time.time() - run["started"])}
    _RUNS.pop(mod.name, None)
    return {"running": False, "done": finish(mod)}


def finish(mod) -> dict:
    """Take the game's file: made the mod's ``descr_vegetation.txt`` with its
    caps line, or left beside the one the mod has."""
    data = Path(mod.data)
    out = data / OUT_REL
    if not out.is_file():
        return {"written": False, "error": _i18n.msg(
            "eng.vegtext.not_written",
            "the game wrote no {rel}; reach the main menu before quitting. Its system.log.txt says why",
            rel=OUT_REL)}
    target = data / TEXT_REL
    if target.is_file():
        return {"written": True, "kept": True, "path": str(out)}
    caps = data / modeltext.CAPS_REL
    caps_text = modeltext.caps_with_text(kb.read_text(caps, modeltext.ENCODING) if caps.is_file() else "", KEY)
    tid = config.new_transfer_id()
    backup_root = config.backup_root_for(tid)
    manifest: Dict[str, List[str]] = {"backed_up": [], "created": [TEXT_REL]}
    shutil.move(str(out), str(target))
    file_op("MOVE", target, f"from {OUT_REL}")
    if caps.is_file():
        bpath = backup_root / "data" / modeltext.CAPS_REL
        bpath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(caps, bpath)
        manifest["backed_up"].append(modeltext.CAPS_REL)
        file_op("BACKUP", caps, f"-> {bpath}")
    else:
        manifest["created"].append(modeltext.CAPS_REL)
    kb.write_text(caps, caps_text, modeltext.ENCODING)
    file_op("WRITE", caps, f"{KEY} text")
    rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "bmdb",
           "action": "vegetation to descr_vegetation.txt",
           "source": mod.name, "source_root": str(mod.root), "dest": mod.name, "dest_root": str(mod.root),
           "unit_type": "", "resolved_type": "", "options": {}, "applied": True, "undone": False, "note": "",
           "summary": _i18n.msg("eng.vegtext.converted", "{text} written by the game; {caps} says vegetation_source text",
                                text=TEXT_REL, caps=modeltext.CAPS_REL),
           "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
    config.append_log(rec)
    log.info("VEG    %s: %s written, id=%s", mod.name, TEXT_REL, tid)
    if hasattr(mod, "drop_caches"):
        mod.drop_caches()
    return {"written": True, "kept": False, "path": str(target), "id": tid}


def vegetation_text(mod) -> bool:
    """Does this mod read ``descr_vegetation.txt``? Its caps line decides.
    ``mod`` is a Mod or its folder, as for modeltext.reads_text."""
    data = getattr(mod, "data", None)
    caps = Path(data if data is not None else Path(mod) / "data") / modeltext.CAPS_REL
    if not caps.is_file():
        return False
    text = "\n".join(ln.split(";", 1)[0] for ln in
                     caps.read_text(encoding=modeltext.ENCODING, errors="replace").splitlines())
    import re
    hits = re.findall(r"^\s*" + KEY + r"\s+(\S+)", text, re.M | re.I)
    return bool(hits) and hits[-1].lower() == "text"
