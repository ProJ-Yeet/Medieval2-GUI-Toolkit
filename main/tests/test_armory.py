"""Armory Studio's server side - unittransfer/armory.py (Phase 95e on).

  * object names in the Blender kit's form split into type, mesh and flag;
  * external models: a .glb and an .obj out of this toolkit's own exporters
    come back as the same triangles, and a hand-written COLLADA file with Z up
    and a skin is read into the game's space with its two strongest weights;
  * duplicates: the same art through an .obj's six decimals still matches;
  * a real mod's catalogue and one entry as an asset;
  * the export (95i): the check, the dye against the page's, a stamp, and the
    reference horse packed and baked, every vertex reading the texel it read.
  * normal maps (95j): the generator's direction and strength, the page's
    preview against the bake, Skip flat and Specialized per material.
  * into a mod (95k): role templates measured on a mod, and a new entry, a
    unit's new soldier model and a new unit from a template, each undoable.
  * the asset library (95l): kept once by place or by bytes, saved whole, and
    sorted by the units that wear each entry.
  * unit cards (95m): a card saved as the game names it, the outline's growth
    and the finish's colour steps.
"""
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import armory, mesh, modelexport
from tests import _realmod, _tmp

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


tmp = Path(_tmp.mkdtemp("ut_armory_"))
armory.ARMORY_DIR = tmp / "armory"
armory.PROJECT = armory.ARMORY_DIR / "project.json"
armory.SHEETS_DIR = armory.ARMORY_DIR / "sheets"

REFERENCE = (ROOT / "Reference" / "TWCenter" / "--- TOOLS n RESOURCES ---" /
             "TEMPLATE - Barded-Mailed Horses" / "Barded-Mailed Horses")

# ---------------------------------------------------------------------------
print("\nObject names")

check("Body__horse_body_01__opt is Body, horse_body_01, optional",
      armory.split_name("Body__horse_body_01__opt") == ("Body", "horse_body_01", 1))
check("a trailing .001 goes", armory.split_name("Head__head_01.001") == ("Head", "head_01", 0))
check("a name not in the kit's form is its own type and mesh",
      armory.split_name("Cube.002") == ("Cube", "Cube", 0))


def tri_positions(m, g):
    return [m.positions[i * 3 + k] for i in g.indices for k in range(3)]


# ---------------------------------------------------------------------------
print("\nExternal models")

horse_path = REFERENCE / "mount_barded_horse_lod0.mesh"
horse = mesh.read_mesh(horse_path) if horse_path.is_file() else None
if horse is not None:
    glb = tmp / "horse.glb"
    glb.write_bytes(modelexport.export_glb(horse, name="horse"))
    view = armory.external_view(str(glb))
    back = armory.external_by_id(view["id"])[0]
    check(f"a .glb comes back with every triangle ({view['triangles']} of {horse.triangles})",
          view["triangles"] == horse.triangles and len(view["objects"]) == len(horse.groups))
    worst = max(max(abs(a - b) for a, b in zip(tri_positions(back, g1), tri_positions(horse, g0)))
                for g0, g1 in zip(horse.groups, back.groups))
    check(f"in the game's space, winding and all ({worst:.1e})", worst < 1e-5)
    check("each object takes only its own vertices",
          back.vertices <= horse.vertices * 1.01)

    z = zipfile.ZipFile(io.BytesIO(modelexport.export_obj_zip(horse, name="horse")))
    z.extractall(tmp / "obj")
    view = armory.external_view(str(tmp / "obj" / "horse.obj"))
    back = armory.external_by_id(view["id"])[0]
    check("an .obj's objects take their kit names: type and mesh",
          [(o["name"], o["mesh"]) for o in view["objects"]]
          == [(g.name, g.texture_group) for g in horse.groups])
    worst = max(max(abs(a - b) for a, b in zip(tri_positions(back, g1), tri_positions(horse, g0)))
                for g0, g1 in zip(horse.groups, back.groups))
    check(f"and the same triangles to the .obj's six decimals ({worst:.1e})", worst < 2e-6)
    # duplicates: the fingerprint can miss a copy through six decimals, the
    # shape cannot
    orig = armory._objects(horse)
    same = sum(1 for a, b in zip(orig, view["objects"])
               if a["shape"][0] == b["shape"][0]
               and all(abs(a["shape"][i] - b["shape"][i]) <= 1e-4 for i in range(1, 5)))
    check(f"every object's shape matches its original ({same} of {len(orig)})", same == len(orig))


def side_glb(generator):
    """One triangle weighted to bone_Rhand, out at glTF +x and +z, the way
    Blender and IWTE write a soldier's right hand: on the game's +x side."""
    import struct as _s
    pos = _s.pack("<9f", 0.8, 0.5, 0.1, 0.9, 0.5, 0.1, 0.8, 0.6, 0.1)
    nrm = _s.pack("<9f", *(0.0, 0.0, 1.0) * 3)
    joints = bytes((1, 0, 0, 0) * 3)
    weights = _s.pack("<12f", *(1.0, 0.0, 0.0, 0.0) * 3)
    binary = pos + nrm + joints + weights
    views = [{"buffer": 0, "byteOffset": o, "byteLength": n}
             for o, n in ((0, 36), (36, 36), (72, 12), (84, 48))]
    accessors = [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                 {"bufferView": 1, "componentType": 5126, "count": 3, "type": "VEC3"},
                 {"bufferView": 2, "componentType": 5121, "count": 3, "type": "VEC4"},
                 {"bufferView": 3, "componentType": 5126, "count": 3, "type": "VEC4"}]
    gltf = {"asset": {"version": "2.0", "generator": generator},
            "buffers": [{"byteLength": len(binary)}], "bufferViews": views, "accessors": accessors,
            "meshes": [{"name": "hand", "primitives": [{"attributes": {
                "POSITION": 0, "NORMAL": 1, "JOINTS_0": 2, "WEIGHTS_0": 3}}]}],
            "nodes": [{"name": "bone_pelvis", "children": [1]},
                      {"name": "bone_Rhand", "translation": [0.76, 0.51, 0.01]},
                      {"name": "Hand__glove", "mesh": 0, "skin": 0}],
            "skins": [{"joints": [0, 1]}], "scenes": [{"nodes": [0, 2]}]}
    return modelexport._glb(gltf, binary)


for generator in ("Khronos glTF Blender I/O v5.2.41", "IWTE_v26_05_A"):
    p = tmp / "side.glb"
    p.write_bytes(side_glb(generator))
    got = armory.external_by_id(armory.external_view(str(p))["id"])[0]
    xs, zs = got.positions[0::3], got.positions[2::3]
    check(f"a {generator.split()[0]} .glb's right hand stays on the game's +x side, "
          f"z mirrored ({min(xs):.2f}, {max(zs):.2f})", min(xs) > 0.7 and max(zs) < -0.09)
    n = got.normals[2]
    check(f"  and its normal is mirrored with it ({n:+.1f})", n < -0.99)

