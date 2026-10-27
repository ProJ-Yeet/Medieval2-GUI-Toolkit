"""Armory Studio, the kitbash workbench in the Models Editor (Phase 95e on).

A port of the behaviour of Armory Studio 3D (``Reference/armorystudio3d/``,
MIT, by muhamadridhomm) onto this toolkit's own readers and writers; none of
its code or art is carried over (ROADMAP, Phase 95).

The workbench builds one model out of parts of others. A part is an
**object**: one group of a source model (``Body``/``horse_body_01``), or one
object of an external file. The models the parts come out of are **assets**,
loaded from any installed mod - a model entry, the models of a unit - or from
a ``.obj``, ``.glb`` or ``.dae`` on disk. Nothing is copied while you work:
an object is its source and the changes made to it, and the export (95i)
reads each source again.

This module is the server side of the assets panel:

* :func:`catalogue` - what a mod offers to import, light enough to list;
* :func:`asset_view` - one model entry as an asset: its objects, skins,
  bones and skeletons, with a fingerprint per object;
* :func:`read_external` - an ``.obj``, ``.glb`` or ``.dae`` read into a
  :class:`~unittransfer.mesh.MeshFile` in the game's space, and
  :func:`external_view`, the same asset shape for it.

**Duplicate detection** is by fingerprint, a hash of an object's triangles
as positions, and by shape, its triangle count, centre and spread compared
with a tolerance, so the same art copied into another mod, loaded twice or
gone through an ``.obj`` is told apart from a part that merely shares a name.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import re
import struct
import threading
import time
import xml.etree.ElementTree as ET
from array import array
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import config, gamepack, mesh
from . import i18n as _i18n

#: The image types an external model's textures may be in.
IMAGE_SUFFIXES = (".png", ".tga", ".dds", ".jpg", ".jpeg", ".texture", ".bmp")
#: The model files an external asset may be.
EXTERNAL_SUFFIXES = (".obj", ".glb", ".gltf", ".dae", ".mesh")

#: Where the workbench keeps its project and what it unpacks out of a .glb.
ARMORY_DIR = config.CONFIG_DIR / "armory"


class ArmoryError(ValueError):
    """Something the workbench cannot do, said as a sentence."""


# ---------------------------------------------------------------------------
# names


#: ``prefix__part`` with ``__opt`` for an optional part: the Blender kit's
#: object names, which is also how IWTE joins a group's type and mesh name.
_KIT_NAME = re.compile(r"^(?P<type>.+?)__(?P<mesh>.+?)(?:__(?P<opt>opt))?(?:\.\d{3})?$", re.I)


def split_name(name: str) -> Tuple[str, str, int]:
    """``(group type, mesh name, flag)`` out of an object's name.

    ``Body__horse_body_01__opt`` is type ``Body``, mesh ``horse_body_01``,
    optional. A name not in the kit's form is its own type and mesh, required.
    """
    m = _KIT_NAME.match(name.strip())
    if m:
        return m.group("type"), m.group("mesh"), 1 if m.group("opt") else 0
    clean = re.sub(r"\.\d{3}$", "", name.strip()) or "part"
    return clean, clean, 0


# ---------------------------------------------------------------------------
# fingerprints


def fingerprint(m: mesh.MeshFile, indices: Sequence[int]) -> str:
    """A hash of one object's triangles as positions, to a tenth of a millimetre.

    By position and not by index, so the same art in another file with its
    vertices in another order still matches as long as its triangles run the
    same way; rounded, so a copy that went through a float conversion does.
    """
    p = m.positions
    h = hashlib.blake2b(digest_size=10)
    buf = array("i")
    for i in indices:
        buf.extend((round(p[i * 3] * 10000), round(p[i * 3 + 1] * 10000),
                    round(p[i * 3 + 2] * 10000)))
        if len(buf) > 30000:
            h.update(buf.tobytes())
            buf = array("i")
    h.update(buf.tobytes())
    return h.hexdigest()


def shape(m: mesh.MeshFile, indices: Sequence[int]) -> List[float]:
    """``[triangles, centre x, y, z, spread]`` of one object, compared with a
    tolerance by the page: a copy whose floats went through six decimals in
    an ``.obj`` lands on the other side of a rounding step often enough that
    :func:`fingerprint` alone misses it."""
    p = m.positions
    n = len(indices)
    if not n:
        return [0, 0.0, 0.0, 0.0, 0.0]
    c = [sum(p[i * 3 + k] for i in indices) / n for k in range(3)]
    spread = (sum((p[i * 3] - c[0]) ** 2 + (p[i * 3 + 1] - c[1]) ** 2 + (p[i * 3 + 2] - c[2]) ** 2
                  for i in indices) / n) ** 0.5
    return [n // 3, round(c[0], 5), round(c[1], 5), round(c[2], 5), round(spread, 5)]


def file_hash(data: bytes) -> str:
    return hashlib.blake2b(data, digest_size=10).hexdigest()


# ---------------------------------------------------------------------------
# what a mod offers


def catalogue(mod) -> dict:
    """Every model entry and every unit with a soldier model, for the import list.

    A row per entry is its name, its LOD count and where its first LOD lives;
    a row per unit names the models it uses, each tagged with the slot
    (soldier, officer, upgrade) so the picker can offer them by role.
    """
    entries = []
    seen = set()
    for e in mod.modeldb.entries:
        k = e.name.lower()
        if k in seen:
            continue
        seen.add(k)
        entries.append({"name": e.name, "lods": len(e.lods),
                        "mesh": (e.lods[0][0] if e.lods else "").replace("\\", "/"),
                        "skeletons": e.skeletons()[:2]})
    known = {e["name"].lower() for e in entries}
    # 100j: the import dialog filters by faction and culture
    try:
        cultures = mod.faction_cultures or {}
    except Exception:
        cultures = {}
    units = []
    for u in mod.edu.units:
        if not u.soldier_model:
            continue
        models = [{"name": u.soldier_model.lower(), "role": "soldier"}]
        models += [{"name": o.lower(), "role": "officer", "n": i + 1}
                   for i, o in enumerate(u.officers)]
        models += [{"name": a.lower(), "role": "upgrade", "n": i + 1}
                   for i, a in enumerate(u.armour_ug_models)]
        for row in models:
            row["missing"] = row["name"] not in known
        units.append({"type": u.type, "category": (u.category or "").lower(),
                      "class": (getattr(u, "class_type", "") or "").lower(),
                      "mount": u.mount or "", "models": models,
                      "factions": list(u.ownership),
                      "cultures": sorted({cultures[f] for f in u.ownership if cultures.get(f)})})
    return {"mod": mod.name, "entries": entries, "units": units}


def _read_entry_mesh(mod, entry, lod: int = 0) -> Tuple[mesh.MeshFile, str]:
    if not entry.lods:
        raise ArmoryError(_i18n.msg("eng.armory.entry_has_no_lods", "{name} names no model file", name=entry.name))
    rel = entry.lods[min(lod, len(entry.lods) - 1)][0].replace("\\", "/").strip()
    path, _where = gamepack.lookup(rel, mod)
    if path is None or not path.is_file():
        raise ArmoryError(_i18n.msg("eng.armory.mesh_not_found", "{rel} is in neither the mod, the game nor its packs", rel=rel))
    try:
        return mesh.read_mesh(path), file_hash(path.read_bytes())
    except mesh.MeshError as e:
        raise ArmoryError(str(e)) from e


def _objects(m: mesh.MeshFile) -> List[dict]:
    out = []
    for i, g in enumerate(m.groups):
        out.append({"index": i, "name": g.name, "mesh": g.texture_group,
                    "flag": g.flag, "triangles": g.triangles, "sheets": g.sheets,
                    "texture": g.texture,
                    "fingerprint": fingerprint(m, g.indices),
                    "shape": shape(m, g.indices)})
    return out


def asset_view(mod, name: str) -> dict:
    """One model entry as an asset: its first LOD's objects, skins and bones."""
    entry = mod.modeldb.by_name().get((name or "").lower())
    if entry is None:
        raise ArmoryError(_i18n.msg("eng.armory.no_such_entry", "{mod} has no model entry {name}", mod=mod.name, name=name))
    m, digest = _read_entry_mesh(mod, entry)
    view = mesh.entry_view(entry, mod.data, mod)
    return {"kind": "entry", "mod": mod.name, "entry": entry.name,
            "mesh": view["lods"][0]["rel"] if view["lods"] else "",
            "lods": len(entry.lods), "file_hash": digest,
            "skins": view["skins"], "skeletons": entry.skeletons(),
            "bones": m.bones, "vertices": m.vertices, "triangles": m.triangles,
            "objects": _objects(m)}


# ---------------------------------------------------------------------------
# external models


