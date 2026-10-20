"""What the script builder and the add-ons, ported from the Pfadfinder-Adam
(formerly MasterOogwayHomebrew) campaign editor, ask of their own editor,
answered from this toolkit (96e1).

:mod:`scriptdocs`, :mod:`scriptbuilder` and :mod:`scriptaddons` are that
editor's ``enginedocs.py``, ``modbuilder.py`` and ``addons.py``, taken with its
author's permission and kept close to the original so later versions can be
taken again. Every call they made into the rest of that editor comes here:
case-blind file lookup, the game folder, which game this is (always Medieval
II here), where the tool's reference files are, the mod's buildings, units,
towns, traits and text tables, and the ``Plan`` its writers fill.

A :class:`Plan` collects files to write and to delete, and notes; :meth:`run`
writes them as one job, each file backed up first and one record in the Log,
so Undo takes the whole job back - inside the mod's ``data/`` the usual way,
and a file in the game's ``script/modules`` with its own backup path.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config, gamepack
from . import i18n as _i18n
from .logutil import file_op, log

TEST_MARK = "// @put_in_by CE_Test - the editor's test mod (Add-ons > Scripts in the game takes it out)"


def _ci(folder, name):
    """``folder/name`` whatever its case, as a str, or None."""
    if not folder:
        return None
    p = os.path.join(folder, name)
    if os.path.exists(p):
        return p
    low = name.lower()
    try:
        for n in os.listdir(folder):
            if n.lower() == low:
                return os.path.join(folder, n)
    except OSError:
        return None
    return None


def ci_path(data, rel):
    cur = data
    for part in rel.replace("\\", "/").split("/"):
        cur = _ci(cur, part) if cur else None
    return cur


def game_of(data_dir) -> str:
    """The game folder a mod's data folder belongs to."""
    data = Path(data_dir)
    root = data.parent
    if root.parent.name.lower() == "mods":
        return str(root.parent.parent)
    got = gamepack.game_root_of(None)
    return str(got) if got else str(root)


def game_kind(mod) -> str:
    return "medieval2"


def reference_dir() -> str:
    return str(Path(__file__).resolve().parent / "data")


def tool_dir() -> Path:
    """The toolkit's own folder for the user's modules and add-ons."""
    d = Path(config.CONFIG_DIR) / "script_modules"
    d.mkdir(parents=True, exist_ok=True)
    return d


class _Named:
    def __init__(self, name, levels=()):
        self.name = name
        self.levels = list(levels)


def read_buildings(mod) -> List[_Named]:
    from . import buildings
    e = buildings.parse_file(Path(mod.data) / "export_descr_buildings.txt")
    out = []
    for b in e.buildings:
        out.append(_Named(b.name, [_Named(getattr(lv, "name", "")) for lv in b.levels]))
    return out


def read_units(mod):
    return list(mod.edu.units)


def towns(mod, campaign) -> List[Dict]:
    from . import campstrat
    try:
        sf = campstrat.read_strat(mod, campaign)
    except Exception:  # noqa: BLE001 - a campaign that will not read has no towns to offer
        return []
    return [{"name": s.get("region") or s.name, "region": s.get("region") or s.name}
            for s in sf.of_kind("settlement")]


def campaigns(mod) -> List[str]:
    from . import campfiles, campstrat
    try:
        got = campfiles.campaigns(mod)
    except Exception:  # noqa: BLE001
        got = []
    if campstrat.DEFAULT_CAMPAIGN in got:
        got = [campstrat.DEFAULT_CAMPAIGN] + [c for c in got if c != campstrat.DEFAULT_CAMPAIGN]
    return got


def trait_names(mod, kind: str) -> List[str]:
    """Trait or ancillary names of the mod."""
    try:
        if kind == "ancillaries":
            from . import ancillaries
            return [a["name"] for a in ancillaries.overview(mod).get("ancillaries", [])]
        from . import traits
        return [t["name"] for t in traits.overview(mod).get("traits", [])]
    except Exception:  # noqa: BLE001
        return []


