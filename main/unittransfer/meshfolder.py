"""Battle models in a folder that is not a mod, for the viewer to draw.

Two kinds of folder are worth pointing the Models Editor at without installing
anything first:

* **a Blender export** - one folder per model, each holding ``<name>.mesh``,
  a ``textures/`` folder and sometimes ``<name>_bmdb.txt``, the entry written
  out ready to paste. That entry names its sheets where the finished mod will
  keep them (``unit_models/_units/reaper/textures/...``), not where they are
  now, so only the file NAME in it is any use here;
* **a copy-pasteable** ``data`` **folder** - ``unit_models/battle_models.modeldb``
  with the meshes and sheets it names, every path in it written from ``data/``
  as the game reads it rather than from the modeldb's own folder.

A folder is opened as a stand-in for a mod: :class:`FolderSource` carries the
``data``, ``modeldb`` and ``unit_models_dir`` the viewer's routes read, so an
entry is drawn by the same code a mod's is and a mesh no entry names goes
through :mod:`loosemesh`'s routes. Its ``data`` is the folder picked, and every
path an entry names is rewritten to where that file actually is under it - the
routes refuse anything outside it, exactly as they refuse anything outside a
mod's ``data``.

A mesh with no entry is offered skins guessed from its own folder. An export
holds one model per folder, so when its sheets are not named for the job the
first is taken as the main sheet and the second as the attachment, and the
viewer has a button to swap the two when that was the wrong way round.
"""
from __future__ import annotations

import os
import posixpath
import re
from pathlib import Path
from typing import Dict, List, Optional

from . import i18n as _i18n
from . import loosemesh, mesh, modeldb

#: what a folder's name is given as, in place of a mod's, on the model routes.
#: A mod's name is a folder name, and Windows allows no ``:`` in one.
PREFIX = "folder:"

#: how far a walk goes: a folder of exports is two deep, a ``data`` folder six,
#: and a slip of the picker onto ``C:\`` must not walk the whole drive
MAX_DEPTH = 8
MAX_FILES = 60000

#: the order a sheet saved three ways is taken in: the game reads ``.texture``
_SHEET_ORDER = (".texture", ".dds", ".tga")
#: ``xijun_n`` and ``mirk_heavy_norm2`` are normal maps too, which
#: :data:`loosemesh._NORMAL` does not say
_NORMAL_N = re.compile(r"(^|[_\-])(n|nm|nrm|norm|normal)\d*$", re.I)
_MAIN = re.compile(r"(^|[_\-])(main|body|diff|diffuse)([_\-.\d]|$)", re.I)


def _is_normal(stem: str) -> bool:
    return bool(loosemesh._NORMAL.search(stem) or _NORMAL_N.search(stem))


def _base(name: str) -> str:
    """A sheet's name with every sheet extension off: ``a.dds.texture`` -> ``a``."""
    s = name
    while True:
        low = s.lower()
        cut = next((x for x in _SHEET_ORDER + (".png",) if low.endswith(x)), "")
        if not cut:
            return s
        s = s[:-len(cut)]


class _NoDb:
    entries: list = []

    def by_name(self):
        return {}


