"""A battle model out of the game's formats: M16's converter half (Phase 57b).

The reference tool's *Asset Converter* turns ``.texture`` into ``.dds`` and a
``.mesh`` or ``.cas`` into MilkShape ``.ms3d`` and back. This does the parts of
that which are sound, and one it did not:

* **a model to ``.glb``** - glTF binary, which Blender 5 imports with nothing
  installed: the mesh with its parts, its skeleton, its skin, its texture and
  any of its loose animations, in one file. MilkShape is not offered: it is a
  2008 program, and the community's own pipeline (the Blender addon in
  ``Reference/``) lives in Blender now.
* **a model to ``.obj``**, zipped with its ``.mtl`` and texture, for anything
  that reads nothing better. Geometry and UVs only - OBJ has no skeleton.
* **``.texture`` to and from ``.dds``**, over :mod:`unittransfer.sprites`,
  whose 48-byte header this measured on 45 340 of the 45 342 ``.texture``
  files in the two installed mods (the other two are bare DDS under that name,
  and come back as they are).

What is not here, and why: **writing a ``.mesh``**. The reference's encoder
writes a layout no real file has (``mesh.py``'s docstring); a real one is a
boost archive whose class bookkeeping IWTE writes, and building one is its own
job. ``.glb`` goes out; nothing comes back in.

The space conversion, the one thing every exporter gets wrong once
------------------------------------------------------------------
M2TW is left-handed (+X right, +Y up, +Z forward - ``mesh.py``); glTF is
right-handed. Mirroring X converts one to the other, and a mirror has three
consequences, all applied here: every position, normal, pivot and
translation key has x negated; every triangle's winding is reversed, or the
faces point inward; and every rotation ``(x, y, z, w)`` becomes
``(x, -y, -z, w)`` - a rotation seen in a mirror across X.

The texture is the viewer's: main and attachment sheets glued side by side
when the entry names a real pair, and ``u`` scaled by the same 0.5 or 1.0 the
viewer uses (``v3Apply``). glTF puts ``v`` = 0 at the top of an image, as
Direct3D does, so ``v`` goes out untouched; OBJ puts it at the bottom, so
there it is flipped.
"""
from __future__ import annotations

import io
import json
import struct
import zipfile
from array import array
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import casanim, mesh, sprites


class ExportError(ValueError):
    pass


# ---------------------------------------------------------------------------
# textures


def texture_to_dds(data: bytes) -> bytes:
    """A ``.texture`` as the DDS inside it; a bare DDS comes back unchanged."""
    if data[:4] == b"DDS ":
        return data
    if data[sprites.TEXTURE_HEADER_LEN:sprites.TEXTURE_HEADER_LEN + 4] != b"DDS ":
        raise ExportError("this is not a .texture - there is no DDS image 48 bytes in, "
                          "where every one of the game's has it")
    return sprites.texture_to_dds(data)


def dds_to_texture(data: bytes) -> bytes:
    if data[:4] != b"DDS ":
        raise ExportError("this is not a DDS image - it does not open with 'DDS '")
    return sprites.dds_to_texture(data)


def glue(main_png: bytes, attach_png: Optional[bytes]) -> bytes:
    """The two sheets as the one image the UVs address: main on the left,
    attachment scaled into the right half. One sheet comes back as it is."""
    from PIL import Image
    if not attach_png:
        return main_png
    a = Image.open(io.BytesIO(main_png)).convert("RGBA")
    b = Image.open(io.BytesIO(attach_png)).convert("RGBA").resize(a.size)
    out = Image.new("RGBA", (a.width * 2, a.height))
    out.paste(a, (0, 0))
    out.paste(b, (a.width, 0))
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# the skeleton


def _mirror(v) -> Tuple[float, float, float]:
    return (-float(v[0]), float(v[1]), float(v[2]))


def _mirror_q(q) -> Tuple[float, float, float, float]:
    x, y, z, w = (float(c) for c in q)
    n = (x * x + y * y + z * z + w * w) ** 0.5 or 1.0
    return (x / n, -y / n, -z / n, w / n)


def _bind_world(skel: casanim.Animation) -> List[Tuple[float, float, float]]:
    out: List[Tuple[float, float, float]] = []
    for i, t in enumerate(skel.tracks):
        par = out[t.parent] if 0 <= t.parent < i else (0.0, 0.0, 0.0)
        out.append(tuple(par[k] + t.pivot[k] for k in range(3)))
    return out


