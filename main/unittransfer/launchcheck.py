"""Will this mod even launch? A readiness row for the Home card (Phase 58).

Home says what each mod is ready for inside the toolkit. This says whether the
GAME will start it, from the same files the game and its launchers read, and
nothing is written. Every rule is one a real mod or the TWCenter archive
states, and each finding names the file it came from:

* **A way to start it.** Measured on the two installed mods, there are two:
  a ``.bat`` in the mod folder that goes to the game folder and starts an
  executable with ``@<its .cfg>`` (ROCSS's ``ROCSS.bat``:
  ``cd ..\\..`` then ``start medieval2.exe @%0\\.\\Configuration.cfg``), and the
  M2TWEOP launcher, ``M2TWEOP_GUI.exe``, whose ``eopData/config/uiCfg.json``
  names the ``.cfg`` in ``modCfgFile`` (DaC: ``TATW.cfg``). A mod with
  neither is looked at through any ``.cfg`` in its folder that has a
  ``[features] mod =`` line - what a shortcut would pass.
* **The .cfg points at this folder.** ``[features] mod = mods/<folder>``,
  compared case-blind the way Windows opens it. DaC's own README: "make sure
  the folder structure is correct and the config file has the right folder
  name". A cfg naming another folder starts another mod.
* **``[io] file_first``** - ROCSS's cfg says what it does: "look up sequence
  of files: mod, main game, packs". Without it a mod's loose files lose to the
  packs. A warning, not a fault: a mod can ship everything packed.
* **The executable is there**, in the game folder the ``.bat`` changes to.
* **Large Address Aware.** DaC ships ``LAA.txt`` and a patcher, ROCSS ships
  ``4gb_patch.exe``; both exist because a big mod runs out of a 32-bit
  process's 2 GB. The flag is one bit in the executable's PE header
  (``IMAGE_FILE_LARGE_ADDRESS_AWARE``, 0x20), read here and never set.
* **The launcher's registry entry**, told and never judged: the archive's
  *Registry Entries for the Launcher* says those entries serve the disk
  version's launcher and "does not work anymore with Steam".
"""
from __future__ import annotations

import configparser
import json
import re
import struct
from pathlib import Path
from typing import Dict, List, Optional

GAME_EXES = ("M2EX.exe", "kingdoms.exe", "medieval2.exe")


def _read_cfg(path: Path) -> Dict[str, Dict[str, str]]:
    """A game ``.cfg`` as ``{section: {key: value}}``, lower-cased, with the
    game's comments (``;`` and ``#``, also after a value) taken off."""
    out: Dict[str, Dict[str, str]] = {}
    sec = ""
    try:
        text = path.read_bytes().decode("latin-1")
    except OSError:
        return out
    for line in text.splitlines():
        line = re.split(r"[;#]", line, 1)[0].strip()
        if not line:
            continue
        m = re.match(r"^\[([^\]]+)\]$", line)
        if m:
            sec = m.group(1).strip().lower()
            out.setdefault(sec, {})
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            out.setdefault(sec, {})[k.strip().lower()] = v.strip()
    return out


