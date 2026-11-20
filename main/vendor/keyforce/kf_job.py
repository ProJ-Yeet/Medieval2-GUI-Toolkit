"""Runs inside a hidden Blender, started by :mod:`unittransfer.keyforce`:

    blender -b --factory-startup --python kf_job.py -- <job.json>

Keyforce Tools' Automatic Bake with *Import, Then Bake*, in one go: every
``*_lod<N>.fbx`` (or the single-LOD ``.fbx``) under the job's folder imported
with its ``_d`` / ``_s`` / ``_n`` maps, the World set to Match Material
Preview, and every mesh with a colour texture baked with the recommended
settings into one ``<source texture>.png`` per colour texture. The bake is
the add-on's own code (``keyforce_tools.py`` beside this file), unchanged.

Writes ``progress.json`` ({fraction, status}) while it runs and
``result.json`` ({results, files, meshes, missing, warnings} or {error}) at
the end, beside the job file.
"""
import json
import sys
import traceback
from pathlib import Path

import bpy

job_path = Path(sys.argv[sys.argv.index("--") + 1])
folder = job_path.parent


sys.path.insert(0, str(Path(__file__).resolve().parent))
import kf_settings as kfs  # noqa: E402

write = kfs.writer(folder)


try:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    import keyforce_tools as kt

    kt.register()
    context = bpy.context
    scene = context.scene
    root, lod = Path(job["root"]), int(job["lod"])
    if not kt.discover(root, lod):
        raise ValueError(f"no *_lod{lod}.fbx (or single-LOD .fbx) under {root}")
    write("progress.json", {"fraction": 0.0, "status": "importing"})
    warnings = []
    before = set(scene.objects)
    files, meshes, missing = kt.import_folder(root, lod, lambda kind, line: warnings.append(str(line)))
    settings = kfs.bake_settings(kt, scene, job.get("settings"))
    objects = [o for o in scene.objects if o not in before and o.type == "MESH"
               and o.name in context.view_layer.objects and o.visible_get() and not o.hide_render
               and o.data.uv_layers and kt.base_color_image(o.active_material) is not None]
    if not objects:
        raise ValueError("no visible meshes with a colour texture to bake")
    steps = kt.bake_prerendered_steps(context, objects, Path(job["out"]), int(job["size"]), settings.bake_samples,
                                      settings.bake_margin, settings.bake_shadows, settings, progress=print)
    results = kfs.run_steps(steps, write)
    glb = None
    if job.get("glb") and results:
        # the meshes in their baked materials, for Armory Studio (one .glb)
        write("progress.json", {"fraction": 1.0, "status": "writing the .glb"})
        kt.apply_baked(objects, results)
        keep = set(objects)
        for obj in objects:
            parent = obj.parent
            while parent is not None:
                keep.add(parent)
                parent = parent.parent
        for obj in context.view_layer.objects:
            obj.select_set(obj in keep)
        glb = Path(job["out"]) / (root.name + ".glb")
        bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True,
                                  export_apply=False, export_animations=False)
    write("result.json", {"glb": str(glb) if glb else None, "results": [{"path": str(path), "layers": layers, "skipped": skipped,
                                       "source": bpy.path.abspath(image.filepath) if image.filepath else image.name}
                                      for path, layers, skipped, image in results],
                          "files": files, "meshes": meshes, "missing": missing, "warnings": warnings})
except Exception as error:
    traceback.print_exc()
    write("result.json", {"error": str(error)})