def bone_map(bones: Sequence[str], skel: casanim.Animation) -> List[int]:
    """The model's bones -> skeleton tracks by name; the viewer's rule, so a
    bone the skeleton lacks goes with the pelvis (``v3aBoneMap``)."""
    names = {t.name.lower(): i for i, t in enumerate(skel.tracks)}
    hub = next((i for i, t in enumerate(skel.tracks) if t.parent == 0), 0)
    return [names.get(b.lower(), hub) for b in bones]


# ---------------------------------------------------------------------------
# glTF


class _Bin:
    """The binary chunk and the accessors into it."""

    def __init__(self):
        self.data = bytearray()
        self.views: List[dict] = []
        self.accessors: List[dict] = []

    def view(self, raw: bytes, target: Optional[int] = None) -> int:
        while len(self.data) % 4:
            self.data.append(0)
        v = {"buffer": 0, "byteOffset": len(self.data), "byteLength": len(raw)}
        if target:
            v["target"] = target
        self.data += raw
        self.views.append(v)
        return len(self.views) - 1

    def accessor(self, raw: bytes, ctype: int, count: int, kind: str,
                 target: Optional[int] = None, minmax: Optional[Tuple[list, list]] = None) -> int:
        a = {"bufferView": self.view(raw, target), "componentType": ctype,
             "count": count, "type": kind}
        if minmax:
            a["min"], a["max"] = minmax
        self.accessors.append(a)
        return len(self.accessors) - 1


FLOAT, UBYTE, USHORT = 5126, 5121, 5123
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