DAE = """<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
 <asset><up_axis>Z_UP</up_axis></asset>
 <library_images><image id="skin_png"><init_from>skin.png</init_from></image></library_images>
 <library_effects><effect id="mat-effect"><profile_COMMON>
  <newparam sid="s"><surface type="2D"><init_from>skin_png</init_from></surface></newparam>
 </profile_COMMON></effect></library_effects>
 <library_materials><material id="mat"><instance_effect url="#mat-effect"/></material></library_materials>
 <library_geometries><geometry id="g" name="Shield__shield_01__opt"><mesh>
  <source id="p"><float_array id="pa" count="9">0 0 0 1 0 0 0 0 1</float_array>
   <technique_common><accessor source="#pa" count="3" stride="3"/></technique_common></source>
  <source id="n"><float_array id="na" count="3">0 -1 0</float_array>
   <technique_common><accessor source="#na" count="1" stride="3"/></technique_common></source>
  <source id="t"><float_array id="ta" count="6">0 0 1 0 0 1</float_array>
   <technique_common><accessor source="#ta" count="3" stride="2"/></technique_common></source>
  <vertices id="v"><input semantic="POSITION" source="#p"/></vertices>
  <triangles material="m" count="1">
   <input semantic="VERTEX" source="#v" offset="0"/><input semantic="NORMAL" source="#n" offset="1"/>
   <input semantic="TEXCOORD" source="#t" offset="2" set="0"/>
   <p>0 0 0 1 0 1 2 0 2</p></triangles>
 </mesh></geometry></library_geometries>
 <library_controllers><controller id="c"><skin source="#g">
  <source id="j"><Name_array id="ja" count="3">bone_pelvis bone_head bone_shield</Name_array></source>
  <source id="w"><float_array id="wa" count="4">1 0.6 0.3 0.1</float_array></source>
  <joints><input semantic="JOINT" source="#j"/></joints>
  <vertex_weights count="3"><input semantic="JOINT" source="#j" offset="0"/><input semantic="WEIGHT" source="#w" offset="1"/>
   <vcount>1 3 1</vcount><v>0 0 1 1 2 2 0 3 2 0</v></vertex_weights>
 </skin></controller></library_controllers>
 <library_visual_scenes><visual_scene id="s"><node><instance_controller url="#c">
  <bind_material><technique_common><instance_material symbol="m" target="#mat"/></technique_common></bind_material>
 </instance_controller></node></visual_scene></library_visual_scenes>
</COLLADA>"""
(tmp / "dae").mkdir()
(tmp / "dae" / "part.dae").write_text(DAE, encoding="utf-8")
from PIL import Image
Image.new("RGBA", (8, 8), (200, 40, 40, 255)).save(tmp / "dae" / "skin.png")
view = armory.external_view(str(tmp / "dae" / "part.dae"))
m = armory.external_by_id(view["id"])[0]
o = view["objects"][0]
check("a .dae object takes its kit name", (o["name"], o["mesh"], o["flag"]) == ("Shield", "shield_01", 1))
check("its texture is found beside it", Path(o["texture_file"]).name == "skin.png")
# Z up: (1,0,0) stays x; (0,0,1) is up; then x is mirrored for the game
check("Z up is turned to Y up and x mirrored",
      [round(v, 4) for v in m.positions] == [0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
check("and the winding reversed with it", list(m.groups[0].indices) == [0, 2, 1])
check("v counts from the top, as in the game", [round(v, 4) for v in m.uvs[1::2]] == [1.0, 1.0, 0.0])
check("the skin's bones are named", set(m.bones) == {"bone_pelvis", "bone_head", "bone_shield"})
w1 = (round(m.weights[2], 3), round(m.weights[3], 3))
check(f"the second vertex keeps its two strongest weights, made whole {w1}", w1 == (0.667, 0.333))
first = m.bones[m.bone_ids[4 + 2]]
check(f"and the heavier one's bone is in the third byte ({first})", first == "bone_head")

# ---------------------------------------------------------------------------
print("\nObjects (95f)")

if horse is not None:
    shutil.copy(horse_path, tmp / "horse.mesh")
    # the reference horse, loose on disk, stands in for an asset
    assets = {"ext|" + str(tmp / "horse.mesh").lower(): {"kind": "external", "path": str(tmp / "horse.mesh")}}
    key = next(iter(assets))
    src = armory.asset_mesh(assets[key], None)
    whole = {"id": 1, "name": "Body", "mesh": "b", "src": [{"asset": key, "group": 1}],
             "t": [0, 0, 0], "r": [0, 0, 0], "s": [1, 1, 1]}
    om = armory.object_mesh(whole, assets, None)
    g = src.groups[1]
    check(f"an object of one whole group has its triangles ({om.triangles} of {g.triangles})",
          om.triangles == g.triangles)
    check("and only the vertices they use", om.vertices == len(set(g.indices)))
    moved = dict(whole, t=[0.5, 0, 0], s=[2, 2, 2], r=[0, 90, 0])
    mm = armory.object_mesh(moved, assets, None)
    c0 = [sum(om.positions[i::3]) / om.vertices for i in range(3)]
    c1 = [sum(mm.positions[i::3]) / mm.vertices for i in range(3)]
    check("moved by its own t, about its own centre", abs(c1[0] - c0[0] - 0.5) < 0.05 and abs(c1[1] - c0[1]) < 0.05)
    lo0, hi0 = om.bounds()
    lo1, hi1 = mm.bounds()
    check("scaled 2 and turned 90 about y: x and z swap their extents, doubled",
          abs((hi1[0] - lo1[0]) - 2 * (hi0[2] - lo0[2])) < 0.02
          and abs((hi1[2] - lo1[2]) - 2 * (hi0[0] - lo0[0])) < 0.02)
    half = dict(whole, src=[{"asset": key, "group": 1, "tris": list(range(0, g.triangles, 2))}])
    check("a split piece holds only its triangles",
          armory.object_mesh(half, assets, None).triangles == len(range(0, g.triangles, 2)))
    # 100m: UVs moved in the UV editor ride on the piece, by asset vertex
    first_v = sorted(set(g.indices))[0]
    moved_uv = dict(whole, src=[{"asset": key, "group": 1, "uv": {str(first_v): [0.25, 0.75]}}])
    mu = armory.object_mesh(moved_uv, assets, None)
    check("a moved UV reaches the object as the export reads it, the rest as they were",
          (mu.uvs[0], mu.uvs[1]) == (0.25, 0.75) and list(mu.uvs[2:]) == list(om.uvs[2:]))
    xf = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 2, 0, 1]
    up = dict(whole, src=[{"asset": key, "group": 1, "xf": xf}])
    cu = armory.object_mesh(up, assets, None).bounds()
    check("a merged piece keeps its own matrix (2 up)", abs(cu[0][1] - lo0[1] - 2) < 1e-4)

    # transfer weights: the horse's head, its weights taken away, takes them
    # back from the rest of the horse
    head_i = next(i for i, gg in enumerate(horse.groups) if gg.name == "Head")
    project = {"assets": list(assets.values()), "objects": [
        {"id": i + 1, "name": gg.name, "mesh": gg.texture_group, "src": [{"asset": key, "group": i}],
         "t": [0, 0, 0], "r": [0, 0, 0], "s": [1, 1, 1]} for i, gg in enumerate(src.groups)]}
    own = armory.object_mesh(project["objects"][head_i], assets, None)
    got = armory.transfer_for(project, head_i + 1, "face", None)
    check(f"weights transferred for every vertex ({got['n']})", got["n"] == own.vertices)
    project["objects"][head_i]["weights"] = got
    back = armory.object_mesh(project["objects"][head_i], assets, None)
    first = [back.bones[back.bone_ids[v * 4 + 2]] for v in range(back.vertices)]
    was = [own.bones[own.bone_ids[v * 4 + 2]] for v in range(own.vertices)]
    agree = sum(a.lower() == b.lower() for a, b in zip(first, was)) / len(was)
    check(f"and the head's strongest bone comes back as it was on {agree:.0%} of them", agree > 0.7)

    # 100k: a battle .mesh from disk names no texture; its sheets come out of
    # its folder as the Models Editor's folder view finds them
    from PIL import Image as _Img
    ext = tmp / "ext100k"
    (ext / "textures").mkdir(parents=True, exist_ok=True)
    shutil.copy(horse_path, ext / "horse.mesh")
    _Img.new("RGB", (8, 8), (200, 10, 10)).save(ext / "textures" / "horse_main.png")
    _Img.new("RGB", (8, 8), (10, 10, 200)).save(ext / "textures" / "horse_att.png")
    _id, em, etex = armory.read_external(str(ext / "horse.mesh"))
    want = {i: ("horse_att.png" if g.sheets == "attach" else "horse_main.png") for i, g in enumerate(em.groups)}
    check(f"a .mesh from disk takes the sheets beside it, main or attachment by object ({len(etex)})",
          all(Path(etex[i]).name == want[i] for i in want) and armory.texture_allowed(etex[0]))

    # 100l: a sheet out to edit, written in other formats, and worn by one
    # object in the bake
    src_png = ext / "textures" / "horse_main.png"
    work = armory.sheet_copy(src_png)
    check("a sheet to edit is a PNG copy under the workbench's own folder, allowed to be served",
          work.parent == armory.SHEETS_DIR and work.suffix == ".png" and armory.texture_allowed(str(work)))
    check("and a second Edit opens the same copy", armory.sheet_copy(work) == work and armory.sheet_copy(src_png) == work)
    check("its stamp moves when it is saved", armory.sheet_stamp(str(work)) > 0 and armory.sheet_stamp(str(tmp / "nope.png")) == 0)
    outs = {}
    for suf in (".tga", ".png", ".jpg", ".dds", ".texture"):
        try:
            outs[suf] = armory.export_sheet(work, tmp / "out" / ("s" + suf)).stat().st_size > 0
        except armory.ArmoryError as e:
            outs[suf] = str(e)
    check(f"a sheet written as TGA, PNG, JPG, DDS and .texture ({outs})", all(v is True for v in outs.values()))
    from unittransfer import armbake
    shs = armbake._Sheets(assets, None, armbake.default_image_of)
    worn = shs.paths({"asset": key, "group": 0, "sheet": str(work)})
    check("an object's own sheet stands for both halves of the game's layout in the bake",
          worn == (str(work), str(work)) and shs.paths({"asset": key, "group": 0})[0] != str(work))

    # 100b: rig a whole object to chosen bones
    rig = armory.rig_to_bones(project, [head_i + 1], ["bone_head"], 1.0, None)[str(head_i + 1)]
    project["objects"][head_i]["weights"] = rig
    back = armory.object_mesh(project["objects"][head_i], assets, None)
    check(f"rigged to one bone, every vertex on it at 1.0 ({rig['n']})",
          rig["n"] == own.vertices and {back.bones[back.bone_ids[v * 4 + 2]] for v in range(back.vertices)} == {"bone_head"}
          and all(abs(back.weights[v * 2] - 1) < 1e-6 for v in range(back.vertices)))
    rig = armory.rig_to_bones(project, [head_i + 1], ["bone_head", "bone_torso"], 0.7, None)[str(head_i + 1)]
    project["objects"][head_i]["weights"] = rig
    back = armory.object_mesh(project["objects"][head_i], assets, None)
    check("rigged to two, the first taking the share set",
          back.bones[back.bone_ids[2]] == "bone_head" and back.bones[back.bone_ids[1]] == "bone_torso"
          and abs(back.weights[0] - 0.7) < 1e-6 and abs(back.weights[1] - 0.3) < 1e-6)
    try:
        armory.rig_to_bones(project, [head_i + 1], [], 1.0, None)
        check("no bone is refused", False)
    except armory.ArmoryError:
        check("no bone is refused", True)

    remap, missing = armory.bone_remap(["bone_RThigh", "bone_Rhand", "bone_tail"],
                                       ["bone_rthigh", "bone_rhand", "bone_pelvis"])
    check("bones match across the archer and melee spellings", remap == [0, 1, -1] and missing == ["bone_tail"])

# 100a: transferred weights that tore shields and legs. A strip of quads
# along x, each vertex on the bones given, stands in for a part.
print("\nTransfer weights keeps what it should (100a)")


def strip(xs, bones_of, y=0.0):
    from array import array as _a
    m = mesh.MeshFile(source="t", format="mesh")
    names = []
    w, ids = _a("f"), bytearray()
    for x in xs:
        for z in (0.0, 0.01):
            m.positions.extend((x, y, z))
            b = bones_of(x)
            if b not in names:
                names.append(b)
            w.extend((1.0, 0.0))
            ids += bytes((0, names.index(b), names.index(b), 0))
    m.bones, m.weights, m.bone_ids = names, w, bytes(ids)
    ix = []
    for i in range(len(xs) - 1):
        a = i * 2
        ix += [a, a + 1, a + 2, a + 1, a + 3, a + 2]
    m.groups.append(mesh.MeshGroup("part", "part", ix, 0))
    return m


def tops(res):
    w, ids, names = res
    return [names[ids[v * 4 + 2]] for v in range(len(ids) // 4)]


src = strip([i * 0.01 for i in range(11)], lambda x: "bone_rhand" if x > 0.05 else "bone_relbow")
shield = strip([i * 0.01 for i in range(11)], lambda x: "bone_relbow")
got = tops(armory.transfer_weights(shield, [src], rigid=True,
                                   own=[{"bone_relbow": 1.0}] * shield.vertices))
check(f"a rigid part comes out on one bone, its own where a quarter would take it ({set(got)})",
      set(got) == {"bone_relbow"})
loose = strip([i * 0.01 for i in range(11)], lambda x: "bone_relbow")
got = tops(armory.transfer_weights(loose, [src], rigid=True))
check(f"and on the bone most vertices take when it had none ({set(got)})", len(set(got)) == 1)
foot = strip([0.0, 0.01, 0.30, 0.31], lambda x: "bone_rfoot" if x > 0.1 else "bone_rlowerleg")
own = [{"bone_rfoot" if foot.positions[v * 3] > 0.1 else "bone_rlowerleg": 1.0} for v in range(foot.vertices)]
shin = strip([0.0, 0.01, 0.02], lambda x: "bone_rlowerleg")
got = tops(armory.transfer_weights(foot, [shin, strip([0.5, 0.51], lambda x: "bone_rfoot", y=1.0)],
                                   own=own, smooth=0))
check(f"a vertex no source reaches keeps its own bone ({got})", got[-1].lower() == "bone_rfoot")
left = strip([0.0, 0.01], lambda x: "bone_lthigh")
right = strip([0.0, 0.01], lambda x: "bone_rthigh", y=0.001)
got = tops(armory.transfer_weights(left, [right, strip([0.0, 0.01], lambda x: "bone_pelvis", y=0.02),
                                          strip([0.0, 0.01], lambda x: "bone_lthigh", y=1.0)],
                                   own=[{"bone_lthigh": 1.0}] * left.vertices, smooth=0))
check(f"a left vertex takes no right bone, keeping its own where that is all there is ({set(got)})",
      set(got) == {"bone_lthigh"})
hand = strip([0.0, 0.01], lambda x: "bone_lhand")
got = tops(armory.transfer_weights(hand, [strip([0.0, 0.01], lambda x: "bone_lelbow", y=0.001)],
                                   own=[{"bone_lhand": 1.0}] * hand.vertices, smooth=0))
check(f"a bone no source carries is kept ({set(got)})", set(got) == {"bone_lhand"})
# 100n: Optimize, on a tetrahedron with a face wound the wrong way, a
# duplicate corner and the triangle that duplicate makes degenerate
print("\nOptimize (100n)")
tet = tmp / "tet100n.obj"
tet.write_text("\n".join([
    "v 0 0 0", "v 1 0 0", "v 0 1 0", "v 0 0 1", "v 0 0 0",
    "f 1 3 2", "f 1 2 4", "f 5 4 3", "f 2 4 3", "f 1 5 2"]) + "\n", encoding="utf-8")
ta = {"kind": "external", "path": str(tet)}
tkey = armory.asset_key(ta)
tproj = {"assets": [ta], "objects": [{"id": 1, "name": "Body", "mesh": "tet", "src": [{"asset": tkey, "group": 0}],
                                      "t": [0, 0, 0], "r": [0, 0, 0], "s": [1, 1, 1]}]}
res = armory.optimize(tproj, [1], {"merge": True, "merge_distance": 0.0001, "degenerate": True,
                                   "outside": True, "reset_normals": True}, None)
cnt = res["counts"]
check(f"a duplicate corner merged, the triangle it collapses dropped, the backward face turned ({cnt})",
      cnt["merged"] == 1 and cnt["degenerate"] == 1 and cnt["flipped"] == 1 and cnt["normals"] == 4)
ch = res["objects"]["1"]["pieces"][0]
tproj["objects"][0]["src"][0].update({k: v for k, v in ch.items() if v is not None})
tm = armory.object_mesh(tproj["objects"][0], armory.project_assets(tproj), None)
ix = list(tm.groups[0].indices)
faces = [tuple(ix[i:i + 3]) for i in range(0, len(ix), 3)]
edges = {}
for a, b, c in faces:
    for e in ((a, b), (b, c), (c, a)):
        edges[e] = edges.get(e, 0) + 1
check(f"what it comes to is a closed shape of four faces, every edge run once each way ({len(faces)}, {tm.vertices} vertices)",
      len(faces) == 4 and tm.vertices == 4 and all(edges.get((b, a)) == 1 for (a, b) in edges))
again = armory.optimize(tproj, [1], {"merge": True, "degenerate": True, "outside": True}, None)["counts"]
check(f"and a second run finds nothing more to do ({again})", again["merged"] == 0 and again["degenerate"] == 0 and again["flipped"] == 0 and again["loose"] == 0)

cape = tmp / "cape100n.obj"
cape.write_text("\n".join([
    "v 0 0 0", "v 1 0 0", "v 1 1 0", "v 0 1 0",
    "v 0 0 0.01", "v 1 0 0.01", "v 1 1 0.01", "v 0 1 0.01",
    "f 1 2 3", "f 1 3 4", "f 5 7 6", "f 5 8 7"]) + "\n", encoding="utf-8")
ca = {"kind": "external", "path": str(cape)}
cproj = {"assets": [ca], "objects": [{"id": 1, "name": "Cape", "mesh": "cape", "src": [{"asset": armory.asset_key(ca), "group": 0}],
                                      "t": [0, 0, 0], "r": [0, 0, 0], "s": [1, 1, 1]}]}
cc = armory.optimize(cproj, [1], {"outside": True}, None)["counts"]
check(f"a doubled cape, its two layers facing apart on purpose, is left as it is ({cc['flipped']} turned)", cc["flipped"] == 0)

import re as _re
_js = (ROOT / "web" / "js" / "armobj.js").read_text(encoding="utf-8")
_page = _re.findall(r"'(bone_\w+)'", _js[_js.index("const ARM_BONES"):_js.index("];", _js.index("const ARM_BONES"))])
check("the page lists the bones in the server's order, head, torso, pelvis, right arm, left arm, legs",
      _page == armory.MED2_BONES and armory.MED2_BONES.index("bone_rhand") < armory.MED2_BONES.index("bone_lhand")
      < armory.MED2_BONES.index("bone_rthigh"))
check("bone sides read the Med2 spellings",
      [armory.bone_side(b) for b in ("bone_Lhand", "bone_RThigh", "bone_rfoot", "bone_pelvis", "bone_head")]
      == ["l", "r", "r", "", ""])

import subprocess
node = shutil.which("node")
if node:
    js = (ROOT / "web" / "js" / "armobj.js").read_text(encoding="utf-8")
    probe = ("const tt=x=>x,ttN=x=>x;" + js + ";console.log(JSON.stringify(["
             "armFixName('Cube'),armFixName('sword_blade'),armFixName('hair1'),armFixName('hair_1'),"
             "armFixName('hair__1'),armFixName('Body__body_01.001'),armChannel(0.5,0.5,0.52),"
             "armChannel(0.95,0.95,0.95),armChannel(0.8,0.1,0.1)]))")
    (tmp / "probe.js").write_text(probe, encoding="utf-8")
    out = subprocess.run([node, str(tmp / "probe.js")], capture_output=True, text=True, timeout=60)
    got = __import__("json").loads(out.stdout or "null")
    check(f"the Blender kit's name fix, in the page ({got})",
          got and got[:6] == ["Cube__Cube", "sword__blade", "hair__hair_1", "hair__hair_1",
                              "hair__hair_1", "Body__body_01"])
    check("grey is metal, white is white, red is cloth", got and got[6:] == ["metal", "white", "cloth"])

    # 95g: the viewport's arithmetic, under node with the page's own files
    stub = ("const tt=x=>x,ttN=x=>x,V3_ENV='',state={},overlay=null,api={};"
            "function v3Norm(a){const L=Math.hypot(...a)||1;return a.map(x=>x/L)}")
    js = "".join((ROOT / "web" / "js" / f).read_text(encoding="utf-8") for f in ("armory.js", "armview.js"))
    probe = stub + js + r""";
const same = (a, b) => a.every((x, i) => Math.abs(x - b[i]) < 1e-6);
const angles = [[10, 20, 30], [-45, 60, 5], [0, 89, 0], [170, -30, 100]];
const trip = angles.every(a => { const e = m3euler(m3(...a)); return same(m3(...e).flat(), m3(...a).flat()); });
const keys = [armKeyName({code: 'Numpad1', key: '1'}), armKeyName({code: 'Numpad1', key: '1', ctrlKey: true}),
              armKeyName({code: 'KeyH', key: 'H', altKey: true}), armKeyName({code: 'NumpadDecimal', key: '.'})];
// two objects a metre apart turned 90 about y as one: each turns and they
// trade places about their middle
ARM.assets = new Map();
const o1 = {src: [], t: [1, 0, 0], r: [0, 0, 0], s: [1, 1, 1]}, o2 = {src: [], t: [-1, 0, 0], r: [0, 0, 0], s: [1, 1, 1]};
const snap = armSnapshot([o1, o2]);
armGroupApply(snap, armMedian(snap), 'rotate', m3axis(1, 90));
console.log(JSON.stringify({trip, keys, t1: o1.t.map(v => Math.round(v * 1000) / 1000), r1: o1.r.map(Math.round)}));
"""
    (tmp / "probe2.js").write_text(probe, encoding="utf-8")
    out = subprocess.run([node, str(tmp / "probe2.js")], capture_output=True, text=True, timeout=60)
    got = __import__("json").loads(out.stdout or "null") or {}
    check("a turn goes into degrees and back to the same matrix", got.get("trip"))
    check(f"keys are named as the keymap writes them ({got.get('keys')})",
          got.get("keys") == ["numpad1", "ctrl+numpad1", "alt+h", "numpad."])

    # while an action plays the posed model is lowered to stand where the
    # still one stood; the skeleton drawn over it is lowered with it (it
    # floated a whole hip-height above a Blender soldier)
    probe = (stub + "".join((ROOT / "web" / "js" / f).read_text(encoding="utf-8")
                            for f in ("armory.js", "armview.js", "armanim.js")) + r""";
const bones = [{parent: -1}, {parent: 0}, {parent: 1}], pose = [[0, 0, 0], [0, 0.8, 0], [0, 0.05, 0]];
function v3aPose(){ return pose.map(p => ({p, m: [1,0,0,0,1,0,0,0,1]})); }
function v3aBoneMap(){ return {map: [0, 1, 2], missing: []}; }
function v3aSkin(g, pose, bind, map, outPos, outNrm, shift){ for(let i = 0; i < outPos.length; i += 3) outPos[i + 1] = g.positions[i + 1] + 0.95 + shift[1]; }
function armAnimLength(){ return 0; }
const geo = {positions: new Float32Array([0, -0.96, 0, 0, 0.95, 0]), outPos: new Float32Array(6), outNrm: new Float32Array(6),
             vertices: 2, weights: [1, 0, 1, 0], joints: [1, 0, 1, 0], bones: ['a', 'b', 'c']};
function armVisibleObjects(){ return [{}]; }
function armAnimGeo(){ return geo; }
function armGl(){ return {bindBuffer(){}, bufferSubData(){}, ARRAY_BUFFER: 0}; }
function armToScreen(p){ return [p[0], p[1]]; }
ARM.anim = {data: {bones}, t: 0, tpose: false, travel: [0, 0], bind: pose, carried: false};
ARM.view = {getBoundingClientRect: () => ({left: 0, top: 0, width: 1})}; ARM.bones = true;
armAnimPose();
const dots = [];
armBonesDraw({save(){}, restore(){}, beginPath(){}, moveTo(){}, lineTo(){}, stroke(){}, fill(){},
              arc(x, y){ dots.push(y); }}, 1, 1);
const meshLow = Math.min(geo.outPos[1], geo.outPos[4]);
console.log(JSON.stringify({meshLow: +meshLow.toFixed(3), footY: +dots[1].toFixed(3)}));
"""
             )
    (tmp / "probe2d.js").write_text(probe, encoding="utf-8")
    out2d = subprocess.run([node, str(tmp / "probe2d.js")], capture_output=True, text=True, timeout=60)
    gotd = __import__("json").loads(out2d.stdout or "null") or {}
    check(f"the skeleton is lowered with the posed model it plays ({gotd or out2d.stderr[-200:]})",
          gotd and abs(gotd["footY"] - (0.05 - 0.96)) < 1e-3)

    # armory.js loads even when viewer3d.js has not arrived yet: core.js
    # fetches a dropped file again, but only after the files behind it ran,
    # and armory.js dying on V3_ENV left the Armory Studio button dead
    probe = ("const tt=x=>x,ttN=x=>x,state={},overlay=null,api={};"
             + (ROOT / "web" / "js" / "armory.js").read_text(encoding="utf-8")
             + ";console.log(typeof armGl)")
    (tmp / "probe2a.js").write_text(probe, encoding="utf-8")
    out2a = subprocess.run([node, str(tmp / "probe2a.js")], capture_output=True, text=True, timeout=60)
    check(f"armory.js loads before viewer3d.js has ({(out2a.stdout + out2a.stderr).strip()[-120:]})",
          out2a.stdout.strip() == "function")

    # a sheet whose request the server never saw (a refused connection) is
    # asked for again until it arrives; one the server answers with an error
    # is not, since asking again will not change that answer
    probe = stub + js + r""";
let fetches = 0, refused = 2;
globalThis.Image = class { set src(u){ setTimeout(() => (u.startsWith('blob:') ? this.onload : this.onerror)(), 0); } };
globalThis.URL = {createObjectURL: () => 'blob:x', revokeObjectURL(){}};
globalThis.fetch = async u => {
  fetches++;
  if(u.includes('bad')) return {ok: false, status: 415};
  if(refused-- > 0) throw new TypeError('Failed to fetch');
  return {ok: true, status: 200, blob: async () => ({})};
};
(async () => {
  const out = {};
  try{ await armImage('/api/armory/texture?path=helmet'); out.got = true; }catch(e){ out.got = String(e); }
  out.fetches = fetches; fetches = 0;
  try{ await armImage('/api/armory/texture?path=bad'); out.bad = 'loaded'; }catch(e){ out.bad = 'refused'; }
  out.badFetches = fetches;
  console.log(JSON.stringify(out));
})();
"""
    (tmp / "probe2b.js").write_text(probe, encoding="utf-8")
    out2b = subprocess.run([node, str(tmp / "probe2b.js")], capture_output=True, text=True, timeout=60)
    gotr = __import__("json").loads(out2b.stdout or "null") or {}
    check(f"a sheet lost on the way is fetched again until it arrives ({gotr})",
          gotr.get("got") is True and gotr.get("fetches") == 3)
    check("a sheet the server refuses is asked for once, not forever",
          gotr.get("bad") == "refused" and gotr.get("badFetches") == 1)
    # the allow before it: a lost one made the sheet's own request a 403
    probe = ("const ARM={},ABORTED='__aborted__',enc=encodeURIComponent;let posts=0,lost=2;"
             "const api={post:async()=>{posts++;if(lost-->0)throw new Error('Failed to fetch');return {ok:true};}};"
             + (ROOT / "web" / "js" / "armtex.js").read_text(encoding="utf-8")
             + ";armAllow('C:/a.png').then(()=>console.log(JSON.stringify({posts,allowed:ARM.sheetAllowed.has('C:/a.png')})));")
    (tmp / "probe2c.js").write_text(probe, encoding="utf-8")
    out2c = subprocess.run([node, str(tmp / "probe2c.js")], capture_output=True, text=True, timeout=60)
    gota = __import__("json").loads(out2c.stdout or "null") or {}
    check(f"a lost allow is sent again until the server has it ({gota or out2c.stderr[-200:]})",
          gota.get("posts") == 3 and gota.get("allowed") is True)
    check(f"several objects turn about their middle ({got.get('t1')}, {got.get('r1')})",
          got.get("t1") == [0, 0, -1] and got.get("r1") == [0, 90, 0])
    if out.stderr.strip():
        print("          " + out.stderr.strip().splitlines()[-1][:120])

# ---------------------------------------------------------------------------
print("\nExport: check, UV packing and the bake (95i)")

from unittransfer import armbake
import numpy as np

names = ["Cube", "sword_blade", "hair1", "hair_1", "hair__1", "Body__body_01.001", "Body__b__opt"]
check("the kit's name fix, in Python as in the page",
      [armbake.fix_name(n) for n in names] == ["Cube__Cube", "sword__blade", "hair__hair_1", "hair__hair_1",
                                               "hair__hair_1", "Body__body_01", "Body__b"])

scoped = {"objects": [{"id": 1}, {"id": 2, "hidden": True}, {"id": 3, "coll": 9}, {"id": 4, "coll": 8}],
          "collections": [{"id": 9, "export": True}, {"id": 8, "hidden": True}]}
check("everything visible goes, a hidden object or collection does not",
      [o["id"] for o in armbake.in_scope(scoped, {})] == [1, 3])
check("or only the collections ticked for export",
      [o["id"] for o in armbake.in_scope(scoped, {"mode": "collections"})] == [3])

# the dye in Python against the page's own armDyePixels, pixel for pixel
rng = np.random.default_rng(95)
px = rng.integers(0, 256, size=(24, 24, 4), dtype=np.uint8)
px[..., 3] = 255
px[0, :6, :3] = [[250, 250, 250], [128, 128, 132], [200, 170, 40], [120, 70, 30], [40, 60, 160], [255, 255, 255]]
dyes = [
    {"color": [150, 24, 24], "blend": "keepshade", "strength": 1, "keepWhite": True},
    {"color": [30, 90, 200], "blend": "overlay", "strength": 0.6, "keepWhite": False, "metal": True, "desat": 0.3,
     "channels": {"trim": {"on": True, "color": [220, 190, 60]}, "leather": {"on": True, "color": [90, 50, 20]}}},
    {"color": [10, 120, 40], "blend": "softlight", "strength": 0.8,
     "pattern": {"centers": [[40, 40, 40], [200, 200, 200], [120, 60, 200]], "colors": {"1": [200, 30, 30]}}},
]
for blend in ("multiply", "screen", "hardlight"):
    dyes.append({"color": [70, 140, 210], "blend": blend, "strength": 1})
mats = ["", "fabric", "leather", "metal", "", ""]
py_out = [armbake.dye_pixels(px, d, m)[..., :3].reshape(-1).tolist() for d, m in zip(dyes, mats)]
check("grey is metal, white is white, gold is trim, brown is leather, blue is cloth",
      armbake.channels(px[0:1, :5, :3].astype(float) / 255).tolist()[0] == [0, 1, 2, 3, 4])
if node:
    js = (ROOT / "web" / "js" / "armobj.js").read_text(encoding="utf-8")
    probe = ("const tt=x=>x,ttN=x=>x;" + js + ";const px=" + json.dumps(px.reshape(-1).tolist())
             + ";const dyes=" + json.dumps(dyes) + ";const mats=" + json.dumps(mats) + ";"
             "console.log(JSON.stringify(dyes.map((d,i)=>{const a=Uint8ClampedArray.from(px);"
             "const c=d.pattern&&Object.keys(d.pattern.colors||{}).length?d.pattern.centers:null;"
             "armDyePixels(a,d,mats[i],c);const o=[];for(let k=0;k<a.length;k+=4)o.push(a[k],a[k+1],a[k+2]);return o;})))")
    (tmp / "probe3.js").write_text(probe, encoding="utf-8")
    out = subprocess.run([node, str(tmp / "probe3.js")], capture_output=True, text=True, timeout=60)
    js_out = json.loads(out.stdout or "null") or []
    worst = max((max(abs(a - b) for a, b in zip(p, j)) for p, j in zip(py_out, js_out)), default=999)
    check(f"the bake dyes as the preview does, six dyes on 576 pixels (worst {worst} of 255)",
          len(js_out) == len(py_out) and worst <= 1)

# a stamp lands where it is put: a red square, half the box wide, centred
base = np.zeros((100, 100, 4), np.uint8)
base[..., 3] = 255
stamped = armbake.stamp_pixels(base, Image.new("RGBA", (10, 10), (255, 0, 0, 255)),
                               {"x": 0.5, "y": 0.5, "size": 0.5, "rot": 0, "blend": "normal", "opacity": 1},
                               (20, 20, 80, 80))
red = np.argwhere(stamped[..., 0] > 200)
check(f"an emblem is stamped at its place and size ({red.min(0).tolist()} to {red.max(0).tolist()})",
      red.min(0).tolist() == [35, 35] and red.max(0).tolist() == [64, 64])
half = armbake.stamp_pixels(base, Image.new("RGBA", (10, 10), (255, 0, 0, 255)),
                            {"x": 0.5, "y": 0.5, "size": 0.5, "blend": "normal", "opacity": 0.5}, (20, 20, 80, 80))
check("and its opacity blends it with what is under it", 120 <= int(half[50, 50, 0]) <= 135)

if horse is not None:
    # the reference horse, its one sheet a gradient so every texel says where it was
    W = 512
    yy, xx = np.mgrid[0:W, 0:W]
    grad = np.stack([xx % 256, yy % 256, (xx // 256) * 100 + (yy // 256) * 50 + 20, np.full_like(xx, 255)], -1).astype(np.uint8)
    Image.fromarray(grad).save(tmp / "horse_sheet.png")
    hkey = "ext|" + str(tmp / "horse.mesh").lower()
    hasset = {"kind": "external", "path": str(tmp / "horse.mesh"),
              "textures": {str(i): str(tmp / "horse_sheet.png") for i in range(len(horse.groups))}}
    hproj = {"assets": [hasset], "collections": [], "objects": [
        {"id": i + 1, "name": gg.name, "mesh": gg.texture_group, "flag": gg.flag,
         "src": [{"asset": hkey, "group": i}], "t": [0, 0, 0], "r": [0, 0, 0], "s": [1, 1, 1]}
        for i, gg in enumerate(horse.groups)]}
    res = armbake.check_model(hproj, None)
    check(f"the reference horse passes the check ({[i['code'] for i in res['issues']]})", not res["issues"])
    bad = json.loads(json.dumps(hproj))
    bad["objects"][0].update(name="Cube", mesh="")
    bad["objects"][1].update(name=bad["objects"][2]["name"], mesh=bad["objects"][2]["mesh"])
    bad["objects"][3]["mesh"] = bad["objects"][3]["mesh"] + "_opt"
    codes = {i["code"] for i in armbake.check_model(bad, None, skeleton="fs_archer")["issues"]}
    check(f"an empty name, a clash, _opt in a name and a ranged skeleton's missing weapons are found ({sorted(codes)})",
          {"empty_name", "name_clash", "opt_in_name", "ranged_no_primary", "ranged_no_secondary"} <= codes)

    im_of = lambda p: Image.open(p)
    st = {}
    P = armbake.plan(hproj, None, {}, image_of=im_of, _state=st)
    check(f"every island measured and packed ({P['islands']} islands in {P['blocks']} blocks)",
          P["fits"] and P["islands"] >= P["blocks"] > 0)
    bl = st["blocks"]
    # 99l: art is the same when a texel is under two islands, not when their
    # rectangles cross
    def _texels(b):
        out = set()
        for isl in b.islands:
            m = isl.mask()
            ys, xs = np.nonzero(m)
            out |= set(zip((xs + isl.rect[0]).tolist(), (ys + isl.rect[1]).tolist()))
        return out
    tex = [_texels(b) for b in bl]
    twice = any(a.src[0] == b.src[0] and a.src[2] == b.src[2] and a.dkey == b.dkey and tex[i] & tex[i + 1 + j]
                for i, a in enumerate(bl) for j, b in enumerate(bl[i + 1:]))
    check(f"art that overlaps in its source is packed once ({P['folded']} islands folded into others)",
          P["folded"] > 0 and not twice)
    rect_blocks = 0
    for key in {(i.src[0], i.src[2]) for i in st["islands"]}:
        items = [i for i in st["islands"] if (i.src[0], i.src[2]) == key]
        groups = [[list(i.rect)] for i in items]
        merged = True
        while merged:
            merged = False
            out = []
            for g in groups:
                for o in out:
                    if any(armbake._overlap(a, b) for a in g for b in o):
                        o.extend(g); merged = True; break
                else:
                    out.append(g)
            groups = out
        rect_blocks += len(groups)
    check(f"islands whose rectangles cross but whose texels do not stay apart ({P['blocks']} blocks, {rect_blocks} by rectangles)",
          P["blocks"] >= rect_blocks)
    # no texel of a sheet is taken twice, margins included, and every block
    # is on its sheet (its margin may run past the edge)
    clash, inside = False, True
    for sh, S in st["per"].items():
        if not S["size"]:
            continue
        mg = armbake.margin_px(st["margin_pct"], S["size"])
        taken = np.zeros((S["size"] + 2 * mg, S["size"] + 2 * mg), np.int32)
        for b in S["blocks"]:
            m = b.shape(mg)
            h, w = m.shape
            if b.x < 0 or b.y < 0 or b.x + w > taken.shape[1] or b.y + h > taken.shape[0]:
                inside = False
                continue
            taken[b.y:b.y + h, b.x:b.x + w] += m
        clash = clash or bool((taken > 1).any())
    check("no two blocks' shapes overlap on a sheet", not clash)
    check("and every one is on its sheet", inside)
    nested = any(armbake._overlap((a.x, a.y, a.x + a.shape(0).shape[1], a.y + a.shape(0).shape[0]),
                                  (b.x, b.y, b.x + b.shape(0).shape[1], b.y + b.shape(0).shape[0]))
                 for S in st["per"].values() for i, a in enumerate(S["blocks"]) for b in S["blocks"][i + 1:])
    check("blocks nest: a rectangle reaches into another's empty corner", nested)
    check("the dialog's picture of each sheet comes with the plan",
          all(S["picture"].startswith("data:image/png;base64,") for S in P["sheets"].values() if S["size"]))

    # a margin of 1.5%: since 99p fills holes, the horse fits 512 at 1%
    small = armbake.plan(hproj, None, {"size": {"main": 512, "attach": 512}, "margin": 1.5}, image_of=im_of)
    check(f"a sheet too small says what did not fit ({len(small['sheets']['main']['left'])} on the main sheet)",
          not small["fits"] and small["sheets"]["main"]["left"])
    auto = armbake.plan(hproj, None, {"size": {"main": 512, "attach": 512}, "margin": 1.5, "auto": True}, image_of=im_of)
    check(f"and the automatic way out fits it, saying what it cost ({auto['auto']})", auto["fits"] and auto["auto"])
    try:
        armbake.bake(hproj, None, {"size": {"main": 512, "attach": 512}, "margin": 1.5}, str(tmp / "no"), "x", image_of=im_of)
        refused = False
    except armbake.BakeError:
        refused = True
    check("a bake that does not fit is refused", refused)

    got = armbake.bake(hproj, None, {}, str(tmp / "out"), "horse_95i", image_of=im_of)
    back = mesh.read_mesh(tmp / "out" / "horse_95i.mesh")
    check(f"the bake writes the model and its sheets ({', '.join(got['files'])})",
          "horse_95i.mesh" in got["files"] and "horse_95i.texture" in got["files"])
    check(f"the written model has every vertex, triangle and group ({back.vertices}, {back.triangles}, {len(back.groups)})",
          (back.vertices, back.triangles, len(back.groups)) == (horse.vertices, horse.triangles, len(horse.groups)))
    # 2026-10-15: an exported model crashed the game. Its bone table was the
    # bones its parts used, in the order met, numbered 0 on, one unnamed, with
    # no bone_weapon; its sheets had no mipmaps and were two sizes
    back_tab = list(zip(back.bones, back.bone_links))
    check("the bake writes the source model's own bone table, slots and all",
          back_tab == list(zip(horse.bones, horse.bone_links)))
    broken = mesh.MeshFile(source="x", format="mesh")
    broken.bones, broken.bone_links = ["bone_rlowerleg", "", "bone_rfoot"], [0, 1, 2]
    check("a table with an unnamed bone is never copied", not armbake._real_table(broken))
    check("a model whose parts bring no table gets the standard one",
          armbake.bone_table([], {}, None) == armbake.STANDARD_BONES)
    from unittransfer import sprites as _spr
    import struct as _st
    dds = _spr.texture_to_dds((tmp / "out" / "horse_95i.texture").read_bytes())
    side = _st.unpack_from("<I", dds, 16)[0]
    check(f"a sheet carries its whole mipmap chain ({_st.unpack_from('<I', dds, 28)[0]} levels at {side})",
          _st.unpack_from("<I", dds, 28)[0] == side.bit_length())
    check("both sheets are one size", len({v for v in got["sheets"].values()}) == 1)
    whole = armbake.Block([], ("s", None, 0, 1.0, {}), [0, 0, 1019, 1019], "")
    check("a block nearly the sheet's width fits it: the margin may run off the edge",
          not armbake.pack([whole], 1024, 5) and whole.x == 0)
    # 99p: a block goes into a hole under another, which a column profile
    # never reaches. A frame 500 texels square round a 300 hole, and a block
    # of 200 that has nowhere else to go on a 512 sheet
    class _O(dict):
        pass

    def _isl(oid, rects, rect):
        polys = [tri for x0, y0, x1, y1 in rects
                 for tri in (((x0, y0), (x1, y0), (x1, y1)), ((x0, y0), (x1, y1), (x0, y1)))]
        return armbake._Island({"id": oid}, [], ("s", None, 0, 1.0, {}), rect, 0, "main", polys)
    frame = armbake.Block([_isl(1, [(0, 0, 500, 100), (0, 400, 500, 500), (0, 100, 100, 400), (400, 100, 500, 400)],
                                [0, 0, 500, 500])], ("s", None, 0, 1.0, {}), [0, 0, 500, 500], "")
    inner = armbake.Block([_isl(2, [(0, 0, 200, 200)], [0, 0, 200, 200])], ("t", None, 0, 1.0, {}), [0, 0, 200, 200], "")
    left99 = armbake.pack([frame, inner], 512, 2)
    check(f"a block is packed into the hole of another (at {inner.x}, {inner.y})",
          not left99 and 100 <= inner.x - frame.x and inner.x - frame.x + 200 <= 400
          and 100 <= inner.y - frame.y and inner.y - frame.y + 200 <= 400)
    strip = armbake.Block([_isl(3, [], [0, 0, 300, 300])], ("u", None, 0, 1.0, {}), [0, 0, 300, 300], "")
    strip.islands[0].polys = [((0, 20), (20, 0), (300, 280)), ((0, 20), (300, 280), (280, 300))]
    check(f"a strip lying across its box is offered the turn that boxes it smallest ({strip.free_angle()} degrees)",
          abs(strip.free_angle() - 45) < 0.5)
    armbake.pack([strip], 512, 2, free=True)
    check(f"and with free rotation it is packed lying straight ({strip.w} by {strip.h})",
          strip.angle and min(strip.w, strip.h) <= 32)
    from unittransfer import sprites
    dds = sprites.texture_to_dds((tmp / "out" / "horse_95i.texture").read_bytes())
    check("its sheet is a .texture the game reads (DXT5 inside)", dds[:4] == b"DDS " and dds[84:88] == b"DXT5")
    sheets = {"main": np.asarray(Image.open(tmp / "out" / "horse_95i.png").convert("RGBA"))}
    if (tmp / "out" / "horse_95i_attach.png").is_file():
        sheets["attach"] = np.asarray(Image.open(tmp / "out" / "horse_95i_attach.png").convert("RGBA"))
    # every vertex finds on its new sheet the texel it had on the old one;
    # a vertex on a pixel's edge may read its neighbour
    assets = armory.project_assets(hproj)
    miss = n = start = 0
    for o in hproj["objects"]:
        old = armory.object_mesh(o, assets, None)
        for v in range(old.vertices):
            u0, v0 = old.uvs[v * 2], old.uvs[v * 2 + 1]
            u1, v1 = back.uvs[(start + v) * 2], back.uvs[(start + v) * 2 + 1]
            sheet = sheets["attach" if u1 >= 1 else "main"]
            S = sheet.shape[0]
            want = grad[int((v0 % 1) * W) % W, int((u0 % 1) * W) % W, :3].astype(int)
            ty, tx = int(v1 * S), int((u1 % 1) * S)
            near = sheet[max(0, ty - 1):ty + 2, max(0, tx - 1):tx + 2, :3].astype(int)
            n += 1
            if np.abs(near - want).max(-1).min() > 1:
                miss += 1
        start += old.vertices
    check(f"each vertex reads the texel it read before, copied not resampled ({n - miss} of {n})", miss == 0)

    # 99p: free rotation, opt in. A block turned to its own angle is
    # resampled, so each vertex reads near the texel it read, not on it
    st_f = {}
    pf = armbake.plan(hproj, None, {"rotate": "free"}, image_of=im_of, _state=st_f)
    check(f"free rotation turns the blocks it boxes smaller ({pf['turned']} of {pf['blocks']}), and is off by default",
          pf["turned"] > 0 and P.get("turned", 0) == 0 and P["settings"]["rotate"] == "quarter")
    armbake.bake(hproj, None, {"rotate": "free"}, str(tmp / "out_free"), "hf", image_of=im_of)
    backf = mesh.read_mesh(tmp / "out_free" / "hf.mesh")
    fsheets = {"main": np.asarray(Image.open(tmp / "out_free" / "hf.png").convert("RGBA"))}
    if (tmp / "out_free" / "hf_attach.png").is_file():
        fsheets["attach"] = np.asarray(Image.open(tmp / "out_free" / "hf_attach.png").convert("RGBA"))
    turned = {o for b in st_f["blocks"] if b.angle for o in b.objs}
    fmiss = fn = start = 0
    for o in hproj["objects"]:
        old = armory.object_mesh(o, assets, None)
        for v in range(old.vertices):
            if o["id"] in turned:
                u0, v0 = old.uvs[v * 2], old.uvs[v * 2 + 1]
                u1, v1 = backf.uvs[(start + v) * 2], backf.uvs[(start + v) * 2 + 1]
                sheet = fsheets["attach" if u1 >= 1 else "main"]
                S_ = sheet.shape[0]
                want = grad[int((v0 % 1) * W) % W, int((u0 % 1) * W) % W, :3].astype(int)
                ty, tx = int(v1 * S_), int((u1 % 1) * S_)
                near = sheet[max(0, ty - 1):ty + 2, max(0, tx - 1):tx + 2, :3].astype(int)
                fn += 1
                if np.abs(near - want).max(-1).min() > 6:
                    fmiss += 1
        start += old.vertices
    check(f"a turned block's vertices read the art they read, resampled ({fn - fmiss} of {fn} within 6 of 255)",
          fn > 0 and fmiss <= fn // 50)

# ---------------------------------------------------------------------------
print("\nNormal maps (95j)")

flat = armbake.normal_pixels(np.full((8, 8, 4), 120, np.uint8), {"strength": 1, "blur": 0})
check("flat art makes a flat map", (flat[..., :3] == [128, 128, 255]).all() and (flat[..., 3] == 0).all())
ramp = np.zeros((8, 16, 4), np.uint8)
ramp[..., :3] = (np.arange(16) * 16)[None, :, None]
ramp[..., 3] = 255
nm = armbake.normal_pixels(ramp, {"strength": 1, "blur": 0})
check(f"art growing lighter to the right tilts the map against it, as the shipped maps do (red {nm[4, 8, 0]})",
      nm[4, 8, 0] < 128 and nm[4, 8, 1] == 128)
inv = armbake.normal_pixels(ramp, {"strength": 1, "blur": 0, "invert": True})
check("invert turns it the other way", inv[4, 8, 0] > 128)
weak = armbake.normal_pixels(ramp, {"strength": 0.5, "blur": 0})
check("half the strength, half the tilt", abs((128 - weak[4, 8, 0]) * 2 - (128 - nm[4, 8, 0])) <= 2)

nmode = {"mode": "specialized", "materials": {"metal": {"strength": 0.3}}}
check("Specialized: a metal object takes metal's setting, changed by the user",
      armbake.normal_setting(nmode, {"material": "metal"})["strength"] == 0.3
      and armbake.normal_setting(nmode, {"material": "metal"})["blur"] == armbake.NORMAL_MATERIALS["metal"]["blur"])
check("an object's own setting wins, and no material is 'other'",
      armbake.normal_setting(nmode, {"material": "metal", "normal": {"strength": 2}})["strength"] == 2
      and armbake.normal_setting(nmode, {})["strength"] == armbake.NORMAL_MATERIALS["other"]["strength"])
check("Generic is one setting, Skip none",
      armbake.normal_setting({"mode": "generic"}, {"material": "metal"}) == armbake.NORMAL_GENERIC
      and armbake.normal_setting({"mode": "skip"}, {}) is None)

if node:
    js = "".join((ROOT / "web" / "js" / f).read_text(encoding="utf-8") for f in ("armobj.js", "armnormal.js"))
    art = rng.integers(0, 256, size=(20, 20, 4), dtype=np.uint8)
    sets = [{"strength": 1.0, "blur": 0}, {"strength": 1.4, "blur": 1.5}, {"strength": 0.7, "blur": 0.8, "invert": True}]
    probe = ("const tt=x=>x,ttN=x=>x;" + js + ";const px=" + json.dumps(art.reshape(-1).tolist())
             + ";const sets=" + json.dumps(sets) + ";console.log(JSON.stringify(sets.map(s=>Array.from(armNormalPixels(px,20,20,s)))))")
    (tmp / "probe4.js").write_text(probe, encoding="utf-8")
    out = subprocess.run([node, str(tmp / "probe4.js")], capture_output=True, text=True, timeout=60)
    js_out = json.loads(out.stdout or "null") or []
    py_out = [armbake.normal_pixels(art, s_).reshape(-1).tolist() for s_ in sets]
    worst = max((max(abs(a - b) for a, b in zip(p, j)) for p, j in zip(py_out, js_out)), default=999)
    check(f"the preview's normal map is the bake's, blur and all (worst {worst} of 255)",
          len(js_out) == 3 and worst <= 1)

if horse is not None:
    got = armbake.bake(hproj, None, {}, str(tmp / "n_skip"), "h", image_of=im_of)
    flat_sheet = np.asarray(Image.open(tmp / "n_skip" / "h_normal.png").convert("RGBA"))
    check(f"Skip writes a flat normal map beside each sheet ({', '.join(f for f in got['files'] if 'normal' in f)})",
          "h_normal.texture" in got["files"] and (flat_sheet[..., :3] == [128, 128, 255]).all())
    hproj["normals"] = {"mode": "specialized"}
    hproj["objects"][0]["material"] = "wood"
    for o in hproj["objects"][1:]:
        o["material"] = "skin"
    st = {}
    armbake.plan(hproj, None, {}, image_of=im_of, _state=st)
    armbake.bake(hproj, None, {}, str(tmp / "n_spec"), "h", image_of=im_of)
    specs = {sh: np.asarray(Image.open(tmp / "n_spec" / f"h{'' if sh == 'main' else '_attach'}_normal.png").convert("RGBA")).astype(int)
             for sh in ("main", "attach") if st["per"][sh]["size"]}

    def tilt(obj_id):
        for sh, spec in specs.items():
            for b in st["per"][sh]["blocks"]:
                if b.islands[0].obj["id"] == obj_id and b.placed:
                    w, h = (b.h, b.w) if b.rot else (b.w, b.h)
                    return np.abs(spec[b.y:b.y + h, b.x:b.x + w, :2] - 128).mean()
        return 0.0
    wood_id = hproj["objects"][0]["id"]
    skin_id = hproj["objects"][1]["id"]
    check(f"Specialized: wood is cut deeper than skin ({tilt(wood_id):.1f} against {tilt(skin_id):.1f})",
          tilt(wood_id) > tilt(skin_id) > 0)
    hproj.pop("normals")

# ---------------------------------------------------------------------------
print("\nInto a mod: the import unit menu (95k)")

game_k = _realmod.game(required=False)
AMER = (game_k / "mods" / "americas") if game_k.is_dir() else None
if horse is not None and AMER is not None and AMER.is_dir():
    from unittransfer import armunit, config, gamepack, transfer
    from unittransfer.mod import Mod
    amer = Mod(AMER)
    cfg = tmp / "cfg"
    cfg.mkdir()
    config.CONFIG_DIR = cfg
    config.BACKUP_DIR = cfg / "backups"
    config.SETTINGS_PATH = cfg / "settings.json"
    config.LOG_PATH = cfg / "transfers.json"
    mroot = tmp / "mod_k"
    for rel in ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
                "descr_mount.txt"):
        src, _where = gamepack.lookup(rel, amer)
        if src is not None and src.is_file():
            (mroot / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, mroot / "data" / rel)
    kmod = Mod(mroot)
    temps = armunit.role_templates(kmod)
    counts = ", ".join(f"{r} {t['units']}" for r, t in temps.items())
    check(f"role templates measured on the mod itself ({counts})",
          set(temps) == set(armunit.ROLES))
    check(f"a pike unit is a phalanx with pikes ({temps['pike']['skeletons']}, {temps['pike']['fields'].get('formation')})",
          "pike" in temps["pike"]["fields"].get("attributes", "") and "phalanx" in temps["pike"]["fields"].get("formation", "")
          and any("pike" in s.lower() for s in temps["pike"]["skeletons"]))
    check(f"cavalry rides ({temps['cavalry']['fields'].get('mount')})", temps["cavalry"]["fields"].get("mount"))

    bake_dir = str(tmp / "out")
    base = {"bake_folder": bake_dir, "stem": "horse_95i"}
    sk = armunit.plan_install(kmod, dict(base, choice="skip", name="armory_horse", template="cavalry"))
    shown = armunit.payload(sk)
    check(f"Skip plans one new entry, cloned from the template's ({sk['steps'][0]['plan'].new_entries[0][0]})",
          shown["ok"] and [n for n, _r, _p in sk["steps"][0]["plan"].new_entries] == ["armory_horse"])
    rec = armunit.apply_install(lambda n: Mod(mroot), "mod_k", dict(base, choice="skip", name="armory_horse", template="cavalry"))
    after = Mod(mroot)
    ent = after.modeldb.by_name().get("armory_horse")
    check("written: the entry points at the baked mesh, copied into its folder",
          ent is not None and ent.lods[0][0].endswith("armory/armory_horse/horse_95i.mesh")
          and (mroot / "data" / "unit_models/_units/armory/armory_horse/horse_95i.mesh").is_file())
    check("and at its sheets and normal maps, in the folder's textures/",
          (mroot / "data" / "unit_models/_units/armory/armory_horse/textures/horse_95i.texture").is_file()
          and (mroot / "data" / "unit_models/_units/armory/armory_horse/textures/horse_95i_normal.texture").is_file())
    check("its skeletons are the cavalry template's",
          ent is not None and ent.animations[0].primary_skeleton == temps["cavalry"]["skeletons"][0])
    transfer.undo(rec["records"][0]["id"])
    check("Undo takes the entry back out", "armory_horse" not in Mod(mroot).modeldb.by_name())

    unit_k = next(u.type for u in kmod.edu.units
                  if (u.category or "").lower() == "infantry" and kmod.modeldb.by_name().get((u.soldier_model or "").lower()))
    armunit.apply_install(lambda n: Mod(mroot), "mod_k", dict(base, choice="add", name="armory_foot", unit=unit_k))
    after = Mod(mroot)
    check(f"Add to a unit: {unit_k} now wears the new entry",
          after.edu.by_type()[unit_k].soldier_model.lower() == "armory_foot" and "armory_foot" in after.modeldb.by_name())

    try:
        armunit.plan_install(after, dict(base, choice="new", name="armory_pike", unit=unit_k, new_type=unit_k))
        refused = False
    except armunit.InstallError:
        refused = True
    check("a new unit cannot take a type the mod has", refused)
    got = armunit.apply_install(lambda n: Mod(mroot), "mod_k",
                                dict(base, choice="new", name="armory_pike", unit=unit_k,
                                     new_type="armory_pikemen", template="pike"))
    after = Mod(mroot)
    nu = after.edu.by_type().get("armory_pikemen")
    check("New unit: the unit is duplicated and wears the new entry",
          nu is not None and nu.soldier_model.lower() == "armory_pike" and len(got["records"]) == 2)
    attrs = armunit._field(nu, "attributes") if nu else ""
    check(f"with the pike template's class, formation and attributes ({attrs})",
          nu is not None and "pike" in attrs and "phalanx" in armunit._field(nu, "formation")
          and (nu.class_type or "").lower() == "spearmen")
    check("and the unit it came from is unchanged", after.edu.by_type()[unit_k].soldier_model.lower() == "armory_foot")
else:
    print("  no mod installed to write into; skipped")

# ---------------------------------------------------------------------------
print("\nThe asset library (95l)")

from unittransfer import armlib
lib = armlib.load()
check("an empty library to start", lib == {"items": [], "collections": [], "categories": []})
a1 = armlib.add(lib, {"kind": "entry", "mod": "americas", "entry": "peasants", "file_hash": "abc", "name": "Peasants"})
a2 = armlib.add(lib, {"kind": "entry", "mod": "americas", "entry": "peasants"})
a3 = armlib.add(lib, {"kind": "entry", "mod": "teutonic", "entry": "farmers", "file_hash": "abc"})
a4 = armlib.add(lib, {"kind": "external", "path": "C:/m/Shield.glb"})
check("a model is kept once, with its own name", a1.get("item", {}).get("name") == "Peasants" and a1["item"]["id"] == 1)
check("the same entry again is refused as the same", a2.get("why") == "same" and a2["same"]["id"] == 1)
check("so is another entry whose model file is byte for byte the same", a3.get("why") == "art")
check("a file is named by its file name", a4.get("item", {}).get("name") == "Shield.glb")
lib["collections"].append({"id": 1, "name": "Elves"})
lib["items"][0]["collections"] = [1]
lib["items"][0]["notes"] = "good shield"
armlib.save(lib)
check("names, notes and collections save and load back", armlib.load() == lib)
try:
    armlib.check_lib({"nope": 1})
    refused = False
except armory.ArmoryError:
    refused = True
check("something that is not a library is not saved", refused)

if game_k.is_dir() and AMER is not None and AMER.is_dir():
    from unittransfer.mod import Mod
    amer = Mod(AMER)
    u = next(x for x in amer.edu.units if x.category and x.class_type
             and amer.modeldb.by_name().get((x.soldier_model or "").lower()))
    lib2 = {"items": [{"id": 1, "kind": "entry", "mod": "americas", "entry": u.soldier_model},
                      {"id": 2, "kind": "external", "path": "x.obj"}], "collections": [], "categories": []}
    fac = armlib.facets(lib2, lambda n: amer)
    f1 = fac[1]
    check(f"an entry sorts by the units that wear it ({u.type}: {f1['type']} {f1['class']}, {len(f1['faction'])} factions)",
          u.category.lower() in f1["type"] and u.class_type.lower() in f1["class"] and f1["faction"])
    check("a file has none of those", fac[2] == {"class": [], "type": [], "faction": [], "tier": []})

# ---------------------------------------------------------------------------
print("\nUnit cards, Generate (95m)")

import base64 as _b64
buf = io.BytesIO()
Image.new("RGBA", (48, 64), (120, 40, 40, 255)).save(buf, "PNG")
url = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
got = armory.save_card("Elf Guard", "card", url)
check(f"a unit card is saved as the game names it ({Path(got['path']).name})",
      Path(got["path"]).name == "#Elf_Guard.tga" and Image.open(got["path"]).size == (48, 64))
got = armory.save_card("Elf Guard", "info", url)
check("an info card as <name>_info.tga, with a .png beside it",
      Path(got["path"]).name == "Elf_Guard_info.tga" and Path(got["path"]).with_suffix(".png").is_file())
try:
    armory.save_card("", "card", url)
    refused = False
except armory.ArmoryError:
    refused = True
check("a card with no name is refused", refused)
if node:
    js = (ROOT / "web" / "js" / "cardgen.js").read_text(encoding="utf-8")
    probe = ("const tt=x=>x,ttN=x=>x,state={},ARM={};" + js + r""";
const m = new Uint8Array(9 * 9); m[4 * 9 + 4] = 1;
const g = cgDilate(m, 9, 9, 2); let n = 0; for(const v of g) n += v;
const d = new Uint8ClampedArray([100, 150, 200, 255]);
cgFinish(d, 1, 1, {exposure: 0, brightness: 0, contrast: 1, gamma: 1, saturation: 1, hue: 0, sharpen: 0});
const e = new Uint8ClampedArray([100, 150, 200, 255]);
cgFinish(e, 1, 1, {exposure: 0, brightness: 0, contrast: 1, gamma: 1, saturation: 0, hue: 0, sharpen: 0});
console.log(JSON.stringify({n, same: Array.from(d), grey: Array.from(e)}));
""")
    (tmp / "probe5.js").write_text(probe, encoding="utf-8")
    out = subprocess.run([node, str(tmp / "probe5.js")], capture_output=True, text=True, timeout=60)
    got = json.loads(out.stdout or "null") or {}
    check(f"the outline grows the silhouette by its width (a pixel grown by 2 covers {got.get('n')})", got.get("n") == 25)
    check(f"the finish at its neutral settings leaves a pixel alone ({got.get('same')})",
          got.get("same") and max(abs(a - b) for a, b in zip(got["same"], [100, 150, 200, 255])) <= 1)
    grey = got.get("grey") or [0, 1, 2]
    check(f"and saturation 0 makes it grey ({grey})", max(grey[:3]) - min(grey[:3]) <= 1)

# ---------------------------------------------------------------------------
print("\nThe card maker's IK rig and pose library (99n)")

poses = json.loads((ROOT / "unittransfer" / "data" / "m2_poses.json").read_text(encoding="utf-8"))
check(f"the kit's three rigs and its pose library ship ({len(poses['poses'])} poses, "
      f"{', '.join(f'{k} {len(v)} bones' for k, v in poses['rigs'].items())})",
      set(poses["rigs"]) == {"infantry", "archer", "dwarf"} and len(poses["poses"]) > 200)
if node:
    js = (ROOT / "web" / "js" / "cgrig.js").read_text(encoding="utf-8")
    probe = (js.replace("\nconst ", "\nvar ") + r""";
function v3aBind(anim){ const out = []; anim.bones.forEach((b, i) => { const par = b.parent >= 0 ? out[b.parent] : [0,0,0];
  out.push([par[0]+b.pivot[0], par[1]+b.pivot[1], par[2]+b.pivot[2]]); }); return out; }
const fs = require('fs');
const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const truth = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const rig = crRig(data.rigs.infantry);
const byName = new Map(data.poses.map(p => [p.n, p]));
const errs = truth.poses.map(t => {
  const pose = t.pose === '(rest)' ? {b: {}} : byName.get(t.pose);
  const W = crSolve(rig, pose.b, 'infantry');
  let worst = 0;
  for(const [n, m] of Object.entries(t.bones)){
    if(!n.startsWith('bone_')) continue;
    const a = W[rig.byName.get(n)];
    worst = Math.max(worst, Math.hypot(a[3]-m[3], a[7]-m[7], a[11]-m[11]));
  }
  return [t.pose, worst];
});
// at rest, the skeleton is posed as it is bound
const anim = {bones: [{name: 'Scene Root', parent: -1, pivot: [0,0,0]}, {name: 'bone_pelvis', parent: 0, pivot: [0,0,0]},
  {name: 'bone_RThigh', parent: 1, pivot: [0.0952, 0.0008, 0]}, {name: 'bone_Rlowerleg', parent: 2, pivot: [0.0226, -0.4645, 0.0144]}]};
const rest = crPoseOn(rig, crSolve(rig, {}, 'infantry'), anim);
const still = rest.every((b, i) => Math.abs(b.m[0] - 1) + Math.abs(b.m[4] - 1) + Math.abs(b.m[8] - 1) < 0.01);
// a pose applied to the arms leaves the legs as they were
const legs = {'IK angle right': {l: [0.1, 0, 0]}};
const armsOnly = crApply(legs, byName.get('IK 2H Full 1'), 'arms');
console.log(JSON.stringify({errs, still, legsKept: !!armsOnly['IK angle right'] && !armsOnly['IK Pelvis'],
  armsTaken: !!armsOnly['IK frist right']}));
""")
    (tmp / "probe6.js").write_text(probe, encoding="utf-8")
    out = subprocess.run([node, str(tmp / "probe6.js"), str(ROOT / "unittransfer" / "data" / "m2_poses.json"),
                          str(ROOT / "tests" / "rig_truth.json")], capture_output=True, text=True, timeout=60)
    got = json.loads(out.stdout or "null") or {}
    errs = got.get("errs") or []
    rest_err = max((e for n, e in errs if n == "(rest)"), default=1)
    check(f"at rest the rig's Med2 bones are Blender's to the millimetre ({rest_err:.4f} m)", rest_err < 0.002)
    worst = max((e for n, e in errs), default=1)
    mid = sorted(e for n, e in errs)[len(errs) // 2] if errs else 1
    check(f"on thirteen of the kit's poses, Blender's own solve and this one agree (median {mid:.3f} m, worst {worst:.3f} m)",
          len(errs) == 13 and mid < 0.03 and worst < 0.15)
    check("the rig at rest leaves the model's skeleton as it is bound", got.get("still") is True)
    check("a pose applied to the arms takes the arms and keeps the legs",
          got.get("legsKept") is True and got.get("armsTaken") is True)

# ---------------------------------------------------------------------------
print("\nThe project")
armory.save_project({"v": 1, "objects": [{"id": 1}]})
check("a project saves and loads back", armory.load_project() == {"v": 1, "objects": [{"id": 1}]})

# ---------------------------------------------------------------------------
print("\nSaved sessions and backups (99o)")

T0 = 1_800_000_000.0
armory.save_project({"v": 1, "objects": [{"id": 1}], "extra": {"cam": {"dist": 3}}}, now=T0)
got = armory.session_action({"action": "save", "name": "Elf guard"}, now=T0 + 1)
sid = got["project"]["session"]["id"]
view = armory.sessions_view()
check(f"the open model saves as a named session ({sid})",
      [x["name"] for x in view["sessions"]] == ["Elf guard"] and view["current"] == sid)
armory.save_project(dict(got["project"], objects=[{"id": 1}, {"id": 2}]), now=T0 + 2)
check("every save of the open model is a save of its session",
      len(json.loads((armory.ARMORY_DIR / "sessions" / f"{sid}.json").read_text(encoding="utf-8"))["objects"]) == 2)
armory.session_action({"action": "duplicate", "id": sid, "name": "Orc guard"}, now=T0 + 3)
other = next(x["id"] for x in armory.sessions_view()["sessions"] if x["name"] == "Orc guard")
opened = armory.session_action({"action": "open", "id": other}, now=T0 + 4)["project"]
check("a duplicate opens as a session of its own, the camera with it",
      opened["session"]["id"] == other and opened["extra"]["cam"]["dist"] == 3
      and armory.load_project()["session"]["id"] == other)
armory.session_action({"action": "rename", "id": other, "name": "Uruk guard"})
check("a session renames", armory.load_project()["session"]["name"] == "Uruk guard")
# backups: one every BACKUP_EVERY seconds while the model changes
before = len(armory.sessions_view()["backups"])
proj = armory.load_project()
armory.save_project(dict(proj, objects=[{"id": 9}]), now=T0 + 10)
armory.save_project(dict(proj, objects=[{"id": 9}, {"id": 10}]), now=T0 + 11)
mid = len(armory.sessions_view()["backups"])
armory.save_project(dict(proj, objects=[{"id": 9}, {"id": 10}, {"id": 11}]), now=T0 + 10 + armory.BACKUP_EVERY + 1)
after = armory.sessions_view()["backups"]
check(f"a backup is taken when the last is {armory.BACKUP_EVERY} s old, not before ({before}, {mid}, {len(after)})",
      mid == before and len(after) == before + 1)
armory.save_project(dict(proj, objects=[{"id": 9}, {"id": 10}, {"id": 11}]), now=T0 + 10 + 3 * armory.BACKUP_EVERY)
check("and not when nothing changed", len(armory.sessions_view()["backups"]) == len(after))
oldest = after[-1]["file"]
back = armory.session_action({"action": "revert", "file": oldest}, now=T0 + 5000)["project"]
check(f"a backup puts the model back, as the session it was ({back['session']['name']})",
      back["session"]["id"] == other and armory.load_project()["objects"] == back["objects"])
for k in range(armory.BACKUPS_KEPT + 5):
    armory.save_project(dict(proj, objects=[{"id": 100 + k}]), now=T0 + 10_000 + k * (armory.BACKUP_EVERY + 1))
check(f"only the last {armory.BACKUPS_KEPT} backups are kept",
      len(armory.sessions_view()["backups"]) == armory.BACKUPS_KEPT)
n_before = len(armory.sessions_view()["backups"])
had = armory.load_project()["objects"]
armory.save_project(dict(armory.load_project(), objects=[], assets=[]), now=T0 + 10_000 + 26 * (armory.BACKUP_EVERY + 1) + 5)
saved = [json.loads((armory.ARMORY_DIR / "backups" / other / b["file"]).read_text(encoding="utf-8"))
         for b in armory.sessions_view()["backups"][:1]]
check("a save that would empty a model backs it up first, however recent the last backup",
      saved and saved[0]["objects"] == had)
armory.closed()
check("a page that says goodbye leaves no crash behind", armory.sessions_view()["unclean"] is False)
armory.opened()
check("one that never did, does", armory.sessions_view()["unclean"] is True)
try:
    armory.session_action({"action": "open", "id": "../../etc"})
    refused = False
except armory.ArmoryError:
    refused = True
check("a session id is a name, never a path", refused)
armory.session_action({"action": "delete", "id": other})
check("a session deletes, and the open model stays, as no session",
      "session" not in armory.load_project() and other not in [x["id"] for x in armory.sessions_view()["sessions"]])

# ---------------------------------------------------------------------------
print("\nImport from a folder: every model in it, found")
fold = tmp / "kit"
(fold / "helmets" / "deep").mkdir(parents=True)
(fold / ".git").mkdir()
for rel in ("a_body.obj", "helmets/kettle.glb", "helmets/deep/sallet.dae", "b_shield.MESH",
            "notes.txt", "helmets/kettle.png", ".git/stray.obj"):
    (fold / rel).write_bytes(b"x")
f = armory.folder_models(str(fold))
rels = [m["rel"] for m in f["models"]]
check("every model under it, in the folders under it too",
      rels == ["a_body.obj", "b_shield.MESH", "helmets/kettle.glb", "helmets/deep/sallet.dae"])
check("each with its own folder for grouping", [m["dir"] for m in f["models"]] == ["", "", "helmets", "helmets/deep"])
check("and the full path the import reads", all(Path(m["path"]).is_file() for m in f["models"]))
check("pictures, notes and hidden folders are not models", not any(r.endswith((".png", ".txt")) or ".git" in r for r in rels))
cap = armory.folder_models(str(fold), limit=2)
check("a folder with too many is cut short, and says so", len(cap["models"]) == 2 and cap["truncated"])
try:
    armory.folder_models(str(fold / "a_body.obj")); check("a file is refused as a folder", False)
except armory.ArmoryError:
    check("a file is refused as a folder", True)

print("\nA real mod")
game = _realmod.game(required=False)
mods = sorted(p for p in (game / "mods").iterdir() if (p / "data").is_dir()) if game.is_dir() else []
if mods:
    from unittransfer.mod import Mod
    mod = Mod(mods[0])
    cat = armory.catalogue(mod)
    check(f"{mod.name}: {len(cat['entries'])} entries and {len(cat['units'])} units offered",
          cat["entries"] and cat["units"])
    unit = next(u for u in cat["units"] if not u["models"][0]["missing"])
    check("a unit's soldier is listed first", unit["models"][0]["role"] == "soldier")
    cul = sum(1 for u in cat["units"] if u["cultures"])
    check(f"each unit carries its factions and their cultures, for the filters (100j; {cul} with a culture)",
          all(u["factions"] is not None for u in cat["units"]) and cul > 0
          and all(set(u["cultures"]) <= set(mod.faction_cultures.values()) for u in cat["units"]))
    asset = armory.asset_view(mod, unit["models"][0]["name"])
    check(f"its soldier as an asset: {len(asset['objects'])} objects, {asset['triangles']} triangles",
          asset["objects"] and sum(o["triangles"] for o in asset["objects"]) == asset["triangles"])
    try:
        armory.asset_view(mod, "no_such_entry_here")
        refused = False
    except armory.ArmoryError:
        refused = True
    check("an entry the mod has not got is refused by name", refused)
    # 95i on a real entry: its skin's main and attachment sheets, read whole
    rproj = {"assets": [{"kind": "entry", "mod": mod.name, "entry": asset["entry"]}], "collections": [],
             "objects": [{"id": i + 1, "name": ob["name"], "mesh": ob["mesh"], "flag": ob["flag"],
                          "src": [{"asset": f"{mod.name}|{asset['entry']}", "group": i}],
                          "t": [0, 0, 0], "r": [0, 0, 0], "s": [1, 1, 1]} for i, ob in enumerate(asset["objects"])]}
    try:
        RP = armbake.plan(rproj, lambda n: mod, {})
        sizes = {s: v["size"] for s, v in RP["sheets"].items()}
        check(f"{asset['entry']} packs onto its sheets {sizes}: {RP['islands']} islands in {RP['blocks']} blocks",
              RP["fits"] and RP["islands"] > 0)
    except armory.ArmoryError as e:
        check(f"{asset['entry']} packs onto its sheets ({e})", False)
else:
    print("  no mod installed; skipped")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