class FolderSource:
    """A folder standing in for a mod, read only."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.name = PREFIX + str(self.root)
        self.data = self.root
        self.unit_models_dir = self.root
        self.notes: List[str] = []
        self.truncated = False
        self.files = self._walk()
        self.by_base: Dict[str, List[str]] = {}
        self.by_rel: Dict[str, str] = {}
        for p in self.files:
            r = self.rel(p)
            self.by_base.setdefault(p.name.lower(), []).append(r)
            self.by_rel[r.lower()] = r
        # loosemesh walks unit_models_dir itself on first use; this one is
        # walked already, within the limits above
        self.__dict__["_loosemesh"] = {"files": [
            p for p in self.files
            if p.suffix.lower() in loosemesh.TEXTURE_SUFFIXES + (".mesh",)]}
        self.modeldb = self._entries()

    # ---- reading the folder ------------------------------------------------
    def _walk(self) -> List[Path]:
        out: List[Path] = []
        base = len(self.root.parts)
        for dirpath, dirs, names in os.walk(self.root):
            depth = len(Path(dirpath).parts) - base
            dirs[:] = sorted(d for d in dirs if not d.startswith(".")) if depth < MAX_DEPTH else []
            for n in sorted(names):
                low = n.lower()
                if (low.endswith((".mesh", ".modeldb", "bmdb.txt", ".spr"))
                        or low.endswith(loosemesh.TEXTURE_SUFFIXES)):
                    out.append(Path(dirpath) / n)
            if len(out) > MAX_FILES:
                self.truncated = True
                break
        return out

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def locate(self, rel: str, heads: List[str]) -> Optional[str]:
        """Where a path an entry names really is under the folder, or ``None``.

        ``heads`` are folders as :meth:`_head` gives them. The path is tried as
        written from each of them first, then by its file name
        alone anywhere in the folder, nearest to the first base winning: an
        export's ``_bmdb.txt`` names the sheet where the mod will keep it.
        """
        rel = (rel or "").strip().replace("\\", "/")
        if not rel or rel == "0":
            return None
        if rel.lower().startswith("data/"):
            rel = rel[5:]
        # Looked up in the walk, as strings, rather than on disk or through
        # pathlib: a full mod's modeldb copied in with its data folder is a
        # thousand entries naming twenty thousand files, nearly all elsewhere.
        for h in heads:
            key = posixpath.normpath(f"{h}/{rel}" if h else rel).lower()
            if key in self.by_rel:
                return self.by_rel[key]
        hits = self.by_base.get(rel.rsplit("/", 1)[-1].lower(), [])
        if not hits:
            return None
        near = (heads[0] if heads else "").lower()

        def distance(r: str) -> int:
            low = r.lower()
            if not near or low.startswith(near + "/"):
                return low.count("/") - (near.count("/") + 1 if near else 0)
            return 100 + low.count("/")
        return min(hits, key=distance)

    def _heads(self, bases: List[Path]) -> List[str]:
        """``bases`` relative to the folder, as strings, any outside it left out."""
        out = []
        for b in bases:
            try:
                out.append(b.relative_to(self.root).as_posix().strip(".").strip("/"))
            except ValueError:
                continue
        return out

    def _place(self, e, bases: List[Path]) -> None:
        """Rewrite an entry's meshes and sheets to where they are in the folder.

        A path not found is left as written, so the viewer says "not in this
        folder" about the file the entry really names.
        """
        heads = self._heads(bases)
        e.lods = [(self.locate(m, heads) or m, d) for m, d in e.lods]
        for t in list(e.main_textures) + list(e.attach_textures):
            t.texture = self.locate(t.texture, heads) or t.texture
            t.normal = self.locate(t.normal, heads) or t.normal

    def _entries(self):
        dbs = [p for p in self.files if p.suffix.lower() == ".modeldb"]
        if not dbs:
            return _NoDb()
        out, seen = [], set()
        for p in dbs:
            try:
                db = modeldb.parse_file(p)
            except (ValueError, OSError) as e:
                self.notes.append(f"{self.rel(p)}: {e}")
                continue
            # its paths start from data/, which is the folder unit_models is in
            data = p.parent.parent if p.parent.name.lower() == "unit_models" else p.parent
            for e in db.entries:
                if e.name in seen:
                    continue
                seen.add(e.name)
                self._place(e, [data, self.root])
                out.append(e)
        db = _NoDb()
        db.entries = out
        db.by_name = lambda: {e.name: e for e in out}
        return db

    # ---- what the panel lists ----------------------------------------------
    def listing(self) -> dict:
        named = {loosemesh._norm(r) for e in self.modeldb.entries for r in e.mesh_files()}
        # A data folder made to be pasted into a mod often carries that mod's
        # whole modeldb for the few entries it adds, so only the entries whose
        # model is in the folder are listed, and the rest are counted.
        entries, elsewhere = [], 0
        for e in self.modeldb.entries:
            have = [m for m in e.mesh_files() if loosemesh._norm(m) in self.by_rel]
            if not have:
                elsewhere += 1
                continue
            entries.append({"name": e.name, "group": Path(have[0]).parent.as_posix(),
                            "lods": len(e.lods),
                            "skins": len(mesh.entry_view(e, self.root)["skins"])})
        meshes = []
        for p in self.files:
            if p.suffix.lower() != ".mesh":
                continue
            rel = self.rel(p)
            if loosemesh._norm(rel) in named:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            meshes.append({"rel": rel, "name": p.name,
                           "group": Path(rel).parent.as_posix() if "/" in rel else ".",
                           "bytes": size, "hint": "folder" if self.sheets(p.parent) else ""})
        meshes.sort(key=lambda m: (m["group"].lower(), m["name"].lower()))
        return {"mod": self.name, "root": str(self.root),
                "kind": "data" if self.modeldb.entries else "export",
                "entries": entries, "elsewhere": elsewhere,
                "meshes": meshes, "notes": self.notes,
                "truncated": self.truncated}

    # ---- a mesh with no entry ----------------------------------------------
    def sheets(self, folder: Path) -> List[Path]:
        """The skins a mesh's folder holds: ``textures/`` if it has one, else
        the folder itself. Normal maps out, and one file per sheet - an export
        often saves the same one as ``.texture``, ``.dds`` and ``.tga``."""
        tex = folder / "textures"
        where = tex if any(p.parent == tex for p in self.files) else folder
        best: Dict[str, Path] = {}
        for p in self.files:
            if p.parent != where or p.suffix.lower() not in _SHEET_ORDER:
                continue
            key = _base(p.name).lower()
            if _is_normal(_base(p.name)):
                continue
            have = best.get(key)
            if have is None or _SHEET_ORDER.index(p.suffix.lower()) < _SHEET_ORDER.index(have.suffix.lower()):
                best[key] = p
        return [best[k] for k in sorted(best)]

    def _bmdb_entry(self, src: Path):
        """The export's own ``_bmdb.txt`` beside ``src``, read, and its name."""
        stem = src.name[:-5] if src.name.lower().endswith(".mesh") else src.stem
        here = [p for p in self.files if p.parent == src.parent
                and p.name.lower().endswith("bmdb.txt")]
        mine = [p for p in here if p.name.lower() == f"{stem.lower()}_bmdb.txt"]
        pick = mine[0] if mine else (here[0] if len(here) == 1 else None)
        if pick is None:
            return None, ""
        try:
            e = modeldb.parse_entry(pick.read_text(encoding=modeldb.ENCODING))
        except (ValueError, OSError) as err:
            self.notes.append(f"{self.rel(pick)}: {err}")
            return None, ""
        return e, pick.name

    def _from_bmdb(self, src: Path) -> List[dict]:
        """The skins the export's own ``_bmdb.txt`` names, found by file name."""
        e, name = self._bmdb_entry(src)
        if e is None:
            return []
        self._place(e, [src.parent / "textures", src.parent])
        rows = [r for r in mesh.entry_view(e, self.root)["skins"] if r["exists"]]
        for r in rows:
            r["why"], r["entry"] = "bmdb", name
        return rows

    def skeleton_sets(self, rel: str, known: List[str]) -> dict:
        """The skeletons a mesh with no entry is animated by, and how they were found.

        The folder has no animations of its own: they are played out of a
        mod's packs, by skeleton name. The export's ``_bmdb.txt`` names its
        skeletons when there is one. Otherwise an export carries a ``.cas`` of
        each skeleton it was rigged to beside the mesh, named for it
        (``mtw2_swordsman.cas``), so a ``.cas`` whose name is a skeleton in
        ``known`` (the mod's pack) is taken as one. ``sets`` is shaped like an
        entry's, for :func:`unittransfer.animview.sets_view`.
        """
        src = self.root / rel
        e, name = self._bmdb_entry(src)
        if e is not None and e.animations:
            return {"why": "bmdb", "from": name, "sets": [
                {"mount": a.mount_type, "primary": a.primary_skeleton,
                 "secondary": a.secondary_skeleton,
                 "primary_weapons": list(a.pri_weapons),
                 "secondary_weapons": list(a.sec_weapons)} for a in e.animations]}
        by_low = {k.lower(): k for k in known}
        cas = [p for p in sorted(src.parent.iterdir(), key=lambda p: p.name.lower())
               if p.is_file() and p.suffix.lower() == ".cas"] if src.parent.is_dir() else []
        names = [by_low[p.stem.lower()] for p in cas if p.stem.lower() in by_low]
        if not names:
            return {"why": "", "from": "", "sets": []}
        return {"why": "cas", "from": ", ".join(p.name for p in cas if p.stem.lower() in by_low),
                "sets": [{"mount": "none", "primary": names[0],
                          "secondary": names[1] if len(names) > 1 else "",
                          "primary_weapons": [], "secondary_weapons": []}]}

    def _guess(self, src: Path) -> List[dict]:
        """Main and attachment sheets taken from the folder, best guess first."""
        found = self.sheets(src.parent)
        if not found:
            return []
        stem = loosemesh._stem(src.name)

        def rank(p: Path):
            b = _base(p.name).lower()
            return (not _MAIN.search(b), stem not in b, len(b), b)
        att = sorted((p for p in found if loosemesh._ATTACH.search(_base(p.name))), key=rank)
        main = sorted((p for p in found if p not in att), key=rank)
        if not main:
            main, att = att[:1], att[1:]
        if not att and len(main) == 2:
            # one model to a folder, so two sheets are its main and attachment
            # sheets; which is which is a guess, and the viewer can swap them
            main, att = main[:1], main[1:]
        row = lambda m, a, why: {"rel": self.rel(m), "exists": True,
                                 "attach": self.rel(a) if a else "",
                                 "attach_exists": a is not None,
                                 "factions": [], "why": why}
        if att:
            return [row(m, att[0], "pair") for m in main]
        return [row(m, None, "folder") for m in main]

    def view(self, rel: str) -> dict:
        """One mesh no entry names, as the viewer's picker needs it."""
        src = self.root / rel
        out: List[dict] = []
        seen = set()
        for r in self._from_bmdb(src) + self._guess(src):
            key = (r["rel"].lower(), (r.get("attach") or "").lower())
            if key not in seen:
                seen.add(key)
                out.append(r)
        return {"name": src.name, "scale": 1.0, "loose": rel,
                "lods": [{"index": 0, "rel": rel, "distance": 0, "exists": True}],
                "skins": out, "skeletons": []}


_OPEN: Dict[str, FolderSource] = {}


def open_folder(path: str, fresh: bool = False) -> FolderSource:
    """The folder at ``path`` as a source, read again when ``fresh``.

    Raises :class:`ValueError` with a sentence when it is not a folder.
    """
    raw = (path or "").strip().strip('"')
    if raw.startswith(PREFIX):
        raw = raw[len(PREFIX):]
    if not raw:
        raise ValueError(_i18n.msg("eng.meshfolder.no_folder_named", "no folder named"))
    p = Path(raw).expanduser()
    if not p.is_dir():
        raise ValueError(_i18n.msg("eng.meshfolder.is_not_a_folder", "{raw} is not a folder", raw=raw))
    key = str(p.resolve()).lower()
    if fresh or key not in _OPEN:
        _OPEN[key] = FolderSource(p)
    return _OPEN[key]


def is_folder(name: Optional[str]) -> bool:
    return bool(name) and name.startswith(PREFIX)