def export_glb(m: mesh.MeshFile, *, name: str = "model",
               groups: Optional[Sequence[int]] = None,
               skeleton: Optional[casanim.Animation] = None,
               animations: Sequence[Tuple[str, casanim.Animation]] = (),
               texture_png: Optional[bytes] = None, uscale: float = 0.5) -> bytes:
    """One model as a ``.glb``. ``groups`` picks the parts (default all);
    ``skeleton`` is any of its skeleton's animations - each carries the pivots -
    and without one the model goes out static, as a ``.mesh`` with no
    animation file to hand is."""
    n = m.vertices
    if not n:
        raise ExportError("this model has no vertices")
    b = _Bin()
    pos = array("f", m.positions)
    for i in range(0, len(pos), 3):
        pos[i] = -pos[i]
    lo = [min(pos[k::3]) for k in range(3)]
    hi = [max(pos[k::3]) for k in range(3)]
    attrs = {"POSITION": b.accessor(pos.tobytes(), FLOAT, n, "VEC3", ARRAY_BUFFER, (lo, hi))}
    if m.normals:
        nrm = array("f", m.normals)
        for i in range(0, len(nrm), 3):
            nrm[i] = -nrm[i]
            # the model ships a few zero normals (lamedon_clansmen has two);
            # glTF wants unit length, and straight up is as honest as anything
            if abs(nrm[i]) + abs(nrm[i + 1]) + abs(nrm[i + 2]) < 0.05:
                nrm[i], nrm[i + 1], nrm[i + 2] = 0.0, 1.0, 0.0
            else:
                ln = (nrm[i] ** 2 + nrm[i + 1] ** 2 + nrm[i + 2] ** 2) ** 0.5
                nrm[i] /= ln; nrm[i + 1] /= ln; nrm[i + 2] /= ln
        attrs["NORMAL"] = b.accessor(nrm.tobytes(), FLOAT, n, "VEC3", ARRAY_BUFFER)
    if m.uvs:
        uv = array("f", m.uvs)
        for i in range(0, len(uv), 2):
            uv[i] *= uscale
        attrs["TEXCOORD_0"] = b.accessor(uv.tobytes(), FLOAT, n, "VEC2", ARRAY_BUFFER)

    gltf: Dict = {"asset": {"version": "2.0", "generator": "Medieval 2 GUI Toolkit"},
                  "scene": 0, "scenes": [{"name": name, "nodes": []}], "nodes": [],
                  "meshes": [], "buffers": [], "bufferViews": b.views, "accessors": b.accessors}

    skinned = bool(skeleton and m.weights and len(m.bone_ids) == n * 4 and m.bones)
    joint_nodes: List[int] = []
    if skinned:
        bmap = bone_map(m.bones, skeleton)
        joints = bytearray(n * 4)
        weights = array("f", bytes(n * 16))
        hub = next((i for i, t in enumerate(skeleton.tracks) if t.parent == 0), 0)
        for v in range(n):
            w0, w1 = m.weights[v * 2], m.weights[v * 2 + 1]
            j0 = bmap[m.bone_ids[v * 4 + 2]] if m.bone_ids[v * 4 + 2] < len(bmap) else hub
            j1 = bmap[m.bone_ids[v * 4 + 1]] if m.bone_ids[v * 4 + 1] < len(bmap) else hub
            tot = w0 + w1
            if tot <= 0:
                w0, w1, j0, j1, tot = 1.0, 0.0, hub, hub, 1.0
            joints[v * 4], joints[v * 4 + 1] = j0, j1
            weights[v * 4], weights[v * 4 + 1] = w0 / tot, w1 / tot
        if len(skeleton.tracks) > 255:
            raise ExportError(f"{len(skeleton.tracks)} bones is more than a byte can index")
        attrs["JOINTS_0"] = b.accessor(bytes(joints), UBYTE, n, "VEC4", ARRAY_BUFFER)
        attrs["WEIGHTS_0"] = b.accessor(weights.tobytes(), FLOAT, n, "VEC4", ARRAY_BUFFER)
        # the skeleton as nodes, parents before children as the file has them
        first = len(gltf["nodes"])
        for i, t in enumerate(skeleton.tracks):
            gltf["nodes"].append({"name": t.name, "translation": list(_mirror(t.pivot))})
            joint_nodes.append(first + i)
        for i, t in enumerate(skeleton.tracks):
            if 0 <= t.parent < i:
                gltf["nodes"][first + t.parent].setdefault("children", []).append(first + i)
            else:
                gltf["scenes"][0]["nodes"].append(first + i)
        ibm = array("f")
        for w in _bind_world(skeleton):
            x, y, z = _mirror(w)
            ibm.extend([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1])
        gltf["skins"] = [{"name": skeleton.source and Path(skeleton.source).stem or "skeleton",
                          "joints": joint_nodes, "skeleton": joint_nodes[0],
                          "inverseBindMatrices": b.accessor(ibm.tobytes(), FLOAT,
                                                            len(joint_nodes), "MAT4")}]

    if texture_png:
        img = b.view(texture_png)
        gltf["images"] = [{"bufferView": img, "mimeType": "image/png", "name": name}]
        gltf["samplers"] = [{"wrapS": 10497, "wrapT": 10497, "magFilter": 9729,
                             "minFilter": 9987}]
        gltf["textures"] = [{"sampler": 0, "source": 0}]
        gltf["materials"] = [{"name": name, "doubleSided": True, "alphaMode": "MASK",
                              "alphaCutoff": 0.35,
                              "pbrMetallicRoughness": {"baseColorTexture": {"index": 0},
                                                       "metallicFactor": 0.0,
                                                       "roughnessFactor": 0.9}}]

    prims = []
    chosen = list(range(len(m.groups))) if groups is None else \
        [g for g in groups if 0 <= g < len(m.groups)]
    for gi in chosen:
        g = m.groups[gi]
        if not g.indices:
            continue
        idx = array("H", g.indices)
        for t in range(0, len(idx) - 2, 3):          # the mirror reverses winding
            idx[t + 1], idx[t + 2] = idx[t + 2], idx[t + 1]
        prim = {"attributes": dict(attrs),
                "indices": b.accessor(idx.tobytes(), USHORT, len(idx), "SCALAR",
                                      ELEMENT_ARRAY_BUFFER)}
        if texture_png:
            prim["material"] = 0
        prims.append(prim)
    if not prims:
        raise ExportError("none of the parts asked for has a face")
    gltf["meshes"].append({"name": name, "primitives": prims})
    node = {"name": name, "mesh": 0}
    if skinned:
        node["skin"] = 0
    gltf["nodes"].append(node)
    gltf["scenes"][0]["nodes"].append(len(gltf["nodes"]) - 1)

    if skinned and animations:
        gltf["animations"] = []
        by_name = {t.name.lower(): joint_nodes[i] for i, t in enumerate(skeleton.tracks)}
        for label, anim in animations:
            _animation(gltf, b, label, anim, by_name)
        if not gltf["animations"]:
            del gltf["animations"]

    gltf["buffers"] = [{"byteLength": len(b.data)}]
    return _glb(gltf, bytes(b.data))