class _Builder:
    """Collects objects into one vertex pool in the game's space.

    Every external format is right-handed with Y up, and the game is
    left-handed (``mesh.py``), so x is negated and each triangle's winding
    reversed, the inverse of what ``modelexport`` does on the way out.
    """

    def __init__(self, source: str):
        self.m = mesh.MeshFile(source=source, format="mesh")
        self.weights = array("f")
        self.ids = bytearray()
        self.skinned = False
        self.object_textures: List[str] = []

    def add(self, name: str, pos, nrm, uv, tris, texture: str = "",
            joints=None, weights=None, bone_names: Sequence[str] = ()):
        # an object takes only the vertices its own triangles use: a .glb's
        # primitives can all share one pool (this toolkit's exporter does)
        used = sorted({i for t in tris for i in t})
        if len(used) < len(pos):
            remap = {old: new for new, old in enumerate(used)}
            pick = lambda seq: [seq[i] for i in used] if seq is not None else None
            pos, nrm, uv = pick(pos), pick(nrm), pick(uv)
            joints, weights = pick(joints), pick(weights)
            tris = [(remap[a], remap[b], remap[c]) for a, b, c in tris]
        base = self.m.vertices
        n = len(pos)
        for x, y, z in pos:
            self.m.positions.extend((-x, y, z))
        for i in range(n):
            if nrm:
                x, y, z = nrm[i]
                self.m.normals.extend((-x, y, z))
            else:
                self.m.normals.extend((0.0, 1.0, 0.0))
            if uv:
                self.m.uvs.extend(uv[i])
            else:
                self.m.uvs.extend((0.0, 0.0))
        if joints is not None and bone_names:
            self.skinned = True
            for i in range(n):
                pairs = sorted(zip(weights[i], joints[i]), reverse=True)[:2]
                while len(pairs) < 2:
                    pairs.append((0.0, 0))
                total = pairs[0][0] + pairs[1][0] or 1.0
                ids = []
                for w, j in pairs:
                    bone = bone_names[j] if j < len(bone_names) else ""
                    if bone not in self.m.bones:
                        self.m.bones.append(bone)
                    ids.append(self.m.bones.index(bone))
                    self.weights.append(w / total)
                # the file's packing: the first weight's bone in the THIRD
                # byte, the second's in the second (mesh.geometry_payload)
                self.ids += bytes((0, ids[1], ids[0], 0))
        else:
            for _ in range(n):
                self.weights.extend((1.0, 0.0))
                self.ids += bytes(4)
        idx = array("H")
        for a, b, c in tris:
            idx.extend((a + base, c + base, b + base))
        gtype, gmesh, flag = split_name(name)
        self.m.groups.append(mesh.MeshGroup(gtype, gmesh, idx, flag, texture=texture))

    def done(self) -> mesh.MeshFile:
        if self.m.vertices > 0xFFFF + 1:
            raise ArmoryError(_i18n.msg("eng.armory.too_many_vertices", "{n:,} vertices: a .mesh indexes at most 65,536", n=self.m.vertices))
        if not self.m.groups:
            raise ArmoryError(_i18n.msg("eng.armory.no_objects", "no geometry in this file"))
        if self.skinned:
            self.m.weights = self.weights
            self.m.bone_ids = bytes(self.ids)
        self.m.textures = sorted({g.texture for g in self.m.groups if g.texture})
        mesh._classify_sheets(self.m)
        return self.m


def _fan(face: Sequence[int]) -> List[Tuple[int, int, int]]:
    return [(face[0], face[i], face[i + 1]) for i in range(1, len(face) - 1)]


def _read_obj(path: Path) -> mesh.MeshFile:
    """An ``.obj``: ``o``/``g`` start an object, ``usemtl`` names its material,
    ``map_Kd`` in the ``.mtl`` its texture. ``v`` counts from the bottom of an
    image in OBJ and from the top in the game, so it is flipped."""
    text = path.read_text(encoding="utf-8", errors="replace")
    vs, vts, vns = [], [], []
    materials: Dict[str, str] = {}
    objects: List[dict] = []
    cur = None

    def start(name):
        nonlocal cur
        cur = {"name": name, "faces": [], "mtl": cur["mtl"] if cur else ""}
        objects.append(cur)

    for raw in text.splitlines():
        parts = raw.split()
        if not parts or parts[0].startswith("#"):
            continue
        tag = parts[0]
        if tag == "v":
            vs.append(tuple(float(x) for x in parts[1:4]))
        elif tag == "vt":
            vts.append((float(parts[1]), 1.0 - float(parts[2]) if len(parts) > 2 else 0.0))
        elif tag == "vn":
            vns.append(tuple(float(x) for x in parts[1:4]))
        elif tag in ("o", "g"):
            name = " ".join(parts[1:]) or "part"
            if cur is None or cur["faces"] or tag == "o":
                start(name)
            else:
                cur["name"] = name
        elif tag == "usemtl":
            if cur is None:
                start(path.stem)
            if cur["faces"]:
                start(cur["name"])
            cur["mtl"] = " ".join(parts[1:])
        elif tag == "mtllib":
            mtl = path.parent / " ".join(parts[1:])
            if mtl.is_file():
                name = ""
                for line in mtl.read_text(encoding="utf-8", errors="replace").splitlines():
                    bits = line.split()
                    if not bits:
                        continue
                    if bits[0] == "newmtl":
                        name = " ".join(bits[1:])
                    elif bits[0].lower() == "map_kd" and name:
                        # a file name may hold spaces; options (-s 1 1 1) come first
                        rest = line.strip().split(None, 1)[1] if len(bits) > 1 else ""
                        materials[name] = rest if rest and not rest.startswith("-") else bits[-1]
        elif tag == "f":
            if cur is None:
                start(path.stem)
            cur["faces"].append([tuple(int(x) if x else 0 for x in (c.split("/") + ["", ""])[:3])
                                 for c in parts[1:]])
    b = _Builder(str(path))
    for ob in objects:
        if not ob["faces"]:
            continue
        key: Dict[tuple, int] = {}
        pos, nrm, uv, tris = [], [], [], []
        for face in ob["faces"]:
            ids = []
            for vi, ti, ni in face:
                k = (vi, ti, ni)
                if k not in key:
                    key[k] = len(pos)
                    pos.append(vs[vi - 1 if vi > 0 else vi])
                    uv.append(vts[ti - 1 if ti > 0 else ti] if ti else (0.0, 0.0))
                    nrm.append(vns[ni - 1 if ni > 0 else ni] if ni else (0.0, 1.0, 0.0))
                ids.append(key[k])
            tris += _fan(ids)
        b.add(ob["name"], pos, nrm if vns else None, uv, tris,
              texture=materials.get(ob["mtl"], ""))
    return b.done()