def large_address_aware(exe: Path) -> Optional[bool]:
    """The PE header's LARGE_ADDRESS_AWARE bit, or None if it is not a PE."""
    try:
        with open(exe, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return None
    if head[:2] != b"MZ" or len(head) < 64:
        return None
    pe, = struct.unpack_from("<I", head, 0x3C)
    if pe + 24 > len(head) or head[pe:pe + 4] != b"PE\0\0":
        return None
    chars, = struct.unpack_from("<H", head, pe + 22)
    return bool(chars & 0x20)


def _find(folder: Path, name: str) -> Optional[Path]:
    """``name`` in ``folder``, case-blind, the way Windows finds it."""
    try:
        return next((p for p in folder.iterdir() if p.name.lower() == name.lower()), None)
    except OSError:
        return None


def _bat_routes(root: Path, game: Path) -> List[dict]:
    """``start <exe> @<cfg>`` in each .bat of the mod folder: one route a
    .bat. ROCSS.bat tries ``M2EX.exe`` and falls back to ``medieval2.exe``
    (``IF EXIST ... ELSE``), so the executables are kept in the order the file
    tries them and :func:`check` takes the first one that is there."""
    out = []
    for bat in sorted(root.glob("*.bat")):
        try:
            text = bat.read_bytes().decode("latin-1")
        except OSError:
            continue
        exes, cfgs = [], []
        # the cfg stops at a `)`: ROCSS.bat closes its IF block right after it
        for m in re.finditer(r"start\s+(?:\"[^\"]*\"\s+)?([\w.\-]+\.exe)\s+@([^\s)]+)", text, re.I):
            exe, arg = m.group(1), m.group(2).strip('"')
            # `%0\..\X` and `%0\.\X` both mean "beside this .bat"
            cfg_name = re.sub(r"^%0\\\.{1,2}\\", "", arg).replace("\\", "/").split("/")[-1]
            if exe not in exes:
                exes.append(exe)
            if cfg_name not in cfgs:
                cfgs.append(cfg_name)
        if exes:
            out.append({"how": bat.name, "kind": "bat", "exe": exes[0], "exes": exes,
                        "cfg": cfgs[0]})
    return out


def _eop_route(root: Path) -> Optional[dict]:
    if not _find(root, "M2TWEOP_GUI.exe"):
        return None
    ui = root / "eopData" / "config" / "uiCfg.json"
    cfg = ""
    try:
        data = json.loads(ui.read_text(encoding="utf-8", errors="replace"))
        cfg = "" if data.get("useVanillaCfg") else str(data.get("modCfgFile") or "")
    except (OSError, ValueError):
        pass
    return {"how": "M2TWEOP_GUI.exe", "kind": "eop", "exe": "", "cfg": cfg,
            "cfg_from": "eopData/config/uiCfg.json"}


def check(mod) -> dict:
    """Every way this mod can be started, and what is wrong with each."""
    root = Path(mod.root)
    game = root.parent.parent
    routes = _bat_routes(root, game)
    eop = _eop_route(root)
    if eop:
        routes.append(eop)
    if not routes:
        for cfg in sorted(root.glob("*.cfg")):
            if "mod" in _read_cfg(cfg).get("features", {}):
                routes.append({"how": cfg.name, "kind": "cfg", "exe": "", "cfg": cfg.name})
    exes = {e: _find(game, e) for e in GAME_EXES}
    rows: List[dict] = []
    for r in routes:
        faults, warns, notes = [], [], []
        cfg_path = _find(root, r["cfg"]) if r["cfg"] else None
        if not r["cfg"]:
            faults.append(f"{r.get('cfg_from', r['how'])} names no .cfg to start with")
        elif cfg_path is None:
            faults.append(f"it starts with {r['cfg']}, and there is no such file in the mod folder")
        else:
            cfg = _read_cfg(cfg_path)
            want = f"mods/{root.name}".lower()
            named = cfg.get("features", {}).get("mod", "")
            if not named:
                faults.append(f"{cfg_path.name} has no [features] mod = line, so the game "
                              f"starts unmodded")
            elif named.replace("\\", "/").strip().strip("/").lower() != want:
                faults.append(f"{cfg_path.name} says mod = {named}, and this mod is "
                              f"mods/{root.name}")
            ff = cfg.get("io", {}).get("file_first", "")
            if ff.lower() not in ("1", "true", "yes", "on"):
                warns.append(f"{cfg_path.name} does not set [io] file_first, so the mod's "
                             f"loose files lose to the packs")
        exe_path = None
        if r["kind"] == "bat":
            tried = [(e, _find(game, e)) for e in r["exes"]]
            exe_path = next((p for _e, p in tried if p), None)
            if exe_path is None:
                faults.append(f"it starts {' or '.join(r['exes'])}, and the game folder has "
                              f"{'neither' if len(tried) > 1 else 'no such file'}")
            elif tried[0][1] is None:
                notes.append(f"it tries {tried[0][0]} first, which is not here, and starts "
                             f"{exe_path.name}")
        else:
            exe_path = exes.get("medieval2.exe") or exes.get("kingdoms.exe")
            if exe_path is None:
                faults.append("neither medieval2.exe nor kingdoms.exe is in the game folder")
        laa = large_address_aware(exe_path) if exe_path else None
        if laa is False:
            warns.append(f"{exe_path.name} is not Large Address Aware, so the game has 2 GB "
                         f"and a big mod runs out of it")
        rows.append({"how": r["how"], "kind": r["kind"], "cfg": r["cfg"],
                     "exe": exe_path.name if exe_path else r["exe"], "laa": laa,
                     "faults": faults, "warnings": warns, "notes": notes,
                     "ok": not faults})
    registry = _registry(root.name)
    verdict = ("none" if not rows else "ready" if any(r["ok"] and not r["warnings"] for r in rows)
               else "warn" if any(r["ok"] for r in rows) else "broken")
    return {"verdict": verdict, "routes": rows, "game": str(game),
            "exes": {e: bool(p) for e, p in exes.items()}, "registry": registry}


def _registry(folder: str) -> dict:
    """The disk launcher's entry for this mod, if any - read, never written.
    Only the disk version's launcher reads it (the archive's tutorial)."""
    try:
        import winreg
    except ImportError:
        return {"read": False, "entry": ""}
    for base in (r"SOFTWARE\WOW6432Node\SEGA\Medieval II Total War\Mods\Unofficial",
                 r"SOFTWARE\SEGA\Medieval II Total War\Mods\Unofficial"):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        except OSError:
            continue
        with key:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(key, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(key, sub) as k:
                        path, _ = winreg.QueryValueEx(k, "Path")
                except OSError:
                    continue
                if str(path).replace("\\", "/").strip("/").lower() == f"mods/{folder}".lower():
                    return {"read": True, "entry": sub}
        return {"read": True, "entry": ""}
    return {"read": True, "entry": ""}