def _animation(gltf: dict, b: _Bin, label: str, anim: casanim.Animation,
               by_name: Dict[str, int]) -> None:
    times = list(anim.key_times) or [0.0]
    inputs: Dict[int, int] = {}

    def time_accessor(count: int) -> int:
        if count not in inputs:
            ts = array("f", times[:count] if count > 1 else [0.0])
            inputs[count] = b.accessor(ts.tobytes(), FLOAT, len(ts), "SCALAR",
                                       minmax=([min(ts)], [max(ts)]))
        return inputs[count]

    samplers, channels = [], []
    for t in anim.tracks:
        node = by_name.get(t.name.lower())
        if node is None:
            continue
        if t.rot_keys:
            q = array("f")
            for k in range(t.rot_keys):
                q.extend(_mirror_q(t.rot[k * 4:k * 4 + 4]))
            samplers.append({"input": time_accessor(t.rot_keys), "interpolation": "LINEAR",
                             "output": b.accessor(q.tobytes(), FLOAT, t.rot_keys, "VEC4")})
            channels.append({"sampler": len(samplers) - 1,
                             "target": {"node": node, "path": "rotation"}})
        if t.pos_keys:
            p = array("f")
            for k in range(t.pos_keys):
                p.extend(_mirror([t.pivot[c] + t.pos[k * 3 + c] for c in range(3)]))
            samplers.append({"input": time_accessor(t.pos_keys), "interpolation": "LINEAR",
                             "output": b.accessor(p.tobytes(), FLOAT, t.pos_keys, "VEC3")})
            channels.append({"sampler": len(samplers) - 1,
                             "target": {"node": node, "path": "translation"}})
    if channels:
        gltf["animations"].append({"name": label, "samplers": samplers, "channels": channels})


