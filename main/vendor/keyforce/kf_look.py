"""Runs inside a hidden Blender, started by :mod:`unittransfer.cycleslook`:

    blender -b --factory-startup --python kf_look.py -- <job.json>

What the Armory's live look at the Cycles bake needs out of Blender itself,
measured here rather than guessed, written into the job's folder:

* ``world_<name>.npy``: each world's HDRI made small exactly as the bake
  makes it (``Image.scale`` to ``WORLD_BLUR_SIZE``, keyforce_tools.mirror_world),
  float RGBA rows from the bottom, as Blender keeps them;
* ``lut.png``: the bake's save through the scene's colour management (AgX in
  a factory scene), as a 3D table: N x N x N inputs laid out N*N wide and N
  high (x = red + N * blue, y = green), each input 2 ** (LUT_LO + t * (LUT_HI -
  LUT_LO)) for t in 0..1, saved by the same ``save_render`` the bake uses;
* ``units.json``: what one white diffuse plane renders to under a sun of
  strength 1 and under a white world of strength 1, so the page's light is
  in Cycles' own units; and the colour management the scene had.
"""
import json
import math
import sys
import traceback
from pathlib import Path

import bpy
import numpy as np

job_path = Path(sys.argv[sys.argv.index("--") + 1])
folder = job_path.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

LUT_N = 33
LUT_LO, LUT_HI = -12.47393, 4.026069


def worlds(kt):
    out = {}
    for name in kt.BUILTIN_HDRIS:
        path = kt.builtin_hdri(name)
        if not path.is_file():
            continue
        image = bpy.data.images.load(str(path), check_existing=True)
        small = image.copy()
        small.scale(*kt.WORLD_BLUR_SIZE)
        w, h = small.size
        px = np.empty(w * h * 4, np.float32)
        small.pixels.foreach_get(px)
        np.save(folder / f"world_{name}.npy", px.reshape(h, w, 4))
        out[name] = str(path)
        bpy.data.images.remove(small)
    return out


def lut(scene):
    n = LUT_N
    t = np.linspace(0.0, 1.0, n)
    v = 2.0 ** (LUT_LO + t * (LUT_HI - LUT_LO))
    r, g, b = np.meshgrid(v, v, v, indexing="ij")          # [r, g, b]
    img = np.zeros((n, n * n, 4), np.float32)              # rows: green; columns: red + n * blue
    for bi in range(n):
        img[:, bi * n:(bi + 1) * n, 0] = r[:, :, bi].T
        img[:, bi * n:(bi + 1) * n, 1] = g[:, :, bi].T
        img[:, bi * n:(bi + 1) * n, 2] = b[:, :, bi].T
    img[..., 3] = 1.0
    image = bpy.data.images.new("kf_look_lut", n * n, n, alpha=True, float_buffer=True)
    image.pixels.foreach_set(img.ravel())                  # Blender's first row is the bottom one
    fmt = scene.render.image_settings
    fmt.file_format, fmt.color_mode, fmt.color_depth = "PNG", "RGB", "8"
    image.save_render(str(folder / "lut.png"), scene=scene)
    bpy.data.images.remove(image)


def units(scene):
    """A white diffuse plane seen from above: under a sun of strength 1 straight
    down, then under a white world of strength 1. Linear, through no view."""
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=4.0)
    plane = bpy.context.object
    mat = bpy.data.materials.new("white")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    plane.data.materials.append(mat)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.0
    cam.location = (0.0, 0.0, 5.0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 0
    scene.render.resolution_x = scene.render.resolution_y = 4
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    fmt = scene.render.image_settings
    fmt.file_format, fmt.color_depth = "OPEN_EXR", "32"
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")

    def shot(name):
        path = folder / f"{name}.exr"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(path))
        px = np.empty(img.size[0] * img.size[1] * 4, np.float32)
        img.pixels.foreach_get(px)
        bpy.data.images.remove(img)
        return float(px.reshape(-1, 4)[:, 0].mean())

    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 1.0
    sun.data.angle = 0.0
    scene.collection.objects.link(sun)
    sun_value = shot("sun")
    sun.data.energy = 0.0
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    world_value = shot("world")
    return {"sun": sun_value, "world": world_value}


try:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    import keyforce_tools as kt

    kt.register()
    scene = bpy.context.scene
    look = scene.view_settings
    info = {"view_transform": look.view_transform, "look": look.look, "exposure": look.exposure,
            "gamma": look.gamma, "display": scene.display_settings.display_device,
            "lut": [LUT_N, LUT_LO, LUT_HI], "blur": list(kt.WORLD_BLUR_SIZE),
            "saturation": kt.WORLD_SATURATION, "ground_lift": kt.WORLD_GROUND_LIFT,
            "blender": bpy.app.version_string}
    info["worlds"] = worlds(kt)
    lut(scene)
    info["units"] = units(scene)
    (folder / "look.json").write_text(json.dumps(info), encoding="utf-8")
except Exception as error:
    traceback.print_exc()
    (folder / "look.json").write_text(json.dumps({"error": str(error)}), encoding="utf-8")
