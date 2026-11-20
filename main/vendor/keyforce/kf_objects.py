"""Runs inside a hidden Blender, started by :mod:`unittransfer.keyforce`:

    blender -b --factory-startup --python kf_objects.py -- <job.json>

Keyforce Tools' bake of Armory Studio's own objects. The toolkit writes, per
colour texture, the objects wearing it (``entry<k>.npz``: positions, normals
and UVs per vertex, triangles and which object each belongs to, in the
game's space, y up) and the maps it decoded (``c<k>.png``, ``c<k>_s.png``,
``c<k>_n.png`` or ``c<k>_m2_norm.png``). Here each object becomes a mesh
with the add-on's own material for those maps, and the add-on's bake (the
recommended settings, or Manual Bake's from the job) writes ``c<k>.png``
into the job's ``out`` folder. ``progress.json`` / ``result.json`` as
kf_job.py writes them.
"""
import json
import sys
import traceback
from pathlib import Path

import bpy
import numpy as np

job_path = Path(sys.argv[sys.argv.index("--") + 1])
folder = job_path.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kf_settings as kfs  # noqa: E402

write = kfs.writer(folder)


def build(name, data, material):
    """One mesh object per Armory object on this texture."""
    pos, nrm, uv = data["pos"], data["nrm"], data["uv"]
    tris, owner = data["tris"], data["obj"]
    made = []
    for one in np.unique(owner):
        faces = tris[owner == one]
        used = np.unique(faces)
        at = np.full(len(pos), -1, np.int64)
        at[used] = np.arange(len(used))
        f = at[faces]
        # the game's y up -> Blender's z up
        co = pos[used][:, [0, 2, 1]] * np.array([1.0, -1.0, 1.0])
        n = nrm[used][:, [0, 2, 1]] * np.array([1.0, -1.0, 1.0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        # The Armory mirrors a file's z to the game's space, and its triangles
        # can wind against their normals; Cycles lights a face by its winding,
        # so it is turned round when most faces point away from their normals.
        face = np.cross(co[f[:, 1]] - co[f[:, 0]], co[f[:, 2]] - co[f[:, 0]])
        if ((face * n[f].sum(1)).sum(1) < 0).mean() > 0.5:
            f = f[:, ::-1]
        me = bpy.data.meshes.new(f"{name}_{int(one)}")
        me.from_pydata(co.tolist(), [], f.tolist())
        layer = me.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", uv[used][f.ravel()].ravel().astype(np.float32))
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.normals_split_custom_set_from_vertices(n.tolist())
        me.materials.append(material)
        me.update()
        obj = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(obj)
        made.append(obj)
    return made


try:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    import keyforce_tools as kt

    kt.register()
    context = bpy.context
    scene = context.scene
    for obj in list(scene.objects):         # the factory scene's cube, camera and light
        bpy.data.objects.remove(obj, do_unlink=True)
    settings = kfs.bake_settings(kt, scene, job.get("settings"))
    out = Path(job["out"])
    entries = job["entries"]
    done = []
    for k, entry in enumerate(entries):
        data = np.load(folder / entry["arrays"])
        maps = {key: folder / value if value else None for key, value in entry["maps"].items()}
        material = kt.make_material(f"c{k}", maps["colour"], maps.get("spec"), maps.get("normal"))
        objects = build(f"c{k}", data, material)
        write("progress.json", {"fraction": k / len(entries), "status": f"{entry['name']}: building"})
        steps = kt.bake_prerendered_steps(context, objects, out, int(entry["size"]), settings.bake_samples,
                                          settings.bake_margin, settings.bake_shadows, settings, progress=print)
        results = kfs.run_steps(steps, write, (k / len(entries), (k + 1) / len(entries)))
        done += [{"entry": k, "path": str(path), "layers": layers, "skipped": skipped}
                 for path, layers, skipped, _image in results]
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    write("result.json", {"results": done})
except Exception as error:
    traceback.print_exc()
    write("result.json", {"error": str(error)})