def faction_names(mod) -> List[str]:
    from . import factions
    try:
        return factions.faction_slots(mod)
    except Exception:  # noqa: BLE001
        return []


class Plan:
    """Files to write and to delete, and the notes that say why."""

    def __init__(self, mod):
        self.mod = mod
        self.writes: Dict[str, bytes] = {}
        self.deletes: Dict[str, str] = {}
        self.notes: List[Tuple[Optional[str], str]] = []

    def binary(self, path, data: bytes) -> None:
        self.writes[os.path.abspath(path)] = bytes(data)
        self.deletes.pop(os.path.abspath(path), None)

    def delete(self, path, why: str = "") -> None:
        self.deletes[os.path.abspath(path)] = why
        self.writes.pop(os.path.abspath(path), None)

    def note(self, _file, text: str) -> None:
        self.notes.append((None, text))

    def stored(self, path) -> Optional[bytes]:
        p = os.path.abspath(path)
        if p in self.writes:
            return self.writes[p]
        try:
            return Path(p).read_bytes()
        except OSError:
            return None

    def words(self) -> List[str]:
        out = [t for _f, t in self.notes]
        out += [_i18n.msg("eng.scriptcompat.writes", "write {path}", path=self._show(p)) for p in self.writes]
        out += [_i18n.msg("eng.scriptcompat.deletes", "take out {path}{why}", path=self._show(p),
                          why=f" ({w})" if w else "") for p, w in self.deletes.items()]
        return out

    def _show(self, p: str) -> str:
        data = os.path.abspath(self.mod.data)
        game = os.path.abspath(game_of(self.mod.data))
        for base, tag in ((data, "data"), (game, "<game>")):
            if p.startswith(base + os.sep):
                return tag + "/" + os.path.relpath(p, base).replace("\\", "/")
        return p

    def run(self, action: str, who: str, summary: str) -> Dict:
        """Write it all, each file backed up first, as one job the Log can undo."""
        if not self.writes and not self.deletes:
            raise ValueError(_i18n.msg("eng.scriptcompat.nothing", "nothing to change"))
        mod = self.mod
        tid = config.new_transfer_id()
        backup_root = config.backup_root_for(tid)
        manifest: Dict[str, list] = {"backed_up": [], "created": [], "outside_backed_up": [],
                                     "outside_created": []}
        data = os.path.abspath(mod.data)
        n = 0

        def keep(path: str) -> None:
            nonlocal n
            inside = path.startswith(data + os.sep)
            if os.path.exists(path):
                if inside:
                    rel = os.path.relpath(path, data).replace("\\", "/")
                    b = backup_root / "data" / rel
                    manifest["backed_up"].append(rel)
                else:
                    n += 1
                    b = backup_root / "outside" / f"{n:03d}_{os.path.basename(path)}"
                    manifest["outside_backed_up"].append([path, str(b)])
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, b)
                file_op("BACKUP", Path(path), f"-> {b}")
            elif inside:
                manifest["created"].append(os.path.relpath(path, data).replace("\\", "/"))
            else:
                manifest["outside_created"].append(path)

        for path, raw in self.writes.items():
            keep(path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".new"
            with open(tmp, "xb") as fh:
                fh.write(raw)
            os.replace(tmp, path)
            file_op("WRITE", Path(path), action)
        for path in self.deletes:
            if os.path.exists(path):
                keep(path)
                os.remove(path)
                file_op("DELETE", Path(path), action)
        rec = {"id": tid, "when": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": "scripts",
               "action": action, "source": mod.name, "source_root": str(mod.root),
               "dest": mod.name, "dest_root": str(mod.root), "unit_type": who, "resolved_type": who,
               "options": {}, "applied": True, "undone": False, "note": "", "summary": summary,
               "warnings": [], "manifest": manifest, "backup_root": str(backup_root)}
        config.append_log(rec)
        log.info("SCRIPTS %s %s in %s, id=%s", action, who, mod.name, tid)
        return rec