def _glb(gltf: dict, binary: bytes) -> bytes:
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    binary += b"\x00" * (-len(binary) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    return b"".join([b"glTF", struct.pack("<II", 2, total),
                     struct.pack("<I", len(js)), b"JSON", js,
                     struct.pack("<I", len(binary)), b"BIN\x00", binary])


def read_glb(data: bytes) -> Tuple[dict, bytes]:
    """A ``.glb``'s JSON and binary chunk - for the tests, and for saying what
    an export holds."""
    if data[:4] != b"glTF":
        raise ExportError("not a .glb")
    _v, total = struct.unpack_from("<II", data, 4)
    jl, = struct.unpack_from("<I", data, 12)
    js = json.loads(data[20:20 + jl])
    at = 20 + jl
    bl, = struct.unpack_from("<I", data, at)
    return js, data[at + 8:at + 8 + bl]


# ---------------------------------------------------------------------------
# OBJ


def export_obj_zip(m: mesh.MeshFile, *, name: str = "model",
                   groups: Optional[Sequence[int]] = None,
                   texture_png: Optional[bytes] = None, uscale: float = 0.5) -> bytes:
    """``<name>.obj`` with its ``.mtl`` and texture, zipped. Mirrored into the
    same right-handed space as the ``.glb``; ``v`` flipped, since OBJ counts it
    from the bottom of the image."""
    lines = [f"# {name} - exported by the Medieval 2 GUI Toolkit",
             f"mtllib {name}.mtl"]
    p, nr, uv = m.positions, m.normals, m.uvs
    for v in range(m.vertices):
        lines.append(f"v {-p[v * 3]:.6f} {p[v * 3 + 1]:.6f} {p[v * 3 + 2]:.6f}")
    for v in range(m.vertices if uv else 0):
        lines.append(f"vt {uv[v * 2] * uscale:.6f} {1.0 - uv[v * 2 + 1]:.6f}")
    for v in range(m.vertices if nr else 0):
        lines.append(f"vn {-nr[v * 3]:.6f} {nr[v * 3 + 1]:.6f} {nr[v * 3 + 2]:.6f}")
    chosen = list(range(len(m.groups))) if groups is None else groups
    for gi in chosen:
        g = m.groups[gi]
        lines.append(f"o {g.name}__{g.texture_group}")
        lines.append("usemtl skin")
        ix = g.indices

        def ref(i):
            i += 1
            if uv and nr:
                return f"{i}/{i}/{i}"
            return f"{i}/{i}" if uv else (f"{i}//{i}" if nr else f"{i}")
        for t in range(0, len(ix) - 2, 3):
            lines.append(f"f {ref(ix[t])} {ref(ix[t + 2])} {ref(ix[t + 1])}")
    mtl = ["newmtl skin", "Kd 1 1 1"]
    if texture_png:
        mtl += [f"map_Kd {name}.png", f"map_d {name}.png"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}.obj", "\n".join(lines) + "\n")
        z.writestr(f"{name}.mtl", "\n".join(mtl) + "\n")
        if texture_png:
            z.writestr(f"{name}.png", texture_png)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# from a modeldb entry, the way the viewer shows it


def texture_case(skin: Optional[dict]) -> Tuple[str, float]:
    """The viewer's three shapes (``v3TexCase``): ``pair`` glued, ``solo`` (no
    attachment named, one sheet spanning both units) and ``self`` (an
    attachment named that is the main file again, or not shipped), with the
    ``u`` scale each one takes."""
    if not skin or not skin.get("rel"):
        return "none", 0.5
    att = (skin.get("attach") or "").strip()
    if not att:
        return "solo", 0.5
    if skin.get("attach_exists") and att.lower() != skin["rel"].strip().lower():
        return "pair", 0.5
    return "self", 1.0


def entry_export(mod, entry, *, fmt: str, lod: int = 0, skin: int = 0,
                 groups: Optional[Sequence[int]] = None, skel: int = 0,
                 actions: Sequence[str] = (), png_of=None) -> Tuple[bytes, str, str]:
    """One modeldb entry as ``(bytes, filename, mime type)``.

    ``png_of(rel)`` is the server's texture reader (the icon cache), so the
    export draws exactly the sheet the viewer drew. ``actions`` names the
    skeleton's actions to put in a ``.glb``; ``*`` is every loose one. The
    skeleton itself comes from the skeleton's ``default`` action when that is
    loose, else from the first loose action - each file carries the pivots."""
    from . import factions
    rels = entry.mesh_files()
    if not 0 <= lod < len(rels):
        raise ExportError(f"{entry.name} has no LOD {lod}")
    src = factions.picture_path(mod, rels[lod])
    if src is None or not src.is_file():
        raise ExportError(f"{rels[lod]} is not in this mod")
    m = mesh.read_mesh(src)
    view = mesh.entry_view(entry, Path(mod.data))
    skins = view.get("skins") or []
    s = skins[skin] if 0 <= skin < len(skins) else None
    case, uscale = texture_case(s)
    png = None
    if png_of and s and s.get("exists"):
        main = png_of(s["rel"])
        att = png_of(s["attach"]) if case == "pair" else None
        png = glue(main, att) if main else None
    name = entry.name
    if fmt == "obj":
        return (export_obj_zip(m, name=name, groups=groups, texture_png=png, uscale=uscale),
                f"{name}_obj.zip", "application/zip")
    if fmt != "glb":
        raise ExportError(f"no export called {fmt!r}")
    skeleton, anims = None, []
    skels = [x for x in dict.fromkeys(entry.skeletons()) if x]
    if skels and m.weights:
        av = casanim.actions_view(mod.data, [skels[min(max(skel, 0), len(skels) - 1)]])
        rows = [r for r in (av["skeletons"][0]["actions"] if av["skeletons"] else []) if r["rel"]]
        data = Path(mod.data)
        base = next((r for r in rows if r["action"].lower() == "default"), rows[0] if rows else None)
        sk_name = av["skeletons"][0]["skeleton"] if av["skeletons"] else ""
        if base:
            try:
                skeleton = casanim.read_anim(data / base["rel"], sk_name, data)
            except casanim.AnimError:
                skeleton = None
        want = {a.lower() for a in actions}
        seen = set()
        for r in rows:
            if ("*" in want or r["action"].lower() in want) and r["rel"] not in seen:
                seen.add(r["rel"])
                try:
                    anims.append((r["action"], casanim.read_anim(data / r["rel"], sk_name, data)))
                except casanim.AnimError:
                    pass
    return (export_glb(m, name=name, groups=groups, skeleton=skeleton, animations=anims,
                       texture_png=png, uscale=uscale),
            f"{name}.glb", "model/gltf-binary")