_GL_TYPES = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
_GL_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _read_gltf(path: Path) -> Tuple[mesh.MeshFile, Dict[str, bytes]]:
    """A ``.glb`` or ``.gltf``: one object per primitive, named for its node.

    Images packed inside the file come back as bytes by name, to be unpacked
    beside the project; ``v`` counts from the top in glTF as in the game.
    """
    data = path.read_bytes()
    buffers: List[bytes] = []
    if data[:4] == b"glTF":
        from .modelexport import read_glb
        gltf, binary = read_glb(data)
        buffers = [binary]
    else:
        gltf = json.loads(data.decode("utf-8"))
        for buf in gltf.get("buffers", []):
            uri = buf.get("uri", "")
            if uri.startswith("data:"):
                buffers.append(base64.b64decode(uri.split(",", 1)[1]))
            else:
                buffers.append((path.parent / uri).read_bytes())

    def view_bytes(vi: int) -> bytes:
        v = gltf["bufferViews"][vi]
        start = v.get("byteOffset", 0)
        return buffers[v.get("buffer", 0)][start:start + v["byteLength"]]

    def accessor(ai: int) -> List[tuple]:
        a = gltf["accessors"][ai]
        fmt = _GL_TYPES[a["componentType"]]
        width = _GL_WIDTH[a["type"]]
        v = gltf["bufferViews"][a["bufferView"]]
        raw = view_bytes(a["bufferView"])
        size = struct.calcsize(fmt)
        stride = v.get("byteStride") or size * width
        off = a.get("byteOffset", 0)
        out = []
        for i in range(a["count"]):
            vals = struct.unpack_from(f"<{width}{fmt}", raw, off + i * stride)
            if a.get("normalized") and fmt != "f":
                top = float(2 ** (8 * size) - 1 if fmt.isupper() else 2 ** (8 * size - 1) - 1)
                vals = tuple(x / top for x in vals)
            out.append(vals)
        return out

    images: Dict[str, bytes] = {}
    names: List[str] = []
    for i, img in enumerate(gltf.get("images", [])):
        name = img.get("name") or f"image_{i}"
        ext = ".png" if "png" in img.get("mimeType", "png") else ".jpg"
        if "bufferView" in img:
            images[name + ext] = view_bytes(img["bufferView"])
            names.append(name + ext)
        else:
            uri = img.get("uri", "")
            if uri.startswith("data:"):
                images[name + ext] = base64.b64decode(uri.split(",", 1)[1])
                names.append(name + ext)
            else:
                names.append(uri)

    def material_texture(mi) -> str:
        if mi is None:
            return ""
        mat = gltf.get("materials", [])[mi]
        tex = (mat.get("pbrMetallicRoughness", {}).get("baseColorTexture") or {}).get("index")
        if tex is None:
            return ""
        src = gltf.get("textures", [])[tex].get("source")
        return names[src] if src is not None and src < len(names) else ""

    b = _Builder(str(path))
    nodes = gltf.get("nodes", [])
    for node in nodes:
        if "mesh" not in node:
            continue
        gm = gltf["meshes"][node["mesh"]]
        skin = gltf.get("skins", [])[node["skin"]] if "skin" in node else None
        bone_names = [nodes[j].get("name", f"bone_{j}") for j in skin["joints"]] if skin else []
        prims = gm.get("primitives", [])
        for pi, prim in enumerate(prims):
            at = prim["attributes"]
            pos = accessor(at["POSITION"])
            nrm = accessor(at["NORMAL"]) if "NORMAL" in at else None
            uv = accessor(at["TEXCOORD_0"]) if "TEXCOORD_0" in at else None
            if "indices" in prim:
                flat = [i[0] for i in accessor(prim["indices"])]
            else:
                flat = list(range(len(pos)))
            tris = [tuple(flat[i:i + 3]) for i in range(0, len(flat) - 2, 3)]
            joints = accessor(at["JOINTS_0"]) if skin and "JOINTS_0" in at else None
            weights = accessor(at["WEIGHTS_0"]) if joints is not None and "WEIGHTS_0" in at else None
            name = node.get("name") or gm.get("name") or "part"
            if len(prims) > 1:
                name = f"{name}_{pi + 1}"
            b.add(name, pos, nrm, uv, tris, texture=material_texture(prim.get("material")),
                  joints=joints, weights=weights, bone_names=bone_names)
    return b.done(), images


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read_dae(path: Path) -> mesh.MeshFile:
    """A COLLADA ``.dae``: one object per ``<triangles>``/``<polylist>``
    block, named for its geometry, with the skin's two strongest weights a
    vertex where a controller binds one. A ``Z_UP`` file (Blender's default)
    is turned to Y up first."""
    root = ET.parse(path).getroot()
    find = lambda el, name: [c for c in el.iter() if _local(c.tag) == name]
    z_up = any((u.text or "").strip().upper() == "Z_UP" for u in find(root, "up_axis"))

    def turn(v):
        return (v[0], v[2], -v[1]) if z_up else v

    images = {img.get("id"): next((t.text or "" for t in img.iter() if _local(t.tag) == "init_from"), "")
              for img in find(root, "image")}
    # effect -> image, through the sampler's surface the way Blender writes it
    effect_image: Dict[str, str] = {}
    for eff in find(root, "effect"):
        for t in eff.iter():
            if _local(t.tag) == "init_from" and (t.text or "").strip() in images:
                effect_image[eff.get("id")] = images[(t.text or "").strip()]
                break
            if _local(t.tag) == "texture" and t.get("texture") in images:
                effect_image[eff.get("id")] = images[t.get("texture")]
                break
    material_image: Dict[str, str] = {}
    for mat in find(root, "material"):
        for t in mat.iter():
            if _local(t.tag) == "instance_effect":
                material_image[mat.get("id")] = effect_image.get(t.get("url", "").lstrip("#"), "")
    # the symbol a <triangles material=...> names is bound to a material in the scene
    symbol: Dict[str, str] = {}
    for im in find(root, "instance_material"):
        symbol[im.get("symbol")] = material_image.get(im.get("target", "").lstrip("#"), "")

    skins: Dict[str, Tuple[List[str], List[List[Tuple[int, float]]]]] = {}
    for ctl in find(root, "skin"):
        sources = {s.get("id"): s for s in ctl if _local(s.tag) == "source"}
        joints_src = weights_src = None
        for inp in [c for c in ctl.iter() if _local(c.tag) == "input"]:
            if inp.get("semantic") == "JOINT":
                joints_src = sources.get(inp.get("source", "").lstrip("#"))
            if inp.get("semantic") == "WEIGHT":
                weights_src = sources.get(inp.get("source", "").lstrip("#"))
        if joints_src is None or weights_src is None:
            continue
        names = next((t.text or "" for t in joints_src.iter() if _local(t.tag) == "Name_array"), "").split()
        wts = [float(x) for x in next((t.text or "" for t in weights_src.iter() if _local(t.tag) == "float_array"), "").split()]
        vw = next((c for c in ctl if _local(c.tag) == "vertex_weights"), None)
        if vw is None:
            continue
        vcount = [int(x) for x in next((t.text or "" for t in vw if _local(t.tag) == "vcount"), "").split()]
        v = [int(x) for x in next((t.text or "" for t in vw if _local(t.tag) == "v"), "").split()]
        per, at = [], 0
        for c in vcount:
            per.append([(v[at + 2 * k], wts[v[at + 2 * k + 1]]) for k in range(c)])
            at += 2 * c
        skins[ctl.get("source", "").lstrip("#")] = (names, per)

    b = _Builder(str(path))
    for geo in find(root, "geometry"):
        gm = next((c for c in geo if _local(c.tag) == "mesh"), None)
        if gm is None:
            continue
        arrays: Dict[str, Tuple[List[float], int]] = {}
        for src in [c for c in gm if _local(c.tag) == "source"]:
            fa = next((t for t in src.iter() if _local(t.tag) == "float_array"), None)
            acc = next((t for t in src.iter() if _local(t.tag) == "accessor"), None)
            if fa is not None:
                arrays[src.get("id")] = ([float(x) for x in (fa.text or "").split()],
                                         int(acc.get("stride", 3)) if acc is not None else 3)
        vert_src = {}
        for vt in [c for c in gm if _local(c.tag) == "vertices"]:
            for inp in vt:
                if _local(inp.tag) == "input" and inp.get("semantic") == "POSITION":
                    vert_src[vt.get("id")] = inp.get("source", "").lstrip("#")
        skin = skins.get(geo.get("id"))
        blocks = [c for c in gm if _local(c.tag) in ("triangles", "polylist", "polygons")]
        for bi, blk in enumerate(blocks):
            inputs = [(i.get("semantic"), i.get("source", "").lstrip("#"), int(i.get("offset", 0)), i.get("set"))
                      for i in blk if _local(i.tag) == "input"]
            if not inputs:
                continue
            stride = max(o for _s, _src, o, _set in inputs) + 1
            p = [int(x) for x in " ".join((t.text or "") for t in blk if _local(t.tag) == "p").split()]
            vcount = [int(x) for x in next((t.text or "" for t in blk if _local(t.tag) == "vcount"), "").split()]
            if _local(blk.tag) == "triangles" or not vcount:
                vcount = [3] * (len(p) // (3 * stride))

            def get(sem, corner):
                for s, src, off, _set in inputs:
                    if s == sem:
                        arr, w = arrays.get(vert_src.get(src, src), ([], 3))
                        k = p[corner * stride + off]
                        return arr[k * w:k * w + w], k
                return None, None

            key: Dict[tuple, int] = {}
            pos, nrm, uv, tris, jn, wt = [], [], [], [], [], []
            corner = 0
            for c in vcount:
                ids = []
                for _ in range(c):
                    k = tuple(p[corner * stride:(corner + 1) * stride])
                    if k not in key:
                        key[k] = len(pos)
                        v, vi = get("VERTEX", corner)
                        pos.append(turn(tuple(v[:3])))
                        n, _ = get("NORMAL", corner)
                        nrm.append(turn(tuple(n[:3])) if n else (0.0, 1.0, 0.0))
                        t, _ = get("TEXCOORD", corner)
                        uv.append((t[0], 1.0 - t[1]) if t else (0.0, 0.0))
                        if skin:
                            pairs = skin[1][vi] if vi < len(skin[1]) else []
                            jn.append([j for j, _w in pairs] or [0])
                            wt.append([w for _j, w in pairs] or [1.0])
                    ids.append(key[k])
                    corner += 1
                tris += _fan(ids)
            name = geo.get("name") or geo.get("id") or "part"
            if len(blocks) > 1:
                name = f"{name}_{bi + 1}"
            b.add(name, pos, nrm, uv, tris, texture=symbol.get(blk.get("material"), ""),
                  joints=jn if skin else None, weights=wt if skin else None,
                  bone_names=skin[0] if skin else ())
    return b.done()


_EXT_LOCK = threading.Lock()
#: path -> (stamp, MeshFile, textures by object name, unpacked folder)
_EXTERNAL: Dict[str, tuple] = {}


def external_id(path: Path) -> str:
    return "ext:" + hashlib.blake2b(str(path).lower().encode("utf-8"), digest_size=8).hexdigest()


def _find_texture(folder: Path, named: str, hints: Sequence[str]) -> Optional[Path]:
    """The image a model names, else one in its folder named for the object."""
    if named:
        p = Path(named.replace("file:///", "").replace("%20", " "))
        cand = p if p.is_absolute() else folder / p
        if cand.is_file():
            return cand
        for sub in (folder, folder / "textures"):
            hit = sub / p.name
            if hit.is_file():
                return hit
    images = [p for sub in (folder, folder / "textures") if sub.is_dir()
              for p in sub.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES]
    for hint in hints:
        hint = hint.lower()
        for p in images:
            if p.stem.lower() == hint:
                return p
        for p in images:
            if hint and hint in p.stem.lower():
                return p
    return None


def read_external(path_text: str) -> Tuple[str, mesh.MeshFile, dict]:
    """``(id, model, textures)`` for an ``.obj``, ``.glb``, ``.gltf`` or ``.dae``.

    Kept while the file is unchanged, so the geometry route serves it without
    a second parse. ``textures`` maps each object's index to the image found
    for it (``""`` where none was: the panel asks for one).
    """
    path = Path((path_text or "").strip().strip('"'))
    if not path.is_file():
        raise ArmoryError(_i18n.msg("eng.armory.no_such_file", "{path} is not a file", path=str(path)))
    suffix = path.suffix.lower()
    if suffix not in EXTERNAL_SUFFIXES:
        raise ArmoryError(_i18n.msg("eng.armory.not_a_model_file", "{name} is not a .obj, .glb, .gltf, .dae or .mesh", name=path.name))
    st = path.stat()
    stamp = (st.st_size, st.st_mtime_ns)
    key = str(path).lower()
    with _EXT_LOCK:
        hit = _EXTERNAL.get(key)
        if hit and hit[0] == stamp:
            return external_id(path), hit[1], hit[2]
    try:
        if suffix == ".mesh":
            # a loose battle model, a Blender export's say, read as the game does
            m, packed = mesh.read_mesh(path, layout=True), {}
        elif suffix == ".obj":
            m, packed = _read_obj(path), {}
        elif suffix in (".glb", ".gltf"):
            m, packed = _read_gltf(path)
        else:
            m, packed = _read_dae(path), {}
    except (ValueError, KeyError, IndexError, struct.error, ET.ParseError, mesh.MeshError) as e:
        raise ArmoryError(_i18n.msg("eng.armory.could_not_read_model", "{name} could not be read: {e}", name=path.name, e=e)) from e
    unpacked = ARMORY_DIR / "external" / external_id(path)[4:]
    if packed:
        unpacked.mkdir(parents=True, exist_ok=True)
        for name, raw in packed.items():
            (unpacked / Path(name).name).write_bytes(raw)
    textures = {}
    sheets = _mesh_sheets(path) if suffix == ".mesh" else None
    for i, g in enumerate(m.groups):
        found = None
        if sheets:
            # a battle .mesh names no texture: the export's own _bmdb.txt, or
            # the main and attachment sheets beside it, as the Models Editor's
            # folder view finds them (100k)
            pick = sheets[1] if g.sheets == "attach" and sheets[1] else sheets[0]
            found = pick
        if g.texture and packed and (unpacked / Path(g.texture).name).is_file():
            found = unpacked / Path(g.texture).name
        if found is None:
            found = _find_texture(path.parent, g.texture, (g.texture_group, g.name, path.stem))
        textures[i] = str(found) if found else ""
    with _EXT_LOCK:
        _EXTERNAL[key] = (stamp, m, textures)
    return external_id(path), m, textures


def _mesh_sheets(path: Path) -> Optional[Tuple[Optional[Path], Optional[Path]]]:
    """``(main, attachment)`` for a loose ``.mesh``, out of its folder."""
    try:
        from . import meshfolder
        fs = meshfolder.open_folder(str(path.parent))
        skins = fs.view(path.name).get("skins") or []
    except Exception:
        return None
    if not skins:
        # the folder view knows the game's sheet types; a .png or .jpg beside
        # the model goes by the same names (main, att)
        from . import loosemesh
        imgs = sorted((p for sub in (path.parent / "textures", path.parent) if sub.is_dir()
                       for p in sub.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES
                       and not re.search(r"(^|[_\-])(n|nrm|norm|normal)([_\-.]|$)", p.stem, re.I)),
                      key=lambda p: p.name.lower())
        att = [p for p in imgs if loosemesh._ATTACH.search(p.stem)]
        main = [p for p in imgs if p not in att]
        main.sort(key=lambda p: (not meshfolder._MAIN.search(p.stem), p.name.lower()))
        if not main:
            return None
        return main[0], (att[0] if att else None)
    first = skins[0]
    main = fs.root / first["rel"] if first.get("rel") else None
    att = fs.root / first["attach"] if first.get("attach") else None
    return (main if main and main.is_file() else None, att if att and att.is_file() else None)


def external_by_id(ext: str) -> Optional[Tuple[mesh.MeshFile, dict]]:
    with _EXT_LOCK:
        for key, (_stamp, m, textures) in _EXTERNAL.items():
            if external_id(Path(key)) == ext:
                return m, textures
    return None


def texture_allowed(path_text: str) -> bool:
    """Only an image an external asset found, or the user picked for one, is served."""
    want = str(Path(path_text)).lower()
    if want.startswith(str(SHEETS_DIR).lower()) and Path(path_text).is_file():
        return True
    with _EXT_LOCK:
        if any(want == str(Path(t)).lower() for _s, _m, tx in _EXTERNAL.values() for t in tx.values() if t):
            return True
        return want in _PICKED


_PICKED: set = set()

# ---------------------------------------------------------------------------
# the Textures tab (100l): a working copy to edit, opened in the user's own
# program, and a sheet written out in the format asked for

#: where a sheet taken out to edit is kept, as a PNG any editor opens
SHEETS_DIR = ARMORY_DIR / "sheets"


def sheet_copy(src: Path) -> Path:
    """A PNG copy of ``src`` under :data:`SHEETS_DIR` to edit; one per source,
    kept, so a second Edit opens the same file with the edits so far."""
    from . import icons
    src = Path(src)
    if str(src).lower().startswith(str(SHEETS_DIR).lower()):
        return src                                   # already a working copy
    tag = hashlib.blake2b(str(src).lower().encode("utf-8"), digest_size=4).hexdigest()
    stem = re.sub(r"[^A-Za-z0-9_\-]", "_", src.name.split(".")[0])[:40] or "sheet"
    out = SHEETS_DIR / f"{stem}_{tag}.png"
    if not out.is_file():
        data = icons._decode_to_png(src, 0)
        if data is None:
            raise ArmoryError(_i18n.msg("eng.armory.sheet_unreadable", "{name} will not decode", name=src.name))
        SHEETS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(out)
    return out


def open_in_editor(path: Path, program: str = "") -> None:
    """``path`` in the program the user set, else the system's own for PNG."""
    import subprocess
    program = (program or "").strip().strip('"')
    if program:
        if not Path(program).is_file():
            raise ArmoryError(_i18n.msg("eng.armory.no_such_program", "{path} is not a program", path=program))
        subprocess.Popen([program, str(path)])
    elif hasattr(os, "startfile"):
        os.startfile(str(path))                       # noqa: S606 - the user's own file
    else:
        subprocess.Popen(["xdg-open", str(path)])


def sheet_stamp(path_text: str) -> int:
    """When the sheet last changed on disk, so the page reloads it after an edit."""
    try:
        return Path(path_text).stat().st_mtime_ns
    except OSError:
        return 0


def export_sheet(src: Path, to: Path) -> Path:
    """``src`` written to ``to`` in the format its suffix names: PNG, TGA,
    JPG, BMP, DDS, or the game's ``.texture`` (a DDS with its header)."""
    from PIL import Image
    from . import icons
    data = icons._decode_to_png(Path(src), 0)
    if data is None:
        raise ArmoryError(_i18n.msg("eng.armory.sheet_unreadable", "{name} will not decode", name=Path(src).name))
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    suffix = to.suffix.lower()
    to.parent.mkdir(parents=True, exist_ok=True)
    if suffix in (".png", ".tga", ".bmp"):
        img.save(to)
    elif suffix in (".jpg", ".jpeg"):
        img.convert("RGB").save(to, quality=95)
    elif suffix in (".dds", ".texture"):
        # as the export bakes a sheet: DXT5 with its whole mipmap chain
        from . import armbake, sprites
        try:
            raw = armbake.dds_with_mipmaps(img)
        except (OSError, ValueError, KeyError) as e:
            raise ArmoryError(_i18n.msg("eng.armory.no_dds_writer", "this Python cannot write DDS: {e}", e=e)) from e
        to.write_bytes(sprites.dds_to_texture(raw) if suffix == ".texture" else raw)
    else:
        raise ArmoryError(_i18n.msg("eng.armory.sheet_format", "{name}: write .png, .tga, .jpg, .bmp, .dds or .texture", name=to.name))
    return to


def allow_texture(path_text: str) -> bool:
    """A sheet picked by hand for an object with none found. True if it is an image."""
    p = Path((path_text or "").strip().strip('"'))
    if not p.is_file() or p.suffix.lower() not in IMAGE_SUFFIXES:
        return False
    with _EXT_LOCK:
        _PICKED.add(str(p).lower())
    return True


def external_view(path_text: str) -> dict:
    """An external model as an asset, the same shape :func:`asset_view` gives."""
    ext, m, textures = read_external(path_text)
    path = Path(path_text.strip().strip('"'))
    objects = _objects(m)
    for o in objects:
        o["texture_file"] = textures.get(o["index"], "")
    return {"kind": "external", "id": ext, "path": str(path), "entry": path.stem,
            "mesh": path.name, "file_hash": file_hash(path.read_bytes()),
            "skins": [], "skeletons": [], "bones": m.bones,
            "skinned": bool(m.weights), "vertices": m.vertices,
            "triangles": m.triangles, "objects": objects}


# ---------------------------------------------------------------------------
# the project


PROJECT = ARMORY_DIR / "project.json"


def load_project() -> dict:
    try:
        return json.loads(PROJECT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


PRESETS = ARMORY_DIR / "presets.json"


def load_presets() -> list:
    """The user's own recolour presets (95f), kept apart from any one model."""
    try:
        return json.loads(PRESETS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def save_presets(presets: list) -> None:
    ARMORY_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS.write_text(json.dumps(presets, indent=1), encoding="utf-8")


KEYS = ARMORY_DIR / "keys.json"


def load_keys() -> dict:
    """The viewport's shortcuts the user changed (95g); the rest are the page's own."""
    try:
        return json.loads(KEYS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_keys(keys: dict) -> None:
    ARMORY_DIR.mkdir(parents=True, exist_ok=True)
    KEYS.write_text(json.dumps(keys, indent=1), encoding="utf-8")


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # a temporary file of each writer's own: two saves at once (a page's
    # last save and its goodbye) must not trip over one another
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(path)


def save_project(project: dict, now: Optional[float] = None) -> None:
    """The working project, saved as it changes. From 99o it is also the
    open session's own file, and backed up now and then (:func:`backup`).
    A save that would empty a model that has objects backs that model up
    first, whatever the clock says: an empty project is sent on purpose
    (New model) and by accident, and the accident must be undoable."""
    if not (project or {}).get("objects"):
        was = load_project()
        if was.get("objects"):
            backup(was, now, force=True)
    _write(PROJECT, project)
    sid = _session_id(project)
    if sid:
        _write(_sessions_dir() / f"{sid}.json", project)
    backup(project, now)
    _write(ARMORY_DIR / "open.json", {"open": True})


# ---------------------------------------------------------------------------
# saved sessions and backups (99o)
#
# A session is a named copy of the project, in sessions/<id>.json; the open
# one is the working project.json, and every save of it is a save of its
# session too. Backups are per session (or of the project no session holds),
# in backups/<id>/<time>.json: one every BACKUP_EVERY seconds while the
# project changes, the newest BACKUPS_KEPT kept. open.json says the page
# had the project open and did not say goodbye, which is how a crash is
# told from a close.

BACKUP_EVERY = 180
BACKUPS_KEPT = 20
_UNSAVED = "_unsaved"


def _sessions_dir() -> Path:
    return ARMORY_DIR / "sessions"


def _backups_dir(sid: str) -> Path:
    return ARMORY_DIR / "backups" / (sid or _UNSAVED)


def _session_id(project: dict) -> str:
    sid = str(((project or {}).get("session") or {}).get("id") or "")
    return sid if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", sid) else ""


def _summary(project: dict) -> dict:
    return {"objects": len(project.get("objects") or []), "assets": len(project.get("assets") or [])}


def backup(project: dict, now: Optional[float] = None, force: bool = False) -> Optional[str]:
    """A backup of the project when the last is BACKUP_EVERY seconds old and
    the project has changed since; the name written, or None."""
    now = time.time() if now is None else now
    folder = _backups_dir(_session_id(project))
    have = sorted(folder.glob("*.json")) if folder.is_dir() else []
    body = json.dumps(project, sort_keys=True)
    if have and not force:
        last = have[-1]
        if now - last.stat().st_mtime < BACKUP_EVERY:
            return None
        try:
            if json.dumps(json.loads(last.read_text(encoding="utf-8")), sort_keys=True) == body:
                return None
        except (OSError, ValueError):
            pass
    name = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    path = folder / f"{name}.json"
    k = 1
    while path.exists():
        path = folder / f"{name}-{k}.json"
        k += 1
    _write(path, project)
    os.utime(path, (now, now))
    for old in sorted(folder.glob("*.json"))[:-BACKUPS_KEPT]:
        old.unlink(missing_ok=True)
    return path.name


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def sessions_view() -> dict:
    """Every saved session, the open one, its backups, and whether the page
    last left the project open without closing (a crash)."""
    out = []
    folder = _sessions_dir()
    for f in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        p = _read(f)
        meta = p.get("session") or {}
        out.append(dict({"id": f.stem, "name": meta.get("name") or f.stem,
                         "saved": f.stat().st_mtime}, **_summary(p)))
    out.sort(key=lambda x: -x["saved"])
    current = load_project()
    sid = _session_id(current)
    bfolder = _backups_dir(sid)
    backups = []
    for f in sorted(bfolder.glob("*.json"), reverse=True) if bfolder.is_dir() else []:
        backups.append(dict({"file": f.name, "time": f.stat().st_mtime}, **_summary(_read(f))))
    unclean = bool(_read(ARMORY_DIR / "open.json").get("open"))
    return {"sessions": out, "current": sid, "name": ((current.get("session") or {}).get("name") or ""),
            "backups": backups, "unclean": unclean}


def opened() -> None:
    """A page has the project open: until it says goodbye, a next open is
    one after a crash."""
    _write(ARMORY_DIR / "open.json", {"open": True})


def closed() -> None:
    """The page said goodbye: the next open is not after a crash."""
    _write(ARMORY_DIR / "open.json", {"open": False})


def _new_id(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")[:40] or "session"
    sid, k = stem, 2
    while (_sessions_dir() / f"{sid}.json").exists():
        sid, k = f"{stem}_{k}", k + 1
    return sid


def session_action(body: dict, now: Optional[float] = None) -> dict:
    """save (the working project under a new name), open, duplicate,
    rename, delete a session; revert the working project to a backup. Each
    answers with the working project as it now is."""
    act = body.get("action") or ""
    name = str(body.get("name") or "").strip()
    sid = str(body.get("id") or "")
    folder = _sessions_dir()
    current = load_project()

    def path_of(i):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", i or "") or not (folder / f"{i}.json").is_file():
            raise ArmoryError(_i18n.msg("eng.armory.no_such_session", "no saved session is called {sid}", sid=i))
        return folder / f"{i}.json"

    if act == "save":
        if not name:
            raise ArmoryError(_i18n.msg("eng.armory.session_needs_name", "a session needs a name"))
        project = body.get("project") if isinstance(body.get("project"), dict) else current
        project = dict(project, session={"id": _new_id(name), "name": name})
        save_project(project, now)
        backup(project, now, force=True)
        return {"project": project}
    if act == "open":
        project = _read(path_of(sid))
        # the one left is backed up as it was, so nothing is lost by opening
        if current.get("objects"):
            backup(current, now, force=True)
        project["session"] = {"id": sid, "name": (project.get("session") or {}).get("name") or sid}
        save_project(project, now)
        return {"project": project}
    if act == "duplicate":
        src = _read(path_of(sid))
        nm = name or ((src.get("session") or {}).get("name") or sid) + " (2)"
        new = _new_id(nm)
        _write(folder / f"{new}.json", dict(src, session={"id": new, "name": nm}))
        return {"project": current}
    if act == "rename":
        if not name:
            raise ArmoryError(_i18n.msg("eng.armory.session_needs_name", "a session needs a name"))
        p = _read(path_of(sid))
        p["session"] = {"id": sid, "name": name}
        _write(folder / f"{sid}.json", p)
        if _session_id(current) == sid:
            current["session"] = p["session"]
            _write(PROJECT, current)
        return {"project": current}
    if act == "delete":
        path_of(sid).unlink()
        if _session_id(current) == sid:
            current.pop("session", None)
            _write(PROJECT, current)
        return {"project": current}
    if act == "revert":
        f = str(body.get("file") or "")
        bpath = _backups_dir(_session_id(current)) / f
        if not re.fullmatch(r"[\w-]+\.json", f) or not bpath.is_file():
            raise ArmoryError(_i18n.msg("eng.armory.no_such_backup", "no backup is called {file}", file=f))
        project = _read(bpath)
        # the state reverted from is a backup of its own
        backup(current, now, force=True)
        if current.get("session"):
            project["session"] = current["session"]
        save_project(project, now)
        return {"project": project}
    raise ArmoryError(_i18n.msg("eng.armory.unknown_session_action", "unknown session action {act}", act=act))


# ---------------------------------------------------------------------------
# an object's geometry (95f): its pieces, moved, turned and scaled


#: model meshes read once while their files are unchanged, by asset key
_MESHES: Dict[str, tuple] = {}


def asset_key(asset: dict) -> str:
    """The page's own key for an asset (``armAssetKey`` in armory.js)."""
    if asset.get("kind") == "external":
        return "ext|" + (asset.get("path") or "").lower()
    return f"{asset.get('mod')}|{asset.get('entry')}"


def asset_mesh(asset: dict, mod_of) -> mesh.MeshFile:
    """The first LOD of an asset, with what writing it back needs.

    ``mod_of(name)`` is how the caller finds an installed mod by name.
    """
    if asset.get("kind") == "external":
        _id, m, _tex = read_external(asset.get("path") or "")
        return m
    mod = mod_of(asset.get("mod") or "")
    entry = mod.modeldb.by_name().get((asset.get("entry") or "").lower())
    if entry is None or not entry.lods:
        raise ArmoryError(_i18n.msg("eng.armory.no_such_entry", "{mod} has no model entry {name}", mod=asset.get("mod"), name=asset.get("entry")))
    rel = entry.lods[0][0].replace("\\", "/").strip()
    path, _where = gamepack.lookup(rel, mod)
    if path is None or not path.is_file():
        raise ArmoryError(_i18n.msg("eng.armory.mesh_not_found", "{rel} is in neither the mod, the game nor its packs", rel=rel))
    st = path.stat()
    key = asset_key(asset)
    hit = _MESHES.get(key)
    if hit and hit[0] == (str(path), st.st_size, st.st_mtime_ns):
        return hit[1]
    m = mesh.read_mesh(path, layout=True)
    _MESHES[key] = ((str(path), st.st_size, st.st_mtime_ns), m)
    return m


def rotation(rx: float, ry: float, rz: float) -> List[List[float]]:
    """Z * Y * X, degrees, the order ``armRot`` in armory.js multiplies in."""
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    X = [[1, 0, 0], [0, ca, -sa], [0, sa, ca]]
    Y = [[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]]
    Z = [[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]
    mul = lambda p, q: [[sum(p[i][k] * q[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mul(Z, mul(Y, X))


def piece_indices(m: mesh.MeshFile, piece: dict) -> List[int]:
    """A piece's triangles as vertex indices into its source model.

    Optimize (100n) leaves a piece ``weld`` ({vertex: the one it merged
    into}) and ``flip`` (triangles turned to face outward), honoured here."""
    g = m.groups[int(piece.get("group", 0))]
    tris = piece.get("tris")
    weld, flip = piece.get("weld") or {}, piece.get("flip") or ()
    ix = g.indices
    if not weld and not flip:
        if tris is None:
            return list(ix)
        return [ix[t * 3 + k] for t in tris if t * 3 + 2 < len(ix) for k in range(3)]
    flip = set(flip)
    out: List[int] = []
    for t in (range(len(ix) // 3) if tris is None else tris):
        if t * 3 + 2 >= len(ix):
            continue
        a, b, c = ix[t * 3], ix[t * 3 + 1], ix[t * 3 + 2]
        if t in flip:
            b, c = c, b
        if weld:
            a, b, c = (int(weld.get(str(v), v)) for v in (a, b, c))
        out += (a, b, c)
    return out


def _xf(p, xf):
    """A piece's own matrix (column-major, as the page keeps it) on a point."""
    if not xf:
        return p
    x, y, z = p
    return (xf[0] * x + xf[4] * y + xf[8] * z + xf[12],
            xf[1] * x + xf[5] * y + xf[9] * z + xf[13],
            xf[2] * x + xf[6] * y + xf[10] * z + xf[14])


def object_mesh(obj: dict, assets: Dict[str, dict], mod_of) -> mesh.MeshFile:
    """One object as a model of its own, in the place the page draws it.

    Each piece takes only the vertices its triangles use, in index order, so
    the page and this agree on which vertex is which. Bones are named per
    vertex across pieces, a union in order of first use. An object with
    ``weights`` of its own (transferred, 95f) wears them.
    """
    out = mesh.MeshFile(source=obj.get("name", ""), format="mesh")
    weights, ids = array("f"), bytearray()
    flat_all = array("H")
    pts: List[Tuple[float, float, float]] = []
    nrms: List[Tuple[float, float, float]] = []
    for piece in obj.get("src") or []:
        asset = assets.get(piece.get("asset"))
        if asset is None:
            continue
        m = asset_mesh(asset, mod_of)
        flat = piece_indices(m, piece)
        used = sorted(set(flat))
        remap = {old: new + len(pts) for new, old in enumerate(used)}
        xf = piece.get("xf")
        skinned = bool(m.weights) and len(m.bone_ids) == m.vertices * 4
        # 100m: UVs moved in the UV editor, by the asset's vertex
        moved = piece.get("uv") or {}
        # 100n: normals Optimize worked out again
        renorm = piece.get("nrm") or {}
        for v in used:
            pts.append(_xf((m.positions[v * 3], m.positions[v * 3 + 1], m.positions[v * 3 + 2]), xf))
            rn = renorm.get(str(v)) if renorm else None
            n = (tuple(float(x) for x in rn) if rn else
                 (m.normals[v * 3], m.normals[v * 3 + 1], m.normals[v * 3 + 2]) if m.normals else (0.0, 1.0, 0.0))
            if xf:
                n = _xf(n, list(xf[:12]) + [0, 0, 0, 1])
            nrms.append(n)
            mv = moved.get(str(v)) if moved else None
            out.uvs.extend((float(mv[0]), float(mv[1])) if mv else
                           (m.uvs[v * 2], m.uvs[v * 2 + 1]) if m.uvs else (0.0, 0.0))
            if skinned:
                b = m.bone_ids[v * 4:v * 4 + 4]
                pair = []
                for k in (2, 1):
                    name = m.bones[b[k]] if b[k] < len(m.bones) else ""
                    if name not in out.bones:
                        out.bones.append(name)
                    pair.append(out.bones.index(name))
                weights.extend((m.weights[v * 2], m.weights[v * 2 + 1]))
                ids += bytes((0, pair[1], pair[0], 0))
            else:
                weights.extend((0.0, 0.0))
                ids += bytes(4)
        flat_all.extend(remap[i] for i in flat)
    # the object's own move, turn and scale, about the centre of what it
    # holds counted by index, as armPivots counts it
    if flat_all:
        cx = sum(pts[i][0] for i in flat_all) / len(flat_all)
        cy = sum(pts[i][1] for i in flat_all) / len(flat_all)
        cz = sum(pts[i][2] for i in flat_all) / len(flat_all)
    else:
        cx = cy = cz = 0.0
    t = obj.get("t") or [0, 0, 0]
    r = rotation(*(obj.get("r") or [0, 0, 0]))
    s = obj.get("s") or [1, 1, 1]
    for x, y, z in pts:
        x, y, z = (x - cx) * s[0], (y - cy) * s[1], (z - cz) * s[2]
        out.positions.extend((r[0][0] * x + r[0][1] * y + r[0][2] * z + cx + t[0],
                              r[1][0] * x + r[1][1] * y + r[1][2] * z + cy + t[1],
                              r[2][0] * x + r[2][1] * y + r[2][2] * z + cz + t[2]))
    inv = [1 / v if v else 0.0 for v in s]
    for x, y, z in nrms:
        x, y, z = x * inv[0], y * inv[1], z * inv[2]
        nx = r[0][0] * x + r[0][1] * y + r[0][2] * z
        ny = r[1][0] * x + r[1][1] * y + r[1][2] * z
        nz = r[2][0] * x + r[2][1] * y + r[2][2] * z
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        out.normals.extend((nx / ln, ny / ln, nz / ln))
    out.weights, out.bone_ids = weights, bytes(ids)
    own = obj.get("weights")
    if own and own.get("n") == len(pts):
        raw = base64.b64decode(own["data"])
        out.weights = array("f")
        out.weights.frombytes(raw[:len(pts) * 8])
        out.bone_ids = raw[len(pts) * 8:]
        out.bones = list(own.get("bones") or [])
    out.groups.append(mesh.MeshGroup(obj.get("name") or "part", obj.get("mesh") or "part",
                                     flat_all, int(obj.get("flag") or 0)))
    return out


def has_weights(m: mesh.MeshFile) -> bool:
    """Any vertex bound to a bone at all."""
    return any(w > 0 for w in m.weights)


# ---------------------------------------------------------------------------
# bones (95g): a part from a skeleton that spells its bones another way


def bone_remap(src: Sequence[str], target: Sequence[str]) -> Tuple[List[int], List[str]]:
    """``(index into target per source bone, names not found)``.

    The archer skeletons write ``bone_rhand``, the melee ones ``bone_Rhand``
    (and ``bone_RThigh`` against ``bone_rthigh``): the same bone in another
    case, which is all the Blender kit's rename between the two does. A bone
    the target has not got at all maps to -1 and is named.
    """
    by_lower = {name.lower(): i for i, name in enumerate(target)}
    out, missing = [], []
    for name in src:
        i = by_lower.get(name.lower(), -1)
        out.append(i)
        if i < 0 and name:
            missing.append(name)
    return out, missing


# ---------------------------------------------------------------------------
# transfer weights (95f)


def _closest_on_triangle(p, a, b, c):
    """The closest point to ``p`` on triangle ``abc``, as barycentric weights
    (Ericson, *Real-Time Collision Detection*, 5.1.5)."""
    dot = lambda u, v: u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    ab = [b[i] - a[i] for i in range(3)]
    ac = [c[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    d1, d2 = dot(ab, ap), dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return (1.0, 0.0, 0.0)
    bp = [p[i] - b[i] for i in range(3)]
    d3, d4 = dot(ab, bp), dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return (0.0, 1.0, 0.0)
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        return (1 - v, v, 0.0)
    cp = [p[i] - c[i] for i in range(3)]
    d5, d6 = dot(ab, cp), dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return (0.0, 0.0, 1.0)
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        return (1 - w, 0.0, w)
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return (0.0, 1 - w, w)
    den = 1.0 / (va + vb + vc)
    v, w = vb * den, vc * den
    return (1 - v - w, v, w)


# the parts that hold one bone in the game, as the Blender kit's prefixes
# name them (``qol_panel.py``): a shield or a weapon moves as one piece
_RIGID_PART = re.compile(r"shield|weapon\d|primary(active|passive)|secondary(active|passive)"
                         r"|ramrod|cannon ?ball|ballista ?arrow", re.I)
# the side a Med2 bone is on: bone_lfoot, bone_Lhand, bone_RThigh
_SIDE = re.compile(r"^bone_([lr])(?=foot|lowerleg|thigh|upperarm|elbow|hand|forearm"
                   r"|shoulder|clavical|clavicle|calf|toe|finger)", re.I)


def bone_side(name: str) -> str:
    """``"l"``, ``"r"`` or ``""`` for a Med2 bone name."""
    m = _SIDE.match(name or "")
    return m.group(1).lower() if m else ""


def transfer_weights(target: mesh.MeshFile, sources: Sequence[mesh.MeshFile],
                     mode: str = "face", smooth: int = 5,
                     own: Optional[Sequence[Dict[str, float]]] = None,
                     reach: float = 0.05, rigid: bool = False,
                     factor: float = 0.5) -> Tuple[array, bytes, List[str]]:
    """Weights for every vertex of ``target`` out of the nearest of ``sources``.

    The Blender kit's *Transfer weights* (``qol_panel.py``): nearest face,
    interpolated, by default, or the nearest vertex or edge; then ``smooth``
    passes of Blender's vertex group smooth at ``factor``. Each vertex keeps
    its two strongest bones, as the format holds. Returns ``(weights,
    bone_ids, bones)`` laid out as :class:`~unittransfer.mesh.MeshFile` keeps
    them.

    ``own`` is the target's weights before the transfer, a ``{bone name:
    weight}`` per vertex (100a). Where it is given, a vertex with no source
    surface within ``reach`` keeps its own (a foot below every other part
    took the shin), as does one whose own strongest bone no source carries
    at all (the hands took the forearm), and a vertex whose own bones are on
    one side takes no bone of the other. ``rigid`` puts every vertex on one bone at 1.0, the
    one most vertices would take, or the part's own where a quarter of them
    would: a shield split over the hand, forearm and upper arm tore apart
    as the arm moved.
    """
    bones: List[str] = []

    def bone_named(name):
        low = [x.lower() for x in bones]
        if name.lower() not in low:
            bones.append(name)
            return len(bones) - 1
        return low.index(name.lower())

    def bone_of(src, b):
        return bone_named(src.bones[b] if b < len(src.bones) else "")

    tris: List[Tuple[int, int, int]] = []
    infl: List[Dict[int, float]] = []
    pts: List[Tuple[float, float, float]] = []
    for src in sources:
        if not has_weights(src) or len(src.bone_ids) != src.vertices * 4:
            continue
        base = len(pts)
        for v in range(src.vertices):
            pts.append((src.positions[v * 3], src.positions[v * 3 + 1], src.positions[v * 3 + 2]))
            b = src.bone_ids[v * 4:v * 4 + 4]
            d: Dict[int, float] = {}
            for k, w in ((2, src.weights[v * 2]), (1, src.weights[v * 2 + 1])):
                if w > 0:
                    j = bone_of(src, b[k])
                    d[j] = d.get(j, 0.0) + w
            infl.append(d)
        for g in src.groups:
            ix = g.indices
            for t in range(0, len(ix) - 2, 3):
                tris.append((base + ix[t], base + ix[t + 1], base + ix[t + 2]))
    if not tris:
        raise ArmoryError(_i18n.msg("eng.armory.no_weights_to_take", "nothing visible in the model has weights to take"))
    # a grid over the source triangles, so each vertex looks only nearby
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    size = max(hi[k] - lo[k] for k in range(3)) or 1.0
    cell = size / max(4, int(round(len(tris) ** (1 / 3))) * 2)
    grid: Dict[Tuple[int, int, int], List[int]] = {}

    def key(p):
        return tuple(int(math.floor((p[k] - lo[k]) / cell)) for k in range(3))
    for ti, (a, b, c) in enumerate(tris):
        ka, kb, kc = key(pts[a]), key(pts[b]), key(pts[c])
        for i in range(min(ka[0], kb[0], kc[0]), max(ka[0], kb[0], kc[0]) + 1):
            for j in range(min(ka[1], kb[1], kc[1]), max(ka[1], kb[1], kc[1]) + 1):
                for k in range(min(ka[2], kb[2], kc[2]), max(ka[2], kb[2], kc[2]) + 1):
                    grid.setdefault((i, j, k), []).append(ti)
    span = int(math.ceil(size / cell)) + 2
    top = [max(c[k] for c in grid) for k in range(3)]

    def shell(c0, ring):
        """The cells ``ring`` steps out from ``c0``, only its shell and only
        inside the grid: a part far from the rest searched the whole cube of
        empty cells round it, ring after ring, a minute for 160 vertices."""
        i0, i1 = max(0, c0[0] - ring), min(top[0], c0[0] + ring)
        j0, j1 = max(0, c0[1] - ring), min(top[1], c0[1] + ring)
        for i in range(i0, i1 + 1):
            ei = abs(i - c0[0]) == ring
            for j in range(j0, j1 + 1):
                if ei or abs(j - c0[1]) == ring:
                    for k in range(max(0, c0[2] - ring), min(top[2], c0[2] + ring) + 1):
                        yield i, j, k
                else:
                    for k in (c0[2] - ring, c0[2] + ring):
                        if 0 <= k <= top[2]:
                            yield i, j, k

    def near(p, limit=None):
        # the cell of the grid nearest the point: every cell past the grid
        # is empty, and a ring counts from there as it did from the point
        c0 = tuple(min(max(x, 0), top[n]) for n, x in enumerate(key(p)))
        # and how far the point is from the grid's box: nothing in a ring is
        # nearer than that and the ring's own reach together
        out2 = sum(max(lo[n] - p[n], 0.0, p[n] - (lo[n] + (top[n] + 1) * cell)) ** 2 for n in range(3))
        best, best_d = None, float("inf")
        for ring in range(span):
            for i, j, k in shell(c0, ring):
                        for ti in grid.get((i, j, k), ()):
                            a, b, c = tris[ti]
                            if mode == "vertex":
                                for vi, bary in ((a, (1.0, 0.0, 0.0)), (b, (0.0, 1.0, 0.0)), (c, (0.0, 0.0, 1.0))):
                                    d = sum((pts[vi][q] - p[q]) ** 2 for q in range(3))
                                    if d < best_d:
                                        best, best_d = (ti, bary), d
                                continue
                            bary = _closest_on_triangle(p, pts[a], pts[b], pts[c])
                            q = [bary[0] * pts[a][n] + bary[1] * pts[b][n] + bary[2] * pts[c][n] for n in range(3)]
                            d = sum((q[n] - p[n]) ** 2 for n in range(3))
                            if mode == "edge":
                                # the nearest edge: the corner the point is
                                # farthest from drops out
                                k0 = min(range(3), key=lambda x: bary[x])
                                rest = [bary[x] if x != k0 else 0.0 for x in range(3)]
                                tot = sum(rest) or 1.0
                                bary = tuple(x / tot for x in rest)
                            if d < best_d:
                                best, best_d = (ti, bary), d
            if best is not None and best_d < out2 + (ring * cell) ** 2:
                break
            # nothing left within ``limit``: what was found stands, or nothing
            if limit is not None and out2 + (ring * cell) ** 2 > limit * limit:
                break
        return best and (best[0], best[1], math.sqrt(best_d))

    n = target.vertices
    carried = {k for d in infl for k in d}
    mine: List[Dict[int, float]] = []
    for v in range(n):
        d0 = (own[v] if own is not None and v < len(own) else None) or {}
        mine.append({bone_named(k): w for k, w in d0.items() if w > 0})
    per: List[Dict[int, float]] = []
    for v in range(n):
        # a vertex of its own with nothing within reach keeps its own, so
        # its search ends at the reach
        hit = near((target.positions[v * 3], target.positions[v * 3 + 1], target.positions[v * 3 + 2]),
                   reach if mine[v] else None)
        d: Dict[int, float] = {}
        if hit is not None:
            (a, b, c), bary = tris[hit[0]], hit[1]
            for vi, w in zip((a, b, c), bary):
                for bone, bw in infl[vi].items():
                    d[bone] = d.get(bone, 0.0) + bw * w
        if mine[v]:
            if hit is None or hit[2] > reach or max(mine[v], key=mine[v].get) not in carried:
                d = dict(mine[v])
            else:
                sides = {bone_side(bones[k]) for k in mine[v]} - {""}
                if len(sides) == 1:
                    other = "r" if sides == {"l"} else "l"
                    d = {k: w for k, w in d.items() if bone_side(bones[k]) != other} or dict(mine[v])
        per.append(d)
    if rigid and n:
        def tally(rows):
            out: Dict[int, int] = {}
            for d in rows:
                if d:
                    k = max(d, key=d.get)
                    out[k] = out.get(k, 0) + 1
            return out
        votes, home_votes = tally(per), tally(mine)
        pick = max(votes, key=votes.get) if votes else 0
        if home_votes:
            home = max(home_votes, key=home_votes.get)
            if votes.get(home, 0) * 4 >= n:
                pick = home
        per = [{pick: 1.0} for _ in range(n)]
        smooth = 0
    if smooth and target.groups:
        nbr: List[set] = [set() for _ in range(n)]
        for g in target.groups:
            ix = g.indices
            for t in range(0, len(ix) - 2, 3):
                a, b, c = ix[t], ix[t + 1], ix[t + 2]
                nbr[a].update((b, c))
                nbr[b].update((a, c))
                nbr[c].update((a, b))
        for _ in range(smooth):
            nxt = []
            for v in range(n):
                if not nbr[v]:
                    nxt.append(per[v])
                    continue
                # Blender's vertex group smooth: each weight moves ``factor``
                # of the way to its neighbours' mean
                acc = {b: w * (1 - factor) for b, w in per[v].items()}
                share = factor / len(nbr[v])
                for u in nbr[v]:
                    for bone, w in per[u].items():
                        acc[bone] = acc.get(bone, 0.0) + w * share
                tot = sum(acc.values()) or 1.0
                nxt.append({b: w / tot for b, w in acc.items()})
            per = nxt
    weights, ids = array("f"), bytearray()
    for d in per:
        top = sorted(d.items(), key=lambda kv: -kv[1])[:2]
        while len(top) < 2:
            top.append((top[0][0] if top else 0, 0.0))
        tot = (top[0][1] + top[1][1]) or 1.0
        weights.extend((top[0][1] / tot, top[1][1] / tot))
        ids += bytes((0, top[1][0], top[0][0], 0))
    return weights, bytes(ids), bones


# ---------------------------------------------------------------------------
# Optimize (100n): the user's Quick Cleanup addon, the steps a game mesh can
# take. Its tris-to-quads and triangulate have nothing to do on a mesh that is
# triangles already; fill holes and fix non-manifold change what the model is
# and are left to Blender. Each step's result rides on the piece - ``tris``
# kept, ``weld``, ``flip``, ``nrm`` - so the sheet, the UVs and the weights
# stay the asset's.

OPTIMIZE_STEPS = ("merge", "degenerate", "outside", "reset_normals", "checks")


def _optimize_piece(m: mesh.MeshFile, piece: dict, opts: dict) -> Tuple[dict, dict]:
    """``(changes, counts)`` for one piece, from its asset as it stands."""
    g = m.groups[int(piece.get("group", 0))]
    ix = g.indices
    tris = list(range(len(ix) // 3)) if piece.get("tris") is None else list(piece["tris"])
    P, U = m.positions, m.uvs
    weld = {int(k): int(v) for k, v in (piece.get("weld") or {}).items()}
    flip = set(piece.get("flip") or ())
    counts = {"merged": 0, "degenerate": 0, "flipped": 0, "normals": 0, "loose": 0}
    corner = lambda t: [ix[t * 3], ix[t * 3 + 1], ix[t * 3 + 2]]
    used = sorted({v for t in tris for v in corner(t)})
    if opts.get("merge"):
        dist = max(1e-7, float(opts.get("merge_distance") or 0.0001))
        cells: Dict[tuple, List[int]] = {}
        for v in used:
            if v in weld:
                continue
            key = tuple(int(math.floor(P[v * 3 + k] / dist)) for k in range(3))
            uv = (round(U[v * 2], 5), round(U[v * 2 + 1], 5)) if U else (0, 0)
            hit = None
            # the cell and its neighbours, so two points either side of a
            # cell wall still meet; a seam (another UV) is never merged
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for w in cells.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                            if hit is None and (round(U[w * 2], 5), round(U[w * 2 + 1], 5)) == uv \
                                    and sum((P[v * 3 + k] - P[w * 3 + k]) ** 2 for k in range(3)) <= dist * dist:
                                hit = w
            if hit is None:
                cells.setdefault(key, []).append(v)
            else:
                weld[v] = hit
                counts["merged"] += 1
    W = lambda v: weld.get(v, v)
    if opts.get("degenerate") or opts.get("merge"):
        keep = []
        eps = (float(opts.get("merge_distance") or 0.0001)) ** 2
        for t in tris:
            a, b, c = (W(v) for v in corner(t))
            if a == b or b == c or a == c:
                counts["degenerate"] += 1
                continue
            if opts.get("degenerate"):
                pa, pb, pc_ = ([P[v * 3 + k] for k in range(3)] for v in (a, b, c))
                e1 = [pb[k] - pa[k] for k in range(3)]
                e2 = [pc_[k] - pa[k] for k in range(3)]
                cr = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                if cr[0] ** 2 + cr[1] ** 2 + cr[2] ** 2 <= eps * eps:
                    counts["degenerate"] += 1
                    continue
            keep.append(t)
        counts["loose"] = len({W(v) for v in used}) - len({W(v) for t in keep for v in corner(t)})
        tris = keep

    def tri(t):
        a, b, c = (W(v) for v in corner(t))
        return (a, c, b) if t in flip else (a, b, c)

    if opts.get("outside") and tris:
        # winding made consistent across each connected part, then each part
        # turned to the side the asset as a whole faces (the game's own
        # convention, read from the model rather than assumed)
        by_edge: Dict[tuple, List[int]] = {}
        for t in tris:
            a, b, c = tri(t)
            for e in ((a, b), (b, c), (c, a)):
                by_edge.setdefault((min(e), max(e)), []).append(t)
        seen: Dict[int, bool] = {}
        parts: List[List[int]] = []
        for t0 in tris:
            if t0 in seen:
                continue
            seen[t0] = False
            part, todo = [t0], [t0]
            while todo:
                t = todo.pop()
                a, b, c = tri(t)
                if seen[t]:
                    a, b, c = a, c, b
                for x, y in ((a, b), (b, c), (c, a)):
                    for u in by_edge[(min(x, y), max(x, y))]:
                        if u == t or u in seen:
                            continue
                        p, q, r = tri(u)
                        same = (x, y) in ((p, q), (q, r), (r, p))
                        # a neighbour sharing an edge runs it the other way
                        seen[u] = same
                        part.append(u)
                        todo.append(u)
            parts.append(part)

        def outward(ts, turned):
            # how far the faces point away from the middle of what they
            # make, weighted by area: no origin in it, so a corner at 0,0,0
            # counts as any other
            vs = {v for t in ts for v in tri(t)}
            C = [sum(P[v * 3 + k] for v in vs) / len(vs) for k in range(3)]
            s = 0.0
            for t in ts:
                a, b, c = tri(t)
                if turned.get(t):
                    b, c = c, b
                pa, pb, pc_ = ([P[v * 3 + k] for k in range(3)] for v in (a, b, c))
                e1 = [pb[k] - pa[k] for k in range(3)]
                e2 = [pc_[k] - pa[k] for k in range(3)]
                cr = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                mid = [(pa[k] + pb[k] + pc_[k]) / 3 - C[k] for k in range(3)]
                s += cr[0] * mid[0] + cr[1] * mid[1] + cr[2] * mid[2]
            return s
        ref = outward(tris, {})
        sign = 1.0 if ref >= 0 else -1.0

        def area(t):
            a, b, c = tri(t)
            pa, pb, pc_ = ([P[v * 3 + k] for k in range(3)] for v in (a, b, c))
            e1 = [pb[k] - pa[k] for k in range(3)]
            e2 = [pc_[k] - pa[k] for k in range(3)]
            return math.sqrt((e1[1] * e2[2] - e1[2] * e2[1]) ** 2 + (e1[2] * e2[0] - e1[0] * e2[2]) ** 2
                             + (e1[0] * e2[1] - e1[1] * e2[0]) ** 2)
        for part in parts:
            turned = {t: seen[t] for t in part}
            edges_of: Dict[tuple, int] = {}
            for t in part:
                a, b, c = tri(t)
                for e in ((a, b), (b, c), (c, a)):
                    k_ = (min(e), max(e))
                    edges_of[k_] = edges_of.get(k_, 0) + 1
            closed = all(n_ == 2 for n_ in edges_of.values())
            if closed:
                # a closed part faces out as the model does
                wrong = outward(part, turned) * sign < 0
            else:
                # an open one (a cloak, a doubled cape) keeps the way most of
                # it already faces, by area: which side is "out" is the
                # modeller's call, and a back-to-back layer faces in on purpose
                wrong = sum(area(t) for t in part if turned[t]) > sum(area(t) for t in part if not turned[t])
            if wrong:
                turned = {t: not v for t, v in turned.items()}
            for t, v in turned.items():
                if v:
                    flip ^= {t}
                    counts["flipped"] += 1
    nrm: Dict[str, list] = dict(piece.get("nrm") or {})
    if opts.get("reset_normals") and tris:
        acc: Dict[int, List[float]] = {}
        for t in tris:
            a, b, c = tri(t)
            pa, pb, pc_ = ([P[v * 3 + k] for k in range(3)] for v in (a, b, c))
            e1 = [pb[k] - pa[k] for k in range(3)]
            e2 = [pc_[k] - pa[k] for k in range(3)]
            cr = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            for v in (a, b, c):
                s = acc.setdefault(v, [0.0, 0.0, 0.0])
                for k in range(3):
                    s[k] += cr[k]
        # the cross product's side against the normals the file had, so the
        # new ones point the way the game's do
        agree = sum(acc[v][0] * m.normals[v * 3] + acc[v][1] * m.normals[v * 3 + 1] + acc[v][2] * m.normals[v * 3 + 2]
                    for v in acc) if m.normals else 1.0
        sgn = 1.0 if agree >= 0 else -1.0
        for v, s in acc.items():
            ln = math.sqrt(s[0] ** 2 + s[1] ** 2 + s[2] ** 2) or 1.0
            nrm[str(v)] = [round(sgn * s[k] / ln, 6) for k in range(3)]
        counts["normals"] = len(acc)
    changes = {"tris": tris if (len(tris) != len(ix) // 3 or piece.get("tris") is not None) else None,
               "weld": {str(k): v for k, v in weld.items()} or None,
               "flip": sorted(flip) or None, "nrm": nrm or None}
    return changes, counts


def optimize(project: dict, obj_ids: Sequence[int], opts: dict, mod_of) -> dict:
    """The page's *Optimize* (100n) on each object: per piece what changes,
    the counts, and the Blender kit's export checks on what it comes to."""
    assets = project_assets(project)
    out: Dict[str, dict] = {}
    total = {"merged": 0, "degenerate": 0, "flipped": 0, "normals": 0, "loose": 0}
    ids = [int(i) for i in obj_ids]
    for o in project.get("objects") or []:
        if o.get("id") not in ids:
            continue
        pieces = []
        for piece in o.get("src") or []:
            asset = assets.get(piece.get("asset"))
            if asset is None:
                pieces.append(None)
                continue
            m = asset_mesh(asset, mod_of)
            ch, n = _optimize_piece(m, piece, opts)
            pieces.append(ch)
            for k in total:
                total[k] += n[k]
        out[str(o["id"])] = {"pieces": pieces}
    checks = None
    if opts.get("checks"):
        from . import armbake
        trial = json.loads(json.dumps(project))
        for o in trial.get("objects") or []:
            got = out.get(str(o.get("id")))
            if not got:
                continue
            for piece, ch in zip(o.get("src") or [], got["pieces"]):
                if ch:
                    for k, v in ch.items():
                        if v is None:
                            piece.pop(k, None)
                        else:
                            piece[k] = v
        try:
            checks = armbake.check_model(trial, mod_of)
        except Exception as e:                                    # a check never stops the run
            checks = {"issues": [], "error": str(e)}
    return {"objects": out, "counts": total, "checks": checks}


def project_assets(project: dict) -> Dict[str, dict]:
    return {asset_key(a): a for a in project.get("assets") or []}


def transfer_for(project: dict, obj_id: int, mode: str, mod_of) -> dict:
    """The page's *Transfer weights* on one object, from every other visible
    object in the model that has weights. The answer is stored on the object
    as ``weights`` (base64 of the weights then the bone bytes)."""
    assets = project_assets(project)
    objs = project.get("objects") or []
    target = next((o for o in objs if o.get("id") == obj_id), None)
    if target is None:
        raise ArmoryError(_i18n.msg("eng.armory.no_such_object", "that object is not in the model"))
    clean = dict(target, weights=None)
    tm = object_mesh(clean, assets, mod_of)
    # what the part wore before, so a vertex nothing reaches keeps it (100a)
    own: List[Dict[str, float]] = []
    for v in range(tm.vertices):
        d: Dict[str, float] = {}
        if len(tm.bone_ids) >= (v + 1) * 4:
            b = tm.bone_ids[v * 4:v * 4 + 4]
            for k, w in ((2, tm.weights[v * 2]), (1, tm.weights[v * 2 + 1])):
                name = tm.bones[b[k]] if b[k] < len(tm.bones) else ""
                if w > 0 and name:
                    d[name] = d.get(name, 0.0) + w
        own.append(d)
    tops = {max(d, key=d.get).lower() for d in own if d}
    whole = all(d and max(d.values()) >= 0.999 for d in own)
    named = f"{target.get('name') or ''} {target.get('mesh') or ''}"
    rigid = bool(_RIGID_PART.search(named)) or (len(tops) == 1 and whole)
    sources = []
    for o in objs:
        if o is target or o.get("hidden"):
            continue
        # a body part takes nothing from a shield or a weapon: the spear in
        # the right hand gave that hand its bone and the left none (100a)
        if not rigid and _RIGID_PART.search(f"{o.get('name') or ''} {o.get('mesh') or ''}"):
            continue
        om = object_mesh(o, assets, mod_of)
        if has_weights(om):
            sources.append(om)
    w, ids, bones = transfer_weights(tm, sources, mode=mode, own=own, rigid=rigid)
    return {"n": tm.vertices, "bones": bones, "mode": mode, "rigid": rigid,
            "data": base64.b64encode(w.tobytes() + ids).decode("ascii")}


# the Med2 skeleton's bones in the order the workbench lists them (100b, the
# user's order): head, torso and pelvis, the right arm from the hand in,
# the left, then the legs; the kit's spelling (``control_rig_data.py``)
MED2_BONES = ["bone_head", "bone_torso", "bone_abs", "bone_pelvis",
              "bone_rhand", "bone_relbow", "bone_rupperarm", "bone_rclavical",
              "bone_lhand", "bone_lelbow", "bone_lupperarm", "bone_lclavical",
              "bone_rthigh", "bone_rlowerleg", "bone_rfoot",
              "bone_lthigh", "bone_llowerleg", "bone_lfoot",
              "bone_jaw", "bone_eyebrow"]


def rig_to_bones(project: dict, obj_ids: Sequence[int], bones: Sequence[str],
                 share: float, mod_of) -> Dict[str, dict]:
    """The page's *Rig to bones* (100b): every vertex of each object on the
    first bone, or on two with ``share`` of the weight on the first. The
    answer per object id is what :func:`transfer_for` stores."""
    names = [b for b in bones if b][:2]
    if not names:
        raise ArmoryError(_i18n.msg("eng.armory.pick_a_bone", "pick a bone to rig to"))
    share = 1.0 if len(names) == 1 else min(1.0, max(0.5, float(share)))
    pair = names if len(names) == 2 else names * 2
    assets = project_assets(project)
    out: Dict[str, dict] = {}
    for oid in obj_ids:
        o = next((x for x in project.get("objects") or [] if x.get("id") == oid), None)
        if o is None:
            continue
        n = object_mesh(dict(o, weights=None), assets, mod_of).vertices
        w = array("f", [share, 1.0 - share] * n)
        ids = bytes((0, 1, 0, 0)) * n if len(names) == 2 else bytes(4 * n)
        out[str(oid)] = {"n": n, "bones": list(dict.fromkeys(pair)), "mode": "rig",
                         "data": base64.b64encode(w.tobytes() + ids).decode("ascii")}
    return out


# ---------------------------------------------------------------------------
# unit cards (95m): what the card maker drew, kept as the game reads it



def save_card(name: str, kind: str, png_data_url: str) -> dict:
    """A card the page drew, written as ``.tga`` (and ``.png``) under
    ``config/armory/cards/<name>/``: ``#<name>.tga`` for a unit card,
    ``<name>_info.tga`` for an info card, ``<name>_<w>x<h>`` for another size
    and ``<name>_hd.png`` for the HD render. The unit editor's card import
    takes the ``.tga`` from there into every owning faction's folder."""
    import io
    from PIL import Image
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", (name or "").strip())
    if not safe:
        raise ArmoryError(_i18n.msg("eng.armory.card_needs_name", "give the card a name"))
    head, _, b64 = (png_data_url or "").partition(",")
    if "image/png" not in head or not b64:
        raise ArmoryError(_i18n.msg("eng.armory.card_not_png", "the card did not come as a PNG"))
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
    folder = ARMORY_DIR / "cards" / safe
    folder.mkdir(parents=True, exist_ok=True)
    if kind == "hd":
        out = folder / f"{safe}_hd.png"
        img.save(out)
        return {"path": str(out), "kind": kind, "size": list(img.size)}
    stem = {"card": f"#{safe}", "info": f"{safe}_info"}.get(kind, f"{safe}_{img.width}x{img.height}")
    img.save(folder / f"{stem}.png")
    out = folder / f"{stem}.tga"
    img.save(out)
    return {"path": str(out), "kind": kind, "size": list(img.size)}
