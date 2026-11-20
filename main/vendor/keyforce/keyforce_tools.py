"""Keyforce Tools: Blender add-on for TpacTool gallery exports.

Install: Edit > Preferences > Add-ons > (drop-down) Install from Disk > this file.
Panel: 3D Viewport > Sidebar (N) > Keyforce.

Import    - every *_lod<N>.fbx under a chosen folder, with the DDS textures next
            to each FBX:
              *_d.dds -> Base Color (+ Alpha)
              *_s.dds -> R = Metallic, G = Glossiness (Roughness = 1 - G),
                         B = AO (multiplies the base color)
              *_n.dds -> Normal Map, green channel inverted
World     - lights the scene like Material Preview, or with one of Blender's
            built-in studio HDRIs (City by default).
Parts     - on the selected meshes: deletes loose parts that are exact copies
            (positions and UVs) of another, then lays the remaining loose parts
            out in a grid with a fixed gap between them.
UV Stacker - goes through chosen textures one by one, opening every object that
            uses the texture in Edit Mode. You select the UV islands to keep
            (they stay exactly as they are). The others: symmetric islands are
            halved (brighter half kept), near-duplicate and mirrored copies are
            merged, then everything is stacked onto the spot inside the kept
            islands where the texture looks the same (rotations allowed, long
            thin islands cut to fit, strips and tiny islands always moved). Also in
            UV Editor > Sidebar (N) > Keyforce. batch_uv_stack.py runs the same
            passes on a whole file. Rules: CONVENTIONS.md.
UV Fold   - select edges across a UV island: the island is cut there and one
            half mirrored onto the other, its vertices snapped onto the kept
            half. Snap to Active stacks selected islands onto the one
            clicked last. Also in UV Editor > Sidebar (N) > Keyforce.
Bake      - pre-rendered colour texture per source texture (lighting and every
            PBR map baked in).

Panel layout: 1. Import, 2. Automatic Bake (recommended settings, one
button), 3. Manual Bake with the steps Dedupe & Spread, Lighting, UV (UV
Stacker, UV Fold & Snap) and Bake. Every section is a collapsible sub-panel.
"""

bl_info = {
    "name": "Keyforce Tools",
    "author": "Keyforce",
    "version": (1, 17, 1),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Keyforce, UV Editor > Sidebar > Keyforce",
    "description": "Import TpacTool gallery exports with their textures, set up lighting, dedupe and spread mesh "
                   "parts, stack UV islands onto matching texture areas",
    "category": "Import-Export",
}

import math
import os
import re
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Vector


TAG = "keyforce_import"
FILE_TAG = "keyforce_file"
# Same marker as invert_normal_green.py so that script skips these normals.
INVERT_MARKER = "keyforce_invert_normal_green"
WORLD_NAME = "Keyforce - World"
BUILTIN_HDRIS = ("city", "courtyard", "forest", "interior", "night", "studio", "sunrise", "sunset")


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------

BAKED_EXTENSIONS = (".png", ".tga", ".dds", ".jpg")


def discover(root, lod, baked=None):
    """(fbx, color, spec, normal) for every *_lod<lod>.fbx; missing maps are None.
    With a baked folder: color is <baked>/<name>.png (else the original _d.dds),
    no spec, and the normal is the Medieval 2 *_m2_norm.dds beside the FBX."""
    suffix = f"_lod{lod}"
    sets = []
    def has_lod(path):
        return re.search(r"_lod\d+$", path.stem, re.I) is not None
    # An export with one LOD ticked has no suffix (t_rh_cape_a1_d.fbx). In a
    # folder without any *_lod<N>.fbx that file is the only LOD, used whichever
    # LOD is chosen.
    single = [f for f in root.rglob("*.fbx")
              if not has_lod(f) and not any(has_lod(g) for g in f.parent.glob("*.fbx"))]
    for fbx in sorted([*root.rglob(f"*{suffix}.fbx"), *single]):
        base = fbx.stem[:-len(suffix)] if has_lod(fbx) else fbx.stem   # t_md_num_chest_a_d
        # Gear rigged to another skeleton is exported beside the main file
        # (t_md_num_props_a_d_horse_lod0.fbx) and uses the same textures.
        base = base.removesuffix("_horse")
        stem = base.removesuffix("_d")            # t_md_num_chest_a
        def find(name, folder=fbx.parent):
            path = folder / name
            return path if path.is_file() else None
        if baked is None:
            sets.append((fbx, find(base + ".dds"), find(stem + "_s.dds"), find(stem + "_n.dds")))
        else:
            color = next((p for p in (find(base + ext, baked) for ext in BAKED_EXTENSIONS) if p), None)
            sets.append((fbx, color or find(base + ".dds"), None, find(stem + "_m2_norm.dds")))
    return sets


def load_image(path, colorspace):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = colorspace
    if colorspace == "Non-Color":
        # Alpha in data maps must not affect the RGB channels.
        image.alpha_mode = "CHANNEL_PACKED"
    return image


def node_tree_of(owner):
    # use_nodes is deprecated from Blender 5.0, where node trees always exist.
    if owner.node_tree is None:
        owner.use_nodes = True
    return owner.node_tree


def make_material(name, color, spec, normal):
    material = bpy.data.materials.new(name)
    material[TAG] = True
    tree = node_tree_of(material)
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (160, 0)
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    # Base color, multiplied by AO from the spec blue channel.
    ao_mix = nodes.new("ShaderNodeMix")
    ao_mix.data_type = "RGBA"
    ao_mix.blend_type = "MULTIPLY"
    ao_mix.label = "Base x AO"
    ao_mix.location = (-160, 300)
    ao_mix.inputs["Factor"].default_value = 1.0
    ao_mix.inputs["B"].default_value = (1.0, 1.0, 1.0, 1.0)
    links.new(ao_mix.outputs["Result"], shader.inputs["Base Color"])
    if color:
        color_node = nodes.new("ShaderNodeTexImage")
        color_node.label = "Baked color" if color.suffix.lower() != ".dds" else "Diffuse (_d)"
        color_node.location = (-760, 300)
        color_node.image = load_image(color, "sRGB")
        links.new(color_node.outputs["Color"], ao_mix.inputs["A"])
        links.new(color_node.outputs["Alpha"], shader.inputs["Alpha"])

    # Spec: R = metallic, G = glossiness (inverted to roughness), B = AO.
    if spec:
        spec_node = nodes.new("ShaderNodeTexImage")
        spec_node.label = "Spec (_s): R Metal, G Gloss, B AO"
        spec_node.location = (-760, 0)
        spec_node.image = load_image(spec, "Non-Color")
        separate = nodes.new("ShaderNodeSeparateColor")
        separate.location = (-460, 0)
        links.new(spec_node.outputs["Color"], separate.inputs["Color"])
        links.new(separate.outputs["Red"], shader.inputs["Metallic"])
        gloss_to_rough = nodes.new("ShaderNodeMath")
        gloss_to_rough.operation = "SUBTRACT"
        gloss_to_rough.label = "Roughness = 1 - Gloss"
        gloss_to_rough.location = (-160, 0)
        gloss_to_rough.inputs[0].default_value = 1.0
        links.new(separate.outputs["Green"], gloss_to_rough.inputs[1])
        links.new(gloss_to_rough.outputs["Value"], shader.inputs["Roughness"])
        links.new(separate.outputs["Blue"], ao_mix.inputs["B"])
    else:
        shader.inputs["Roughness"].default_value = 0.65

    # Normal into Blender's OpenGL convention before the tangent-space Normal Map
    # node. Bannerlord _n maps are DirectX: invert green. TpacTool's _m2_norm maps
    # have both X and Y flipped against Bannerlord's: invert red.
    if normal:
        m2 = normal.stem.lower().endswith("_m2_norm")
        channel, axis = (0, "Red") if m2 else (1, "Green")
        normal_node = nodes.new("ShaderNodeTexImage")
        normal_node.label = "Normal (_m2_norm)" if m2 else "Normal (_n)"
        normal_node.location = (-760, -340)
        normal_node.image = load_image(normal, "Non-Color")
        curve = nodes.new("ShaderNodeRGBCurve")
        # The marker also keeps invert_normal_green.py off these normals.
        curve[INVERT_MARKER] = True
        curve.name = f"Normal - Invert {axis}"
        curve.label = f"Normal: {axis} = 1 - {axis}"
        curve.location = (-460, -340)
        curve.width = 240
        curve.inputs["Fac"].default_value = 1.0
        curve.mapping.initialize()
        flipped = curve.mapping.curves[channel]
        flipped.points[0].location = (0.0, 1.0)
        flipped.points[-1].location = (1.0, 0.0)
        for point in flipped.points:
            point.handle_type = "VECTOR"
        curve.mapping.update()
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.location = (-160, -340)
        normal_map.space = "TANGENT"
        links.new(normal_node.outputs["Color"], curve.inputs["Color"])
        links.new(curve.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])

    # Blender 4.2+ uses surface_render_method; older releases use blend_method.
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "HASHED"
    return material


# Mesh type prefixes and gear words of Bannerlord / TAOM mesh names, for clean_name.
TYPE_TOKENS = {"sm", "sk", "clo", "bo", "cap", "wm"}
ITEM_WORDS = {
    # gear
    "helmet", "helm", "hood", "chest", "torso", "armor", "armour", "plate", "hplate", "chainmail", "scalemail",
    "scale", "leather", "tunic", "dress", "robe", "coat", "cape", "cloak", "tabard", "skirt", "pauld",
    "pauldron", "pauldrons", "shoulder", "bracer", "bracers", "gauntlet", "gauntlets", "gloves", "hands",
    "grvs", "greaves", "boots", "shoes", "feet", "legs", "body", "head", "beard", "hair", "basemesh", "barding",
    "saddle", "harness", "horse",
    # weapons
    "shield", "sword", "blade", "guard", "handle", "pommel", "axe", "mace", "hammer", "mattock", "spear",
    "lance", "pike", "pik", "halberd", "polearm", "glaive", "dagger", "knife", "bow", "longbow", "crossbow",
    "quiver", "arrow", "arrows", "bolt", "javelin", "1h", "2h",
    # troop class and grade
    "inf", "infantry", "infrantry", "cav", "cavalry", "arc", "arch", "archer", "nob", "noble", "lord",
    "captain", "knight", "elite", "heavy", "med", "medium", "light",
}


def clean_name(name):
    """sm_md_num_barding_elite_a.lod2.1 -> barding_elite_a: drops the export and
    Blender suffixes (.lod2, .1), the mesh type (sm_, sk_, clo_, bo_cap_ ...) and
    the faction code (md_num, rh_loke, uruk_hai, gn_orc_brt ...), which ends at the
    first gear word or is taken to be two words. At least two words are kept."""
    base = re.sub(r"(\.lod\d+)?(\.\d+)*$", "", name, flags=re.IGNORECASE)
    tokens = base.split("_")
    while len(tokens) > 2 and tokens[0].lower() in TYPE_TOKENS:
        tokens = tokens[1:]
    first = next((i for i, token in enumerate(tokens[:4]) if token.lower() in ITEM_WORDS), None)
    drop = min(first if first is not None else 2, max(len(tokens) - 2, 0))
    # Never start on a lone letter (spider_forest_a_2o keeps forest_a_2o).
    while drop > 0 and len(tokens[drop]) <= 1:
        drop -= 1
    return "_".join(tokens[drop:])


def make_static(imported, meshes, before_actions):
    """Deletes the armatures, armature modifiers and empty nodes of one FBX,
    keeping every mesh where it is. Returns the objects that are left."""
    for obj in meshes:
        matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = matrix
        for modifier in [m for m in obj.modifiers if m.type == "ARMATURE"]:
            obj.modifiers.remove(modifier)
    for obj in [o for o in imported if o.type in {"ARMATURE", "EMPTY"}]:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            bpy.data.armatures.remove(data)
    # The armatures' animations: the importer gives them a fake user.
    for action in set(bpy.data.actions) - before_actions:
        if action.users <= int(action.use_fake_user):
            bpy.data.actions.remove(action)
    return set(meshes)


def import_folder(root, lod, report, static=False, only=None, baked=None, rename=True):
    """Imports every *_lod<lod>.fbx under root, or just the one at `only`.
    With `baked`: baked color textures from that folder and _m2_norm normals."""
    sets = discover(root, lod, baked)
    if only is not None:
        sets = [s for s in sets if s[0] == only]
    if not sets:
        raise FileNotFoundError(f"No *_lod{lod}.fbx (or single-LOD *.fbx) files found under {root}" if only is None
                                else f"Not found: {only}")
    key = f"{root.name} - LOD {lod}"
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    # Remove a previous import of this folder and LOD (or of the one file) only.
    # Never clear the user's scene.
    def previous(item):
        return item.get(TAG) == key and (only is None or item.get(FILE_TAG) == str(only))
    for obj in list(bpy.data.objects):
        if previous(obj):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Armature) and data.users == 0:
                bpy.data.armatures.remove(data)
            elif isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
    for action in list(bpy.data.actions):
        if previous(action):
            bpy.data.actions.remove(action)
    for material in list(bpy.data.materials):
        if material.get(TAG) and material.users == 0:
            bpy.data.materials.remove(material)
    collection = bpy.data.collections.get(key)
    if collection is None:
        collection = bpy.data.collections.new(key)
        bpy.context.scene.collection.children.link(collection)

    def sub_collection(fbx):
        # The FBX's folder name, plus _horse for gear rigged to the horse.
        horse = fbx.stem.lower().endswith((f"_horse_lod{lod}", "_horse"))
        name = fbx.parent.name + ("_horse" if horse else "")
        for child in collection.children:
            if child.get(TAG) == name:
                return child
        # Names are unique in a .blend: another LOD's import gets "name.001".
        child = bpy.data.collections.new(name)
        child[TAG] = name
        collection.children.link(child)
        return child

    imported_meshes = []
    missing = []
    materials = {}
    for fbx, color, spec, normal in sets:
        target = sub_collection(fbx)
        if baked is None:
            for label, path in (("_d", color), ("_s", spec), ("_n", normal)):
                if path is None:
                    missing.append(f"{fbx.name}: no {label}.dds")
        else:
            if color is None or color.suffix.lower() == ".dds" and color.parent == fbx.parent:
                missing.append(f"{fbx.name}: no baked color in {baked}" + (", using the original _d.dds" if color else ""))
            if normal is None:
                missing.append(f"{fbx.name}: no _m2_norm.dds")
        before_objects = set(bpy.data.objects)
        before_materials = set(bpy.data.materials)
        before_images = set(bpy.data.images)
        before_actions = set(bpy.data.actions)
        # Disable recursive image lookup. Any materials/images created by the
        # importer are discarded after the replacement material is assigned.
        try:
            bpy.ops.import_scene.fbx(filepath=str(fbx), use_image_search=False)
            imported = set(bpy.data.objects) - before_objects
            meshes = [obj for obj in imported if obj.type == "MESH"]
            if static:
                imported = make_static(imported, meshes, before_actions)
            for action in set(bpy.data.actions) - before_actions:
                action[TAG] = key
                action[FILE_TAG] = str(fbx)
            # The main file and its _horse file share one material.
            texture_key = (color, spec, normal)
            material = materials.get(texture_key)
            if material is None:
                name = (color.stem if color else fbx.stem) + f" - LOD{lod}" + (" - Baked" if baked else "")
                material = materials[texture_key] = make_material(name, color, spec, normal)
            for obj in imported:
                obj[TAG] = key
                obj[FILE_TAG] = str(fbx)
                # The importer links into the active collection, which can be
                # the target itself when it is selected in the Outliner.
                if target not in obj.users_collection:
                    target.objects.link(obj)
                for owner in list(obj.users_collection):
                    if owner != target:
                        owner.objects.unlink(obj)
            for obj in meshes:
                # Clear object-linked overrides as well as mesh material slots.
                for slot in obj.material_slots:
                    slot.link = "DATA"
                obj.data.materials.clear()
                obj.data.materials.append(material)
                for polygon in obj.data.polygons:
                    polygon.material_index = 0
                imported_meshes.append(obj)
                if rename:
                    # Name clashes get Blender's own .001 suffix.
                    obj.name = clean_name(obj.name)
                    obj.data.name = obj.name
            for old_material in set(bpy.data.materials) - before_materials:
                if old_material not in materials.values() and old_material.users == 0:
                    bpy.data.materials.remove(old_material)
            for old_image in set(bpy.data.images) - before_images:
                if old_image.users == 0:
                    bpy.data.images.remove(old_image)
            print(f"[Keyforce] {fbx.name}: {len(meshes)} meshes")
        except Exception:
            # Roll back this FBX so a failed import cannot leave original
            # materials on partially imported objects.
            for obj in set(bpy.data.objects) - before_objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            for mat in set(bpy.data.materials) - before_materials:
                if mat.users == 0:
                    bpy.data.materials.remove(mat)
            for img in set(bpy.data.images) - before_images:
                if img.users == 0:
                    bpy.data.images.remove(img)
            raise

    for line in missing:
        report({"WARNING"}, line)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported_meshes:
        obj.select_set(True)
    if imported_meshes:
        bpy.context.view_layer.objects.active = imported_meshes[0]
    return len(sets), len(imported_meshes), len(missing)


# --------------------------------------------------------------------------
# World
# --------------------------------------------------------------------------

def view3d_shading():
    return next((area.spaces.active.shading for screen in bpy.data.screens
                 for area in screen.areas if area.type == "VIEW_3D"), None)


def builtin_hdri(name):
    return Path(bpy.utils.system_resource("DATAFILES", path="studiolights/world")) / f"{name}.exr"


def set_world(choice, show_hdri):
    """choice: 'PREVIEW' (match Material Preview) or a built-in HDRI name."""
    rotation, strength = 0.0, 1.0
    if choice == "PREVIEW":
        shading = view3d_shading()
        hdri = None
        if shading is not None:
            light = bpy.context.preferences.studio_lights.get(shading.studio_light)
            if light is not None and light.type == "WORLD" and Path(light.path).is_file():
                hdri = Path(light.path)
            rotation = shading.studiolight_rotate_z
            strength = shading.studiolight_intensity
        if hdri is None:
            hdri = builtin_hdri("forest")
    else:
        hdri = builtin_hdri(choice)
    if not hdri.is_file():
        raise FileNotFoundError(f"HDRI not found: {hdri}")

    world = bpy.data.worlds.get(WORLD_NAME) or bpy.data.worlds.new(WORLD_NAME)
    tree = node_tree_of(world)
    nodes = tree.nodes
    links = tree.links
    nodes.clear()
    coords = nodes.new("ShaderNodeTexCoord")
    coords.location = (-900, 0)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-700, 0)
    mapping.inputs["Rotation"].default_value[2] = rotation
    links.new(coords.outputs["Generated"], mapping.inputs["Vector"])
    env = nodes.new("ShaderNodeTexEnvironment")
    env.location = (-500, 0)
    env.image = bpy.data.images.load(str(hdri), check_existing=True)
    links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    light = nodes.new("ShaderNodeBackground")
    light.location = (-200, 80)
    light.inputs["Strength"].default_value = strength
    links.new(env.outputs["Color"], light.inputs["Color"])
    output = nodes.new("ShaderNodeOutputWorld")
    output.location = (280, 0)
    if show_hdri:
        links.new(light.outputs["Background"], output.inputs["Surface"])
    else:
        # The HDRI lights the scene; the camera sees a neutral dark grey.
        backdrop = nodes.new("ShaderNodeBackground")
        backdrop.label = "Camera backdrop"
        backdrop.location = (-200, -120)
        backdrop.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1.0)
        path = nodes.new("ShaderNodeLightPath")
        path.location = (-200, 380)
        mix = nodes.new("ShaderNodeMixShader")
        mix.location = (60, 0)
        links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
        links.new(light.outputs["Background"], mix.inputs[1])
        links.new(backdrop.outputs["Background"], mix.inputs[2])
        links.new(mix.outputs["Shader"], output.inputs["Surface"])
    bpy.context.scene.world = world
    return hdri.name


# --------------------------------------------------------------------------
# Dedupe and spread parts
# --------------------------------------------------------------------------

def loose_parts(bm):
    """Vertex lists of the parts L selects (connected through edges)."""
    bm.verts.index_update()
    seen = set()
    parts = []
    for start in bm.verts:
        if start.index in seen:
            continue
        seen.add(start.index)
        stack = [start]
        part = []
        while stack:
            vert = stack.pop()
            part.append(vert)
            for edge in vert.link_edges:
                other = edge.other_vert(vert)
                if other.index not in seen:
                    seen.add(other.index)
                    stack.append(other)
        parts.append(part)
    return parts


def part_signature(verts, matrix, uv_layer, match, precision):
    """What makes two parts duplicates, independent of vertex order.
    UV: vertex and face count plus the UVs of every face corner, wherever the
    parts are. EXACT: faces as loops of (world position, uv). SHAPE: as EXACT,
    measured from each part's own corner so it may lie anywhere."""
    faces = {face for vert in verts for face in vert.link_faces}
    if match == "UV" and uv_layer is not None and faces:
        uvs = sorted((round(loop[uv_layer].uv.x, precision) + 0.0, round(loop[uv_layer].uv.y, precision) + 0.0)
                     for face in faces for loop in face.loops)
        return ("uv", len(verts), len(faces), tuple(uvs))

    world = {vert: matrix @ vert.co for vert in verts}
    origin = Vector((0.0, 0.0, 0.0))
    if match != "EXACT":
        origin = Vector(tuple(min(co[i] for co in world.values()) for i in range(3)))

    def point(vert):
        co = world[vert] - origin
        return (round(co.x, precision) + 0.0, round(co.y, precision) + 0.0, round(co.z, precision) + 0.0)

    if not faces:
        return ("loose", tuple(sorted(point(vert) for vert in verts)))
    signature = []
    for face in faces:
        loops = []
        for loop in face.loops:
            key = point(loop.vert)
            if uv_layer is not None:
                uv = loop[uv_layer].uv
                key += (round(uv.x, precision) + 0.0, round(uv.y, precision) + 0.0)
            loops.append(key)
        first = loops.index(min(loops))
        signature.append(tuple(loops[first:] + loops[:first]))
    signature.sort()
    return (len(verts), tuple(signature))


UV_GRID = 64  # cells per UV unit when comparing UV layouts


def part_material(obj, verts):
    """The material of a part, so parts using different textures never match."""
    face = next((f for v in verts for f in v.link_faces), None)
    if face is None or face.material_index >= len(obj.material_slots):
        return None
    material = obj.material_slots[face.material_index].material
    return material.name if material else None


class FuzzyPart:
    """A loose part reduced to what the % tolerance compares."""

    def __init__(self, obj, verts, uv_layer):
        self.obj = obj
        self.verts = verts
        faces = {face for vert in verts for face in vert.link_faces}
        self.vert_count = len(verts)
        self.face_count = len(faces)
        self.material = part_material(obj, verts)
        # The UV layout as the set of grid cells its face corners fall in.
        self.cells = frozenset((math.floor(loop[uv_layer].uv.x * UV_GRID), math.floor(loop[uv_layer].uv.y * UV_GRID))
                               for face in faces for loop in face.loops)

    def matches(self, other, tolerance):
        if self.material != other.material:
            return False
        for a, b in ((self.vert_count, other.vert_count), (self.face_count, other.face_count)):
            if abs(a - b) > tolerance * max(a, b):
                return False
        if not self.cells or not other.cells:
            return False
        # Share of UV cells in common (1 = the same layout).
        common = len(self.cells & other.cells)
        return common >= (1.0 - tolerance) * len(self.cells | other.cells)


def find_duplicates(meshes, match, precision, tolerance):
    """{bmesh: [verts to delete]} and the number of parts removed."""
    duplicates = {id(bm): [] for _, bm in meshes}
    removed = 0
    if match == "UV" and tolerance > 0:
        parts = []
        for obj, bm in meshes:
            uv_layer = bm.loops.layers.uv.active
            if uv_layer is None:
                continue
            parts += [(bm, FuzzyPart(obj, verts, uv_layer)) for verts in loose_parts(bm)]
        # Most complete version first, so it is the one kept.
        parts.sort(key=lambda p: (-p[1].vert_count, -p[1].face_count))
        kept = []
        for bm, part in parts:
            if any(part.matches(other, tolerance) for other in kept):
                duplicates[id(bm)].extend(part.verts)
                removed += 1
            else:
                kept.append(part)
        return duplicates, removed

    kept = set()
    for obj, bm in meshes:
        uv_layer = bm.loops.layers.uv.active
        for verts in loose_parts(bm):
            signature = (part_material(obj, verts),
                         part_signature(verts, obj.matrix_world, uv_layer, match, precision))
            if signature in kept:
                duplicates[id(bm)].extend(verts)
                removed += 1
            else:
                kept.add(signature)
    return duplicates, removed


def move_uvs_into_tile(obj, bm):
    """Moves every UV island by whole units so it lies in the 0-1 space.
    Returns the number of islands that cross a tile border and can't be moved."""
    from bpy_extras.bmesh_utils import bmesh_linked_uv_islands
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        return 0
    eps = 1e-4
    crossing = 0
    for faces in bmesh_linked_uv_islands(bm, uv_layer):
        uvs = [loop[uv_layer].uv for face in faces for loop in face.loops]
        if not uvs:
            continue
        shift = []
        for axis in (0, 1):
            low = min(uv[axis] for uv in uvs)
            high = max(uv[axis] for uv in uvs)
            tile = math.floor(low + eps)
            if high > tile + 1 + eps:
                shift = None
                break
            shift.append(-tile)
        if shift is None:
            crossing += 1
        elif shift != [0, 0]:
            offset = Vector(shift)
            for uv in uvs:
                uv += offset
    return crossing


def dedupe_parts(obj, settings):
    """Deletes the duplicate loose parts of one mesh object, as Dedupe & Spread
    does with the Parts section's settings (Match, Precision, Tolerance, Move
    UVs into 0-1). For the bake's temporary copy. Returns the number removed."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if settings.into_tile:
        move_uvs_into_tile(obj, bm)
    duplicates, removed = find_duplicates([(obj, bm)], settings.match, settings.precision, settings.tolerance / 100.0)
    if duplicates[id(bm)]:
        bmesh.ops.delete(bm, geom=duplicates[id(bm)], context="VERTS")
    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()
    return removed


def dedupe_and_spread(objects, gap, match, precision, tolerance, into_tile=True):
    meshes = []
    seen_data = set()
    for obj in objects:
        # Linked duplicates share one mesh: process it once.
        if obj.type != "MESH" or obj.data in seen_data:
            continue
        seen_data.add(obj.data)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        meshes.append((obj, bm))

    # 0. UV islands moved by whole tiles into 0-1, so copies in other tiles match too.
    crossing = {}
    if into_tile:
        for obj, bm in meshes:
            count = move_uvs_into_tile(obj, bm)
            if count:
                crossing[obj.name] = count

    # 1. Delete parts matching one kept before (any selected object).
    duplicates, removed = find_duplicates(meshes, match, precision, tolerance)
    for obj, bm in meshes:
        if duplicates[id(bm)]:
            bmesh.ops.delete(bm, geom=duplicates[id(bm)], context="VERTS")

    # 2. Lay the remaining parts out in a grid in the XY plane, keeping Z.
    parts = []
    for obj, bm in meshes:
        matrix = obj.matrix_world
        for verts in loose_parts(bm):
            world = [matrix @ vert.co for vert in verts]
            low = Vector(tuple(min(co[i] for co in world) for i in range(3)))
            high = Vector(tuple(max(co[i] for co in world) for i in range(3)))
            parts.append((obj, bm, verts, low, high))
    if parts:
        columns = math.ceil(math.sqrt(len(parts)))
        start_x = min(p[3].x for p in parts)
        y = min(p[3].y for p in parts)
        for row in range(0, len(parts), columns):
            x = start_x
            depth = 0.0
            for obj, bm, verts, low, high in parts[row:row + columns]:
                delta = Vector((x - low.x, y - low.y, 0.0))
                local = obj.matrix_world.inverted().to_3x3() @ delta
                bmesh.ops.translate(bm, vec=local, verts=verts)
                for layer in bm.verts.layers.shape.values():
                    for vert in verts:
                        vert[layer] += local
                x += (high.x - low.x) + gap
                depth = max(depth, high.y - low.y)
            y += depth + gap

    for obj, bm in meshes:
        bm.to_mesh(obj.data)
        obj.data.update()
        bm.free()
    return removed, len(parts), crossing


# --------------------------------------------------------------------------
# UV islands inside other UV islands
# --------------------------------------------------------------------------

UV_RES = 256  # coverage cells per UV unit


class Island:
    def __init__(self, obj, faces, uv_layer):
        self.obj = obj
        self.face_indices = [face.index for face in faces]
        slots = obj.material_slots
        index = faces[0].material_index
        self.material = slots[index].material.name if index < len(slots) and slots[index].material else None
        self.triangles = []
        for face in faces:
            uvs = [loop[uv_layer].uv.copy() for loop in face.loops]
            self.triangles += [(uvs[0], uvs[i], uvs[i + 1]) for i in range(1, len(uvs) - 1)]
        self.points = [uv for tri in self.triangles for uv in tri]
        self.low = Vector((min(p.x for p in self.points), min(p.y for p in self.points)))
        self.high = Vector((max(p.x for p in self.points), max(p.y for p in self.points)))
        self.area = sum(abs((b - a).cross(c - a)) / 2 for a, b, c in self.triangles)
        self._cells = None

    def cells(self):
        """UV grid cells the island covers, grown by one cell for its border."""
        if self._cells is None:
            from mathutils.geometry import intersect_point_tri_2d
            cells = set()
            for a, b, c in self.triangles:
                for p in (a, b, c):
                    cells.add((math.floor(p.x * UV_RES), math.floor(p.y * UV_RES)))
                for x in range(math.floor(min(a.x, b.x, c.x) * UV_RES), math.floor(max(a.x, b.x, c.x) * UV_RES) + 1):
                    for y in range(math.floor(min(a.y, b.y, c.y) * UV_RES), math.floor(max(a.y, b.y, c.y) * UV_RES) + 1):
                        if (x, y) not in cells and intersect_point_tri_2d(
                                Vector(((x + 0.5) / UV_RES, (y + 0.5) / UV_RES)), a, b, c):
                            cells.add((x, y))
            self._cells = {(x + dx, y + dy) for x, y in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        return self._cells

    def inside(self, other, smaller):
        """Whether this island lies within the other's UVs and is clearly smaller."""
        if self.material != other.material or self.area >= other.area * smaller:
            return False
        if (self.low.x < other.low.x - 1e-4 or self.low.y < other.low.y - 1e-4 or
                self.high.x > other.high.x + 1e-4 or self.high.y > other.high.y + 1e-4):
            return False
        cells = other.cells()
        return all((math.floor(p.x * UV_RES), math.floor(p.y * UV_RES)) in cells for p in self.points)


def find_inner_islands(objects, smaller):
    """{object: face indices} of UV islands lying inside a bigger island of the
    same material (any selected object)."""
    from bpy_extras.bmesh_utils import bmesh_linked_uv_islands
    islands = []
    seen_data = set()
    for obj in objects:
        if obj.type != "MESH" or obj.data in seen_data:
            continue
        seen_data.add(obj.data)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is not None:
            bm.faces.ensure_lookup_table()
            islands += [Island(obj, faces, uv_layer) for faces in bmesh_linked_uv_islands(bm, uv_layer) if faces]
        bm.free()
    # Biggest first: an island only needs checking against bigger ones.
    islands.sort(key=lambda island: -island.area)
    found = {}
    for i, island in enumerate(islands):
        if island.area <= 0:
            continue
        if any(island.inside(bigger, smaller) for bigger in islands[:i]):
            found.setdefault(island.obj, []).extend(island.face_indices)
    return found


def select_faces(obj, face_indices):
    """Selects exactly these faces (with their edges and vertices) in object mode."""
    mesh = obj.data
    selected = set(face_indices)
    verts, edges = set(), set()
    for polygon in mesh.polygons:
        polygon.select = polygon.index in selected
        if polygon.select:
            verts.update(polygon.vertices)
            edges.update(mesh.loops[i].edge_index for i in polygon.loop_indices)
    for vert in mesh.vertices:
        vert.select = vert.index in verts
    for edge in mesh.edges:
        edge.select = edge.index in edges


# --------------------------------------------------------------------------
# UV island stacking
# --------------------------------------------------------------------------
# Moves UV islands onto spots inside other islands where the texture looks the
# same (black onto black, white onto white, half/half onto a matching edge,
# 0/90/180/270 degree rotations), so they reuse texels instead of taking their
# own UV space. Same-shaped islands are stacked exactly on top of each other;
# long thin islands that fit nowhere whole are cut into pieces that do. Scale
# never changes and nothing is mirrored.

STACK_RES = 1024       # texture resolution used for matching
STACK_MARGIN = 1       # keep stacked islands this many matching pixels inside the destination
STACK_SHAPE_TOL = 0.03  # shapes count as "the same" within this fraction of their size
STACK_SPLIT_ASPECT = 4.0  # islands at least this many times longer than wide may be cut to fit
STACK_COARSE = 4       # the rough search runs on the texture shrunk this many times
STACK_CANDIDATES = 24  # best rough spots that get checked exactly
STACK_ROTATIONS = [np.array(m, float) for m in
                   ([[1, 0], [0, 1]], [[0, -1], [1, 0]], [[-1, 0], [0, -1]], [[0, 1], [-1, 0]])]


def base_color_image(material):
    """Image feeding Base Color, else the first sRGB image texture."""
    if not material or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            links = node.inputs["Base Color"].links
            if links and links[0].from_node.type == "TEX_IMAGE":
                return links[0].from_node.image
    for node in material.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image and node.image.colorspace_settings.name == "sRGB":
            return node.image
    return None


def meshes_by_image():
    """{color image: mesh objects whose active material uses it}."""
    by_image = {}
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            image = base_color_image(obj.active_material)
            if image:
                by_image.setdefault(image, []).append(obj)
    return by_image


def load_pixels(image):
    """RGB array (rows from v=0 upwards) shrunk to about STACK_RES."""
    w, h = image.size
    px = np.empty(w * h * 4, np.float32)
    image.pixels.foreach_get(px)
    arr = px.reshape(h, w, 4)[:, :, :3]
    f = max(1, max(w, h) // STACK_RES)
    if w % f == 0 and h % f == 0:
        arr = arr.reshape(h // f, f, w // f, f, 3).mean(axis=(1, 3))
    else:
        arr = arr[::f, ::f]
    return np.ascontiguousarray(arr)


def raster(tris, h, w, ox=0.0, oy=0.0, edges=False):
    """Boolean mask of triangles (T,3,2) on a grid whose pixel (i,j) centre is
    (ox+i+0.5, oy+j+0.5). edges=True also marks pixels touched by triangle
    edges so slivers thinner than a pixel still show up."""
    m = np.zeros((h, w), bool)
    for a, b, c in tris:
        lo = np.minimum(np.minimum(a, b), c)
        hi = np.maximum(np.maximum(a, b), c)
        x0, y0 = max(int(np.floor(lo[0] - ox)), 0), max(int(np.floor(lo[1] - oy)), 0)
        x1, y1 = min(int(np.ceil(hi[0] - ox)), w), min(int(np.ceil(hi[1] - oy)), h)
        if x1 > x0 and y1 > y0:
            X, Y = np.meshgrid(np.arange(x0, x1) + 0.5 + ox, np.arange(y0, y1) + 0.5 + oy)
            d1 = (b[0] - a[0]) * (Y - a[1]) - (b[1] - a[1]) * (X - a[0])
            d2 = (c[0] - b[0]) * (Y - b[1]) - (c[1] - b[1]) * (X - b[0])
            d3 = (a[0] - c[0]) * (Y - c[1]) - (a[1] - c[1]) * (X - c[0])
            m[y0:y1, x0:x1] |= ((d1 >= 0) & (d2 >= 0) & (d3 >= 0)) | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))
        if edges:
            for p, q in ((a, b), (b, c), (c, a)):
                n = int(np.ceil(np.abs(q - p).max() * 2)) + 2
                t = np.linspace(0, 1, n)[:, None]
                s = np.floor(p + (q - p) * t - (ox, oy)).astype(int)
                ok = (s[:, 0] >= 0) & (s[:, 0] < w) & (s[:, 1] >= 0) & (s[:, 1] < h)
                m[s[ok, 1], s[ok, 0]] = True
    return m


class StackIsland:
    """A UV island (or piece of one) in texture pixel space."""

    def __init__(self, obj, faces, uv_layer, scale):
        self.obj, self.faces, self.uv = obj, faces, uv_layer
        self.loops = [loop for face in faces for loop in face.loops]
        self.px = np.array([loop[uv_layer].uv for loop in self.loops], float) * scale
        tris, self.area = [], 0.0
        for face in faces:
            p = np.array([loop[uv_layer].uv for loop in face.loops], float)
            for i in range(1, len(p) - 1):
                tris.append((p[0], p[i], p[i + 1]))
                e1, e2 = p[i] - p[0], p[i + 1] - p[0]
                self.area += abs(e1[0] * e2[1] - e1[1] * e2[0]) / 2
        self.tris = np.array(tris, float).reshape(-1, 3, 2) * scale
        self.verts = np.unique(np.round(self.px, 4), axis=0)
        self.c = self.verts.mean(axis=0)
        self.size = max(np.ptp(self.verts, axis=0).max(), 1e-6)
        # Area centroid: unlike the vertex mean it doesn't depend on the topology.
        t = self.tris
        e1, e2 = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
        a = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / 2
        self.ac = (a[:, None] * t.mean(axis=1)).sum(axis=0) / a.sum() if a.sum() > 0 else self.c


def align(rep, island):
    """Rotation R with (island.verts - island.c) @ R.T ~= rep.verts - rep.c, or None."""
    if len(island.faces) != len(rep.faces) or len(island.verts) != len(rep.verts) \
            or abs(island.area - rep.area) > STACK_SHAPE_TOL * rep.area + 1e-9:
        return None
    a = rep.verts - rep.c
    tol = STACK_SHAPE_TOL * rep.size
    for R in STACK_ROTATIONS:
        b = (island.verts - island.c) @ R.T
        d = np.linalg.norm(a[:, None] - b[None], axis=2)
        if max(d.min(0).max(), d.min(1).max()) <= tol:
            return R
    return None


def long_axis(island):
    """(length / width, unit vector of the long direction) of an island."""
    pts = island.verts - island.c
    if len(pts) < 2:
        return 1.0, np.array([1.0, 0.0])
    axis = np.linalg.eigh(pts.T @ pts)[1][:, 1]
    length = np.ptp(pts @ axis)
    width = np.ptp(pts @ np.array([-axis[1], axis[0]]))
    return length / max(width, 1e-6), axis


class PatchMatcher:
    """Masked sum-of-squared-differences search over the destination mask.
    A rough pass on a shrunken texture scores every position at once with FFT
    correlation; the best few spots are then checked exactly at full size."""

    def __init__(self, img, dest_mask):
        self.img, self.dest = img, dest_mask
        self.h, self.w = dest_mask.shape
        self.levels = {}

    def level(self, f):
        """FFTs of the texture and destination mask shrunk f times (cached)."""
        if f not in self.levels:
            hc, wc = self.h // f, self.w // f
            img_c = self.img[:hc * f, :wc * f].reshape(hc, f, wc, f, 3).mean(axis=(1, 3))
            out_c = (~self.dest[:hc * f, :wc * f]).reshape(hc, f, wc, f).mean(axis=(1, 3))
            self.levels[f] = (hc, wc, [np.fft.rfft2(img_c[:, :, c]) for c in range(3)],
                              np.fft.rfft2((img_c ** 2).sum(axis=2)), np.fft.rfft2(out_c))
        return self.levels[f]

    def search(self, tmpl, mask, f=None):
        """(mean squared error, x, y) of the best spot for the patch, or None."""
        th, tw = mask.shape
        if th > self.h or tw > self.w:
            return None
        if f is None:
            # Thin islands vanish when shrunk, so they get a finer rough pass.
            f = STACK_COARSE
            while f > 1 and min(th, tw) < 2 * f:
                f //= 2
        hc, wc, f_img, f_sq, f_out = self.level(f)

        def pad(k):
            out = np.zeros((hc, wc))
            out[:k.shape[0], :k.shape[1]] = k
            return np.conj(np.fft.rfft2(out))

        # Rough patch: mask coverage and mean colour per f x f block.
        bh, bw = -(-th // f), -(-tw // f)
        m = np.zeros((bh * f, bw * f))
        m[:th, :tw] = mask
        t = np.zeros((bh * f, bw * f, 3))
        t[:th, :tw] = tmpl
        msum = m.reshape(bh, f, bw, f).sum(axis=(1, 3))
        tc = (m[:, :, None] * t).reshape(bh, f, bw, f, 3).sum(axis=(1, 3)) / np.maximum(msum, 1e-9)[:, :, None]
        mc = msum / (f * f)

        fm = pad(mc)
        cross = sum(f_img[c] * pad(mc * tc[:, :, c]) for c in range(3))
        ssd = np.fft.irfft2(f_sq * fm - 2 * cross, s=(hc, wc))
        outside = np.fft.irfft2(f_out * fm, s=(hc, wc))
        ny, nx = hc - bh + 1, wc - bw + 1
        # Rank by colour error plus the share of the patch hanging outside the
        # destination, so spots fully inside come first (dark patches otherwise
        # rank best over the black background between islands).
        out_share = outside[:ny, :nx] / mc.sum()
        rank = ssd[:ny, :nx] / (mc.sum() * 3) + out_share
        rank[out_share > 0.5] = np.inf
        cand = np.argsort(rank, axis=None)[:STACK_CANDIDATES]
        cand = cand[np.isfinite(rank.ravel()[cand])]

        # Exact check around each candidate at full size.
        jj, ii = np.nonzero(mask)
        tv = tmpl[jj, ii]
        d = np.arange(-f, f + 1)
        best = None
        for k in cand:
            yc, xc = divmod(int(k), nx)
            ys = (yc * f + d[:, None] + 0 * d[None]).ravel()
            xs = (xc * f + 0 * d[:, None] + d[None]).ravel()
            ok = (ys >= 0) & (xs >= 0) & (ys + th <= self.h) & (xs + tw <= self.w)
            ys, xs = ys[ok], xs[ok]
            if not len(ys):
                continue
            Y, X = ys[:, None] + jj[None], xs[:, None] + ii[None]
            inside = self.dest[Y, X].all(axis=1)
            if not inside.any():
                continue
            err = ((self.img[Y[inside], X[inside]] - tv) ** 2).sum(axis=(1, 2))
            i = np.argmin(err)
            if best is None or err[i] < best[0]:
                best = (err[i], xs[inside][i], ys[inside][i])
        if best is None:
            # Every rough spot hung over an edge once checked exactly: search
            # again at full size, where "inside" is measured exactly.
            return self.search(tmpl, mask, 1) if f > 1 else None
        return best[0] / (len(jj) * 3), best[1], best[2]


def stack_template(group, R):
    """Mask of the group's first island rotated by R, its grid origin, the mask
    pixels and where they sit in the unrotated island."""
    rep = group[0][0]
    q = (rep.tris - rep.c) @ R.T
    o = np.floor(q.reshape(-1, 2).min(axis=0))
    tw, th = (np.floor(q.reshape(-1, 2).max(axis=0) - o) + 1).astype(int)
    mask = raster(q, th, tw, o[0], o[1], edges=True)
    jj, ii = np.nonzero(mask)
    p = (np.stack([ii, jj], 1) + 0.5 + o) @ R
    return o, mask, jj, ii, p


def collect_islands(objects, scale):
    """{object: bmesh} and every UV island of the objects (in Edit Mode)."""
    from bpy_extras.bmesh_utils import bmesh_linked_uv_islands
    bms, islands = {}, []
    for obj in objects:
        bm = bmesh.from_edit_mesh(obj.data)
        bms[obj] = bm
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is not None:
            islands += [StackIsland(obj, faces, uv_layer, scale) for faces in bmesh_linked_uv_islands(bm, uv_layer)]
    return bms, islands


def stack_islands(img, movers, dests, max_error, split, progress=None, groups=None):
    """Move `movers` onto the best matching spots inside `dests`. Long thin
    islands that don't fit whole are cut into pieces that do (if `split`).
    `groups` ([(island, R)] lists, see below) replaces the same-shape grouping.
    Returns (pieces left without a match, islands stacked whole, islands split)."""
    h, w = img.shape[:2]
    scale = np.array([w, h], float)
    dest = np.zeros((h, w), bool)
    for island in dests:
        dest |= raster(island.tris, h, w)
    for _ in range(STACK_MARGIN):
        e = dest.copy()
        e[1:] &= dest[:-1]
        e[:-1] &= dest[1:]
        e[:, 1:] &= dest[:, :-1]
        e[:, :-1] &= dest[:, 1:]
        dest = e
    matcher = PatchMatcher(img, dest)

    # Same-shaped islands move together: [(island, R aligning it to the group's first)].
    if groups is None:
        groups = []
        for island in sorted(movers, key=lambda i: -i.area):
            for group in groups:
                R = align(group[0][0], island)
                if R is not None:
                    group.append((island, R))
                    break
            else:
                groups.append([(island, np.eye(2))])

    def place(group):
        """Move the group onto its best spot, or return False if none is good enough."""
        best = None
        for R in STACK_ROTATIONS:
            o, mask, jj, ii, p = stack_template(group, R)
            # The patch is the texture under every member of the group, averaged.
            cols = np.zeros((len(p), 3))
            for island, Ri in group:
                s = np.floor(island.c + p @ Ri).astype(int)
                cols += img[s[:, 1] % h, s[:, 0] % w]
            tmpl = np.zeros(mask.shape + (3,))
            tmpl[jj, ii] = cols / len(group)
            hit = matcher.search(tmpl, mask)
            if hit and (best is None or hit[0] < best[0]):
                best = (hit[0], np.array(hit[1:], float) - o, R)
        if best is None or best[0] > max_error:
            return False
        _, D, R = best
        for island, Ri in group:
            new = D + ((island.px - island.c) @ Ri.T) @ R.T
            for loop, xy in zip(island.loops, new / scale):
                loop[island.uv].uv = xy
        return True

    def split_place(island):
        """Cut the island in two across its long axis and place each half,
        cutting halves further while still long. Returns pieces that don't fit."""
        aspect, axis = long_axis(island)
        if len(island.faces) < 2 or aspect < 2:
            return [island]
        t = np.array([np.mean([loop[island.uv].uv for loop in face.loops], axis=0)
                      for face in island.faces]) * scale @ axis
        order = np.argsort(t)
        cut = np.searchsorted(t[order], (t.min() + t.max()) / 2)
        cut = min(max(cut, 1), len(order) - 1)
        rest = []
        for half in (order[:cut], order[cut:]):
            piece = StackIsland(island.obj, [island.faces[i] for i in half], island.uv, scale)
            if not place([(piece, np.eye(2))]):
                rest += split_place(piece)
        return rest

    left, stacked, split_count = [], 0, 0
    for n, group in enumerate(groups):
        if progress:
            progress(n / max(len(groups), 1))
        if place(group):
            stacked += len(group)
            continue
        for island, _ in group:
            if split and long_axis(island)[0] >= STACK_SPLIT_ASPECT:
                rest = split_place(island)
                if sum(len(piece.faces) for piece in rest) < len(island.faces):
                    split_count += 1
                left += rest
            else:
                left.append(island)
    return left, stacked, split_count


# Whole-texture optimisation (CONVENTIONS.md): symmetric islands are halved,
# near-duplicate and mirrored copies merged, then the rest stacked.

STACK_BIG_AREA = 0.02      # batch rules: islands at least this big (fraction of 0-1 UV space) and not
                           # thin strips receive the others
STACK_TINY_AREA = 0.0005   # tiny islands always move, matching texture or not
STACK_SYM_MIN_AREA = 0.002  # smaller islands aren't worth halving
STACK_MATCH_IOU = 0.88     # outline overlap for "same shape" and "symmetric"
STACK_SIZE_TOL = 0.12      # area / extent difference allowed before comparing outlines
STACK_SNAP = 0.03          # vertex snap distance, fraction of the island's size
STACK_MASK_PX = 64         # outline masks are drawn this many pixels across
STACK_ORIENTS = STACK_ROTATIONS + [R @ np.diag([-1.0, 1.0]) for R in STACK_ROTATIONS]  # + mirrored


def islands_of(bms, scale):
    """Every UV island of the bmeshes ({object: bmesh})."""
    from bpy_extras.bmesh_utils import bmesh_linked_uv_islands
    islands = []
    for obj, bm in bms.items():
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is not None:
            islands += [StackIsland(obj, faces, uv_layer, scale) for faces in bmesh_linked_uv_islands(bm, uv_layer)]
    return islands


def sample(img, pts):
    h, w = img.shape[:2]
    s = np.floor(pts).astype(int)
    return img[s[:, 1] % h, s[:, 0] % w]


def pixels(tris):
    """Pixel centres (texture px) covered by the triangles."""
    flat = tris.reshape(-1, 2)
    o = np.floor(flat.min(axis=0))
    w, h = (np.floor(flat.max(axis=0) - o) + 1).astype(int)
    jj, ii = np.nonzero(raster(tris, h, w, o[0], o[1], edges=True))
    return np.stack([ii, jj], 1) + 0.5 + o


def outline_overlap(ta, tb, g):
    """(IoU, shift) of two centred triangle sets drawn g mask px per texture px;
    tb shifted by `shift` (texture px, up to 2 mask px) overlaps ta best."""
    qa, qb = ta * g, tb * g
    flat = np.concatenate([qa.reshape(-1, 2), qb.reshape(-1, 2)])
    o = np.floor(flat.min(axis=0)) - 3
    w, h = (np.ceil(flat.max(axis=0) - o) + 3).astype(int)
    ma, mb = raster(qa, h, w, o[0], o[1]), raster(qb, h, w, o[0], o[1])
    best, sa = (0.0, np.zeros(2)), ma.sum()
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            m = np.roll(np.roll(mb, dy, 0), dx, 1)
            inter = (ma & m).sum()
            union = sa + m.sum() - inter
            if union and inter / union > best[0]:
                best = (inter / union, np.array([dx, dy]) / g)
    return best


def outline_match(a, m, orients=STACK_ORIENTS):
    """(IoU, R, s) with (m.px - m.ac) @ R.T + s ~= a.px - a.ac, or None."""
    if a.area <= 0 or abs(m.area / a.area - 1) > STACK_SIZE_TOL:
        return None
    ea = np.ptp(a.verts - a.ac, axis=0)
    best = None
    for R in orients:
        if np.abs(np.ptp((m.verts - m.ac) @ R.T, axis=0) - ea).max() > STACK_SIZE_TOL * a.size:
            continue
        iou, s = outline_overlap(a.tris - a.ac, (m.tris - m.ac) @ R.T, STACK_MASK_PX / a.size)
        if iou >= STACK_MATCH_IOU and (best is None or iou > best[0]):
            best = (iou, R, s)
    return best


def snap(new, targets, tol):
    """Moves points within `tol` of a target point onto it."""
    d = np.linalg.norm(new[:, None] - targets[None], axis=2)
    i = d.argmin(axis=1)
    close = d[np.arange(len(new)), i] <= tol
    new[close] = targets[i[close]]
    return new


def write_uvs(island, new_px, scale):
    for loop, xy in zip(island.loops, new_px / scale):
        loop[island.uv].uv = xy


def is_rectangle(island, scale):
    """Fills at least 80% of its rotated bounding box (strips, plates)."""
    _, axis = long_axis(island)
    pts = island.verts - island.c
    box = np.ptp(pts @ axis) * np.ptp(pts @ np.array([-axis[1], axis[0]]))
    return box > 0 and island.area * scale[0] * scale[1] >= 0.8 * box


def halve_symmetric(island, img, scale, max_error):
    """If the island is its own mirror image across a line through its middle,
    mirror the darker half onto the brighter half. Returns whether it did."""
    if island.area < STACK_SYM_MIN_AREA or len(island.faces) < 4:
        return False
    pts = island.verts - island.ac
    axes = np.linalg.eigh(pts.T @ pts)[1].T
    angles = {round(float(np.arctan2(v[1], v[0]) % np.pi), 4) for v in axes}
    angles |= {0.0, round(np.pi / 4, 4), round(np.pi / 2, 4), round(3 * np.pi / 4, 4)}
    q = island.tris - island.ac
    best = None
    for theta in angles:
        d = np.array([np.cos(theta), np.sin(theta)])
        F = 2 * np.outer(d, d) - np.eye(2)
        iou, s = outline_overlap(q, q @ F, STACK_MASK_PX / island.size)
        if best is None or iou > best[0]:
            best = (iou, d, F, s)
    iou, d, F, s = best
    if iou < STACK_MATCH_IOU:
        return False
    n = np.array([-d[1], d[0]])
    c0 = island.ac + n * (s @ n) / 2   # a point on the mirror line
    tol = 0.02 * island.size

    # Each face must lie on one side of the line (edges run along it).
    sides = {}
    for face in island.faces:
        dist = (np.array([loop[island.uv].uv for loop in face.loops]) * scale - c0) @ n
        if dist.min() >= -tol:
            sides.setdefault(1, []).append(face)
        elif dist.max() <= tol:
            sides.setdefault(-1, []).append(face)
        else:
            return False
    if len(sides) < 2:
        return False
    halves = {side: StackIsland(island.obj, faces, island.uv, scale) for side, faces in sides.items()}
    if abs(halves[1].area / max(halves[-1].area, 1e-12) - 1) > STACK_SIZE_TOL:
        return False

    luma = np.array([0.2126, 0.7152, 0.0722])
    keep_side = max(halves, key=lambda side: (sample(img, pixels(halves[side].tris)) @ luma).mean())
    keep, move = halves[keep_side], halves[-keep_side]
    # Texture check with brightness removed: the halves should differ in light only.
    kp = pixels(keep.tris)
    a, b = sample(img, kp), sample(img, c0 + (kp - c0) @ F)
    if (((a - a.mean(axis=0)) - (b - b.mean(axis=0))) ** 2).mean() > max_error:
        return False
    write_uvs(move, snap(c0 + (move.px - c0) @ F, keep.verts, STACK_SNAP * island.size), scale)
    return True


def merge_duplicates(islands, img, scale, max_error, locked):
    """Stacks near-duplicate copies (any rotation or mirror) onto the copy whose
    texture fits the others best: a locked copy if the group has one. Locked
    copies never move; copies whose texture differs too much stay.
    Returns (copies moved, copies already on top, faces of copies now on a locked one)."""
    groups = []   # [anchor, [(island, R, s)]]
    for island in sorted((i for i in islands if i.area > 0), key=lambda i: -i.area):
        for group in groups:
            hit = outline_match(group[0], island)
            if hit:
                group[1].append((island, hit[1], hit[2]))
                break
        else:
            groups.append([island, [(island, np.eye(2), np.zeros(2))]])

    moved = already = 0
    on_locked = set()
    for anchor, members in groups:
        if len(members) < 2:
            continue
        q = pixels(anchor.tris - anchor.ac)
        patches = [sample(img, m.ac + (q - s) @ R) for m, R, s in members]
        D = np.array([[((p1 - p2) ** 2).mean() for p2 in patches] for p1 in patches])
        # Fit to the others (ties: the biggest); locked copies first if there are any.
        score = D.sum(axis=1) - 1e-9 * np.array([m.area for m, _, _ in members])
        is_locked = np.array([locked(m) for m, _, _ in members])
        if is_locked.any():
            score[~is_locked] = np.inf
        b = int(np.argmin(score))
        best, Rb, sb = members[b]
        for i, (m, R, s) in enumerate(members):
            if i == b or is_locked[i] or D[b, i] > max_error:
                continue
            new = snap(best.ac + ((m.px - m.ac) @ R.T + s - sb) @ Rb, best.verts, STACK_SNAP * best.size)
            if is_locked[b]:
                on_locked.update(m.faces)
            if np.abs(new - m.px).max() < 0.5:
                already += 1
                continue
            write_uvs(m, new, scale)
            moved += 1
    return moved, already, on_locked


def must_move(island, scale):
    """Rectangles, thin strips and tiny islands always move (CONVENTIONS.md)."""
    return (island.area < STACK_TINY_AREA or long_axis(island)[0] >= STACK_SPLIT_ASPECT
            or is_rectangle(island, scale))


# Strips: the thin rectangles (edge bands, rivet rows, trim) cut from the
# texture's trim areas. Learnt from the user's hand-sorted Final Applied file
# (2026-11-16): they first go onto the main islands where the texture matches;
# the rest go back where they were and stack onto each other, each onto the
# most alike longer strip (all metal with all metal, half dark with half dark).

STRIP_WIDTH = 0.02      # strips are at most this wide (fraction of the texture)
STRIP_FILL = 0.7        # and fill this much of their smallest rotated box,
STRIP_FILL_LONG = 0.5   # or this much when STRIP_ASPECT times longer than wide
STRIP_ASPECT = 3.0
STRIP_ON_MAIN = 0.9     # a strip this much inside other islands already lies on them
STRIP_WIDTH_SLACK = 1   # px a strip may be wider than the strip it stacks onto
STRIP_OVERHANG = 0.05   # share of a strip allowed to hang over the strip below


def min_rect(island):
    """(origin, long axis, short axis, length, width) of the island's smallest
    rotated bounding box, texture px."""
    p = sorted(set(map(tuple, np.round(island.verts, 4))))
    if len(p) < 3:
        return island.c, np.array([1.0, 0.0]), np.array([0.0, 1.0]), island.size, 1e-6

    def turn(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo, hi = [], []
    for q in p:
        while len(lo) >= 2 and turn(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(hi) >= 2 and turn(hi[-2], hi[-1], q) <= 0:
            hi.pop()
        hi.append(q)
    h = np.array(lo[:-1] + hi[:-1])
    best = None
    for i in range(len(h)):
        e = h[(i + 1) % len(h)] - h[i]
        n = np.linalg.norm(e)
        if n < 1e-9:
            continue
        u = e / n
        v = np.array([-u[1], u[0]])
        a, b = h @ u, h @ v
        if best is None or np.ptp(a) * np.ptp(b) < best[0]:
            best = (np.ptp(a) * np.ptp(b), u, v, a, b)
    _, u, v, a, b = best
    if np.ptp(a) < np.ptp(b):
        u, v, a, b = v, -u, b, -a
    return a.min() * u + b.min() * v, u, v, max(np.ptp(a), 1e-6), max(np.ptp(b), 1e-6)


class Strip:
    """A strip seen in its own box: texture colours on a 1 px grid along
    (s, long) and across (t, short) it, and which grid cells it covers."""

    def __init__(self, island, img, members=None):
        self.island = island
        self.members = members or [island]
        self.o, self.u, self.v, self.L, self.W = min_rect(island)
        self.F = np.stack([self.u, self.v])            # px offset -> (s, t)
        q = (island.tris - self.o) @ self.F.T
        nl, nw = int(np.ceil(self.L)), int(np.ceil(self.W))
        self.mask = raster(q, nw, nl).T                # [s, t]
        if not self.mask.any():
            self.mask = raster(q, nw, nl, edges=True).T
        s, t = np.meshgrid(np.arange(nl) + 0.5, np.arange(nw) + 0.5, indexing="ij")
        pts = self.o + s[..., None] * self.u + t[..., None] * self.v
        self.col = sample(img, pts.reshape(-1, 2)).reshape(nl, nw, 3)
        # Profile: mean colour of each row along the strip, and how many pixels it has.
        self.rows_n = self.mask.sum(axis=0).astype(float)
        self.rows = (self.col * self.mask[..., None]).sum(axis=0) / np.maximum(self.rows_n, 1)[:, None]
        self.area = self.mask.sum()

    def flipped(self):
        """Colours and mask turned 180 degrees in the strip's box."""
        return self.col[::-1, ::-1], self.mask[::-1, ::-1]


def strip_box(island, scale):
    """(fill of its smallest rotated box, length, width) in texture px, fill by covered pixels."""
    o, u, v, L, W = min_rect(island)
    g = 4.0 / max(min(W, L), 1.0) if W < 4 else 1.0  # draw thin strips finer
    q = (island.tris - o) @ np.stack([u, v]).T * g
    cover = raster(q, int(np.ceil(W * g)) + 1, int(np.ceil(L * g)) + 1).sum() / (g * g)
    return min(cover / (L * W), 1.0), L, W


def is_strip(island, scale):
    """Thin rectangle cut from the texture's trim (see STRIP_*)."""
    fill, L, W = strip_box(island, scale)
    if W > STRIP_WIDTH * np.sqrt(scale[0] * scale[1]):
        return False
    return fill >= STRIP_FILL or (L >= STRIP_ASPECT * W and fill >= STRIP_FILL_LONG)


def share_inside(island, mask):
    """Share of the island's pixels that lie inside the mask."""
    p = np.floor(pixels(island.tris)).astype(int)
    h, w = mask.shape
    ok = (p[:, 0] >= 0) & (p[:, 0] < w) & (p[:, 1] >= 0) & (p[:, 1] < h)
    return mask[p[ok, 1], p[ok, 0]].sum() / max(len(p), 1)


def profile_distance(a, b):
    """Smallest profile difference of strip a laid across strip b (any row
    offset, either way round), over their whole lengths."""
    wa, wb = len(a.rows), len(b.rows)
    best = np.inf
    for rows, n in ((a.rows, a.rows_n), (a.rows[::-1], a.rows_n[::-1])):
        for dt in range(0, max(wb - wa, 0) + 1):
            k = min(wa, wb - dt)
            if k <= 0 or not n[:k].sum():
                continue
            d = (n[:k, None] * (rows[:k] - b.rows[dt:dt + k]) ** 2).sum() / (n[:k].sum() * 3)
            best = min(best, d)
    return best


def fit_strip(a, b, max_error):
    """Best (error, flip, ds, dt) for strip a laid inside strip b, or None.
    error is the profile error: mean colour of each row along the strip,
    compared across its width, so strips group by what they show (all metal,
    half dark / half metal, a gold edge) rather than by every rivet. Among the
    offsets within max_error the one whose every pixel matches best wins."""
    la, wa = a.mask.shape
    lb, wb = b.mask.shape
    if la > lb or wa > wb + STRIP_WIDTH_SLACK:
        return None
    best = None
    bm = np.zeros((lb, max(wb, wa)))
    bm[:, :wb] = b.mask
    bc = np.zeros((lb, max(wb, wa), 3))
    bc[:, :wb] = b.col
    bsq = (bc ** 2).sum(axis=2)
    for flip in (False, True):
        col, mask = a.flipped() if flip else (a.col, a.mask)
        m = mask.astype(float)
        n = m.sum()
        if not n:
            return None
        asq = ((col ** 2).sum(axis=2) * m).sum()
        for dt in range(0, max(wb - wa, 0) + 1):
            # Per row t: 1-D correlations along s give every offset ds at once.
            k = lb - la + 1
            cross, bsum, out, prof = np.zeros(k), np.zeros(k), np.zeros(k), np.zeros(k)
            for t in range(wa):
                mt = m[:, t]
                nt = mt.sum()
                if not nt:
                    continue
                bsum += np.correlate(bsq[:, dt + t], mt, "valid")
                out += np.correlate(1.0 - bm[:, dt + t], mt, "valid")
                for c in range(3):
                    cross += np.correlate(bc[:, dt + t, c], mt * col[:, t, c], "valid")
                    mean_b = np.correlate(bc[:, dt + t, c], mt, "valid") / nt
                    prof += nt * ((mt * col[:, t, c]).sum() / nt - mean_b) ** 2
            err = (asq + bsum - 2 * cross) / (n * 3)
            prof /= n * 3
            ok = (out <= STRIP_OVERHANG * n) & (prof <= max_error)
            if not ok.any():
                continue
            i = int(np.argmin(np.where(ok, err, np.inf)))
            if best is None or err[i] < best[4]:
                best = (float(prof[i]), flip, i, dt, float(err[i]))
    return best and best[:4]


def move_strip(a, b, flip, ds, dt, scale):
    """Lay strip a (and the copies on it) inside strip b at offset (ds, dt)."""
    la, wa = a.mask.shape
    for island in a.members:
        st = (island.px - a.o) @ a.F.T
        if flip:
            st = np.array([la, wa]) - st
        st += (ds, dt)
        write_uvs(island, b.o + st @ b.F, scale)


def stack_strips(strips, img, max_error, scale, progress=None):
    """Stacks strips onto each other where they were: biggest first, each onto
    the most alike strip already kept that is at least as long, else it is
    kept itself. Returns (strips stacked, strips kept)."""
    strips = sorted(strips, key=lambda s: -s.area)
    hosts, stacked = [], 0
    for n, a in enumerate(strips):
        if progress:
            progress(n / max(len(strips), 1))
        # Cheap first look: the profiles over the whole length.
        cand = []
        for b in hosts:
            if b.mask.shape[0] < a.mask.shape[0] or b.mask.shape[1] + STRIP_WIDTH_SLACK < a.mask.shape[1]:
                continue
            d = profile_distance(a, b)
            if d <= 2 * max_error:
                cand.append((d, b))
        best = None
        for _, b in sorted(cand, key=lambda c: c[0])[:8]:
            hit = fit_strip(a, b, max_error)
            if hit and (best is None or hit[0] < best[0][0]):
                best = (hit, b)
        if best:
            (_, flip, ds, dt), b = best
            move_strip(a, b, flip, ds, dt, scale)
            stacked += len(a.members)
        else:
            hosts.append(a)
    return stacked, len(hosts)


def strip_keep(bms, img):
    """Faces of every island that is not a strip: what Stack Strips keeps."""
    scale = np.array(img.shape[1::-1], float)
    return {face for island in islands_of(bms, scale) if not is_strip(island, scale) for face in island.faces}


def optimise_uvs(bms, img, max_error, keep=None, halve=True, merge=True, split=True, force_move=True,
                 progress=None, strips=True):
    """All three passes on the islands of one texture ({object: bmesh} using it).
    keep: faces whose islands stay exactly as they are and are the only places
    others may be stacked onto (interactive). None: batch rules, everything
    under STACK_BIG_AREA and every thin strip is stacked onto the rest.
    strips: strips (is_strip) go whole onto the kept islands, else stack onto
    each other where they were (stack_strips) instead of being split or forced.
    Returns (stats dict, pieces left where they were)."""
    scale = np.array(img.shape[1::-1], float)

    def locked(island):
        return keep is not None and island.faces[0] in keep

    stats = dict(halved=0, merged=0, already=0, stacked=0, split=0, forced=0, movers=0, into_tile=0,
                 strips=0, strips_stacked=0, strips_kept=0)
    # The texture repeats, so islands shifted by whole UV tiles look the same:
    # bring them into 0-1, where the matching works.
    for island in islands_of(bms, scale):
        tile = np.floor(island.ac / scale)
        if tile.any() and not locked(island) and (np.floor(island.verts / scale) == tile).all():
            write_uvs(island, island.px - tile * scale, scale)
            stats["into_tile"] += 1
    if halve:
        for island in islands_of(bms, scale):
            if not locked(island):
                stats["halved"] += halve_symmetric(island, img, scale, max_error)
    on_locked = set()
    if merge:
        stats["merged"], stats["already"], on_locked = merge_duplicates(islands_of(bms, scale), img, scale,
                                                                        max_error, locked)

    islands = islands_of(bms, scale)
    if keep is None:
        # Thin strips never receive others, however big.
        movers = [i for i in islands if i.area < STACK_BIG_AREA or long_axis(i)[0] >= STACK_SPLIT_ASPECT]
        dests = [i for i in islands if i.area >= STACK_BIG_AREA and long_axis(i)[0] < STACK_SPLIT_ASPECT]
    else:
        movers = [i for i in islands if not locked(i) and i.faces[0] not in on_locked]
        dests = [i for i in islands if locked(i)]
    movers.sort(key=lambda i: -i.area)
    stats["movers"] = len(movers)
    if not movers or not dests:
        return stats, movers

    # Copies merged above lie on top of each other: they move together.
    groups = []
    for island in movers:
        for group in groups:
            rep = group[0][0]
            if np.linalg.norm(rep.ac - island.ac) <= 0.05 * rep.size and outline_match(rep, island, [np.eye(2)]):
                island.c = rep.c   # move rigidly with the group's first island
                group.append((island, np.eye(2)))
                break
        else:
            groups.append([(island, np.eye(2))])

    # Strips go whole onto the main islands, else onto each other where they
    # were; strips already lying on a main island stay.
    dest_mask = np.zeros(img.shape[:2], bool)
    for island in dests:
        dest_mask |= raster(island.tris, *img.shape[:2])
    strip_groups, others = [], []
    for group in groups:
        rep = group[0][0]
        if strips and is_strip(rep, scale):
            if share_inside(rep, dest_mask) < STRIP_ON_MAIN:
                strip_groups.append(group)
        else:
            others.append(group)
    stats["strips"] = sum(len(g) for g in strip_groups)
    if strip_groups:
        left_strips, n, _ = stack_islands(img, [], dests, max_error, False, None, strip_groups)
        stats["stacked"] += n
        rest = {face for island in left_strips for face in island.faces}
        stats["strips_stacked"], stats["strips_kept"] = stack_strips(
            [Strip(g[0][0], img, [i for i, _ in g]) for g in strip_groups if g[0][0].faces[0] in rest],
            img, max_error, scale)
    groups = others
    movers = [i for g in groups for i, _ in g]

    forced_faces = {face for island in movers if must_move(island, scale) for face in island.faces}
    left, stacked, stats["split"] = stack_islands(img, movers, dests, max_error, split, progress, groups)
    stats["stacked"] += stacked
    if force_move:
        # What is left of them (pieces cut from them, triangular ends included)
        # goes to its best spot, however different the texture there is.
        forced = [piece for piece in left if piece.faces[0] in forced_faces]
        if forced:
            left = [piece for piece in left if piece.faces[0] not in forced_faces]
            rest, _, _ = stack_islands(img, forced, dests, np.inf, True)
            stats["forced"] = len(forced) - len(rest)
            left += rest
    return stats, left


# Blender 5 keeps UV selection on loops and faces; 4.x keeps it in the UV layer.
UV_SELECT_ON_LOOPS = hasattr(bmesh.types.BMLoop, "uv_select_vert")


def visible_uv_islands(bm, uv_layer):
    """UV islands made only of the faces the UV editor shows: never hidden
    ones, and with UV sync off only faces selected in the mesh. Blender's
    bmesh_linked_uv_islands counts hidden faces too, so a hidden piece
    touching a visible island used to join it, move with it and throw off
    the fit (user, 2026-11-16)."""
    sync = bpy.context.scene.tool_settings.use_uv_select_sync
    shown = {face for face in bm.faces if not face.hide and (sync or face.select)}
    islands, seen = [], set()
    for seed in shown:
        if seed in seen:
            continue
        seen.add(seed)
        island, todo = [seed], [seed]
        while todo:
            face = todo.pop()
            for loop in face.loops:
                uv = loop[uv_layer].uv
                for other in loop.vert.link_loops:
                    f = other.face
                    if f in shown and f not in seen and (other[uv_layer].uv - uv).length_squared < 1e-14:
                        seen.add(f)
                        island.append(f)
                        todo.append(f)
        islands.append(island)
    return islands


def uv_selected(bm, island):
    if bpy.context.scene.tool_settings.use_uv_select_sync and not getattr(bm, "uv_select_sync_valid", False):
        return any(face.select for face in island.faces)
    if UV_SELECT_ON_LOOPS:
        return any(face.uv_select for face in island.faces) or any(loop.uv_select_vert for loop in island.loops)
    return any(loop[island.uv].select for loop in island.loops)


def set_uv_selected(faces, uv_layer, state):
    for face in faces:
        if UV_SELECT_ON_LOOPS:
            face.uv_select_set(state)
        for loop in face.loops:
            if UV_SELECT_ON_LOOPS:
                loop.uv_select_vert_set(state)
                loop.uv_select_edge_set(state)
            else:
                loop[uv_layer].select = state
                loop[uv_layer].select_edge = state


def uv_face_selected(bm, face, uv_layer):
    if bpy.context.scene.tool_settings.use_uv_select_sync and not getattr(bm, "uv_select_sync_valid", False):
        return face.select
    if UV_SELECT_ON_LOOPS:
        return face.uv_select
    return all(loop[uv_layer].select for loop in face.loops)


def uv_edge_selected(bm, loop, uv_layer):
    if bpy.context.scene.tool_settings.use_uv_select_sync and not getattr(bm, "uv_select_sync_valid", False):
        return loop.edge.select
    if UV_SELECT_ON_LOOPS:
        return loop.uv_select_edge
    return loop[uv_layer].select_edge


def snap_onto(new, keep, tol, fixed):
    """Moves each point (except `fixed`) within `tol` of the kept half onto it:
    onto its nearest vertex if one is that close, else onto its nearest edge.
    Returns how many points moved."""
    free = ~fixed
    verts = np.unique(keep.px, axis=0)   # exact, unlike keep.verts
    d = np.linalg.norm(new[:, None] - verts[None], axis=2)
    i = d.argmin(axis=1)
    on_vert = free & (d[np.arange(len(new)), i] <= tol)
    new[on_vert] = verts[i[on_vert]]
    rest = np.nonzero(free & ~on_vert)[0]
    if len(rest):
        a = keep.tris.reshape(-1, 2)
        b = keep.tris[:, [1, 2, 0]].reshape(-1, 2)
        ab = b - a
        p = new[rest][:, None]
        t = np.clip(((p - a) * ab).sum(axis=2) / np.maximum((ab * ab).sum(axis=1), 1e-18), 0, 1)
        q = a + t[..., None] * ab
        e = np.linalg.norm(p - q, axis=2)
        j = e.argmin(axis=1)
        close = e[np.arange(len(rest)), j] <= tol
        new[rest[close]] = q[np.arange(len(rest)), j][close]
        return int(on_vert.sum() + close.sum())
    return int(on_vert.sum())


def match_points(cost):
    """Hungarian method: for an n x m cost matrix (n <= m), the column for each
    row, all different, with the lowest total cost."""
    n, m = cost.shape
    u, v = np.zeros(n + 1), np.zeros(m + 1)
    p, way = np.zeros(m + 1, int), np.zeros(m + 1, int)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = np.full(m + 1, np.inf), np.zeros(m + 1, bool)
        while True:
            used[j0] = True
            free = ~used[1:]
            cur = cost[p[j0] - 1] - u[p[j0]] - v[1:]
            better = free & (cur < minv[1:])
            minv[1:][better] = cur[better]
            way[1:][better] = j0
            j1 = int(np.argmin(np.where(free, minv[1:], np.inf))) + 1
            delta = minv[j1]
            u[p[used]] += delta
            v[used] -= delta
            minv[~used] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    cols = np.zeros(n, int)
    for j in range(1, m + 1):
        if p[j]:
            cols[p[j] - 1] = j - 1
    return cols


def force_snap(new, mirrored, move, keep, fixed):
    """Puts every mirrored vertex (except `fixed`) onto a vertex of the kept
    half, each onto a different one where there are enough. First the mirrored
    half is turned and shifted (never scaled) to line up with the kept half,
    with the cut held in place. Returns how many vertices moved."""
    groups = {}
    for k, loop in enumerate(move.loops):
        if not fixed[k]:
            groups.setdefault(loop.vert, []).append(k)
    if not groups:
        return 0
    rows = list(groups.values())
    pts = np.array([new[r[0]] for r in rows])
    anchors, held = mirrored[fixed], move.px[fixed]
    verts = np.unique(keep.px, axis=0)
    # Line up (ICP): match to nearest kept vertices, best rigid fit, repeat.
    for _ in range(30):
        near = verts[np.linalg.norm(pts[:, None] - verts[None], axis=2).argmin(axis=1)]
        src, dst = np.concatenate([pts, anchors]), np.concatenate([near, held])
        cs, cd = src.mean(axis=0), dst.mean(axis=0)
        U, _, Vt = np.linalg.svd((src - cs).T @ (dst - cd))
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1] *= -1
            R = Vt.T @ U.T
        pts, anchors = (pts - cs) @ R.T + cd, (anchors - cs) @ R.T + cd
        if np.abs(R - np.eye(2)).max() < 1e-7 and np.abs(cd - cs).max() < 1e-9:
            break
    # Targets: kept vertices not already taken by the cut.
    targets = verts[np.linalg.norm(verts[:, None] - held[None], axis=2).min(axis=1) > 1e-9]         if len(held) else verts
    cost = ((pts[:, None] - targets[None]) ** 2).sum(axis=2)
    cols = match_points(cost) if len(pts) <= len(targets) else cost.argmin(axis=1)
    for r, j in zip(rows, cols):
        new[r] = targets[j]
    return len(rows)


def fold_island(faces, uv_layer, cut_loops, flip, snap_dist, keep_faces=None, force=False):
    """Cuts the island along the selected edges and mirrors one half onto the
    other across the line through them; the moved vertices then snap onto the
    kept half (with `force`, every one of them, see force_snap). Keeps
    `keep_faces` if given, else the bigger half (the smaller one if `flip`).
    Returns (vertices snapped, None) or (None, why not)."""
    cut_edges = {loop.edge for loop in cut_loops}
    if keep_faces is None and all(edge in cut_edges for face in faces for edge in face.edges):
        return None, "the whole island is selected; select only the edges to cut along"
    pts = np.array([loop[uv_layer].uv for loop in cut_loops] +
                   [loop.link_loop_next[uv_layer].uv for loop in cut_loops], float)
    c0 = pts.mean(axis=0)
    q = pts - c0
    if np.ptp(pts, axis=0).max() < 1e-6:
        return None, "the cut has no length"
    d = np.linalg.eigh(q.T @ q)[1][:, -1]   # the cut's direction
    n = np.array([-d[1], d[0]])

    # The halves: faces reachable from each other without crossing the cut.
    face_set, seen, halves = set(faces), set(), []
    if keep_faces is not None:
        halves = [list(keep_faces), [f for f in faces if f not in keep_faces]]
        seen = face_set
    for face in faces:
        if face in seen:
            continue
        seen.add(face)
        part, todo = [], [face]
        while todo:
            f = todo.pop()
            part.append(f)
            for edge in f.edges:
                if edge not in cut_edges:
                    for g in edge.link_faces:
                        if g in face_set and g not in seen:
                            seen.add(g)
                            todo.append(g)
        halves.append(part)
    if len(halves) != 2 and keep_faces is None:
        # The cut doesn't split the island in two: sort faces by side of the line.
        side = lambda f: np.mean([loop[uv_layer].uv for loop in f.loops], axis=0) @ n >= c0 @ n
        halves = [[f for f in faces if side(f)], [f for f in faces if not side(f)]]
        if not all(halves):
            return None, "all faces lie on one side of the cut"

    scale = np.ones(2)
    a, b = (StackIsland(None, half, uv_layer, scale) for half in halves)
    if keep_faces is not None:
        keep, move = a, b
    else:
        keep, move = (a, b) if (a.area >= b.area) != flip else (b, a)
    F = 2 * np.outer(d, d) - np.eye(2)
    mirrored = c0 + (move.px - c0) @ F
    new = mirrored.copy()
    # Vertices on the cut stay put, so both halves stay joined there.
    cut_verts = {v for edge in cut_edges for v in edge.verts}
    fixed = np.array([loop.vert in cut_verts for loop in move.loops])
    new[fixed] = move.px[fixed]
    if force:
        snapped = force_snap(new, mirrored, move, keep, fixed)
    else:
        size = max(np.ptp(np.concatenate([keep.verts, move.verts]), axis=0).max(), 1e-6)
        snapped = snap_onto(new, keep, snap_dist * size, fixed)
    write_uvs(move, new, scale)
    return snapped, None


def snap_island(mover, target, mirror, force, snap_dist):
    """Moves one island onto another: the best of the 4 rotations (and 4
    mirrors if `mirror`) by outline overlap, then its vertices snap onto the
    target's (with `force`, every one, see force_snap).
    Returns (vertices snapped, outline overlap)."""
    q = (mover.tris - mover.ac)
    best = None
    for R in (STACK_ORIENTS if mirror else STACK_ROTATIONS):
        iou, shift = outline_overlap(target.tris - target.ac, q @ R.T, STACK_MASK_PX / target.size)
        if best is None or iou > best[0]:
            best = (iou, R, shift)
    iou, R, shift = best
    new = target.ac + (mover.px - mover.ac) @ R.T + shift
    fixed = np.zeros(len(new), bool)
    if force:
        snapped = force_snap(new, new.copy(), mover, target, fixed)
    else:
        snapped = snap_onto(new, target, snap_dist * target.size, fixed)
    write_uvs(mover, new, np.ones(2))
    return snapped, iou


def texture_objects(context, name):
    """The image and the mesh objects in the view layer that use it."""
    image = bpy.data.images.get(name)
    layer = context.view_layer.objects
    return image, [obj for obj in meshes_by_image().get(image, []) if obj.name in layer]


def layer_collections(layer_collection):
    yield layer_collection
    for child in layer_collection.children:
        yield from layer_collections(child)


def layer_path(layer_collection, collection):
    """Layer collections from `layer_collection` down to the one holding `collection`."""
    if layer_collection.collection == collection:
        return [layer_collection]
    for child in layer_collection.children:
        path = layer_path(child, collection)
        if path:
            return [layer_collection] + path
    return []


def image_editors(context):
    """Image editor spaces in the current screen and the UV Editing workspace."""
    screens = [context.screen] if context.screen else []
    workspace = bpy.data.workspaces.get("UV Editing")
    if workspace is not None:
        screens += list(workspace.screens)
    for screen in dict.fromkeys(screens):
        for area in screen.areas:
            if area.type == "IMAGE_EDITOR":
                yield area.spaces.active


def leave_texture(context, stack):
    """Back to Object Mode, hiding again what was unhidden for the texture and
    unpinning the texture images it pinned."""
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    queue = set(stack.queue_list())
    for space in image_editors(context):
        if space.use_image_pin and space.image is not None and space.image.name in queue:
            space.use_image_pin = False
    for name in stack.unhidden.split("\n"):
        if name in context.view_layer.objects:
            context.view_layer.objects[name].hide_set(True)
    for name in stack.unhidden_collections.split("\n"):
        for layer_collection in layer_collections(context.view_layer.layer_collection):
            if layer_collection.name == name:
                layer_collection.hide_viewport = True
    for name in stack.hidden_others.split("\n"):
        if name in context.view_layer.objects:
            context.view_layer.objects[name].hide_set(False)
    stack.unhidden = stack.unhidden_collections = stack.hidden_others = ""


def open_texture(context, stack, name):
    """Every object using texture `name` in Edit Mode (hidden objects and
    collections unhidden for now), all faces selected so their UVs show, no UVs
    selected, the UV Editing workspace open and the texture pinned in its UV
    editor. False if none can be shown."""
    image, objects = texture_objects(context, name)
    hidden_collections = []
    for obj in objects:
        for collection in obj.users_collection:
            for layer_collection in layer_path(context.view_layer.layer_collection, collection):
                if layer_collection.hide_viewport:
                    layer_collection.hide_viewport = False
                    hidden_collections.append(layer_collection.name)
    hidden = [obj for obj in objects if obj.hide_get()]
    for obj in hidden:
        obj.hide_set(False)
    stack.unhidden = "\n".join(obj.name for obj in hidden)
    stack.unhidden_collections = "\n".join(hidden_collections)
    objects = [obj for obj in objects if obj.visible_get()]
    if not objects:
        return False
    if stack.hide_others:
        keep = set(objects)
        others = [obj for obj in context.view_layer.objects
                  if obj.type == "MESH" and obj not in keep and obj.visible_get()]
        for obj in others:
            obj.hide_set(True)
        stack.hidden_others = "\n".join(obj.name for obj in others)
    for obj in context.view_layer.objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    context.view_layer.objects.active = objects[0]
    bpy.ops.object.mode_set(mode="EDIT")
    context.scene.tool_settings.use_uv_select_sync = False
    for obj in objects:
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            face.select_set(True)
        if bm.loops.layers.uv.active is not None:
            set_uv_selected(bm.faces, bm.loops.layers.uv.active, False)
        bmesh.update_edit_mesh(obj.data)
    workspace = bpy.data.workspaces.get("UV Editing")
    if context.window is not None and workspace is not None:
        context.window.workspace = workspace
    for space in image_editors(context):
        space.image = image
        # Unpinned, Edit Mode swaps in the active object's image node instead.
        space.use_image_pin = True
    return True


def go_to_texture(context, stack, step):
    """Open texture number `step` of the queue, skipping ones whose objects
    can't be shown (disabled in viewports or in an excluded collection)."""
    queue = stack.queue_list()
    skipped = []
    leave_texture(context, stack)
    while step < len(queue) and not open_texture(context, stack, queue[step]):
        leave_texture(context, stack)
        skipped.append(queue[step])
        step += 1
    stack.step = step if step < len(queue) else -1
    stack.report = "Skipped (objects can't be shown): " + ", ".join(skipped) if skipped else ""


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Pre-rendered bake
# --------------------------------------------------------------------------

KEY_LIGHT = "Keyforce - Key Light"
SURROUND_LIGHT = "Keyforce - Surround Light"
NO_SHADOW = " (no shadow)"   # name ending of a sun's twin that casts no shadows
# Sun rotations (degrees): the eight suns of the user's rig in Black Numenor.blend
# (above, below and the four sides, two of the sides twice).
SURROUND_TURNS = ((-90.1, -0.2, 184.7), (-97.0, 2.6, 266.8), (-89.9, 200.1, -4.1), (3.1, 4.0, -15.1),
                  (-98.2, 0.4, 184.6), (-178.8, 1.4, 190.2), (-81.5, 199.3, -6.9), (-98.0, -2.3, 92.7))
FILL_NODE = "Keyforce Fill"
FILL_ADD = "Keyforce Fill Add"
FILL_DIM = "Keyforce World Dim"
# Size of the surround suns. The user's rig had 0.53 degrees; that small, glossy
# metal only caught them where the reflection angle happened to line up, which
# baked as blotches (chest_a, bracer_a). Engravings come from the normal map.
SURROUND_ANGLE = math.radians(4.0)
BAKE_MASK = 512        # UV islands are compared on a grid this many pixels across
BAKE_AWAY = 4.0        # UV shift that takes an island out of a bake
# An island with CONTAIN_SHARE of it inside one island at least CONTAIN_BIGGER
# times its size gives way to that island (bake_layers).
CONTAIN_SHARE, CONTAIN_BIGGER = 0.9, 1.05
# Biggest image one Cycles bake gets. Bigger textures are baked in chunks of
# this size (the UVs scaled up, one chunk in 0-1 at a time): Cycles' memory
# grows with the image, a 2048 bake in one go peaked at 4.7 GB of RAM.
BAKE_CHUNK = 1024
BAKE_UV = "Keyforce Bake"                   # UV map of the temporary joined copy
BAKE_TARGET_UV = "Keyforce Bake Target"     # its UV map the bake writes through
BAKE_PREVIEW = "Keyforce Bake (so far)"     # image shown in the image editors during a bake
METAL_OTHER_LIGHT = 0.3   # metal: share of the weaker light (suns or world) added to the brighter
WORLD_SATURATION = 0.5    # colour saturation of the world's light in a bake
WORLD_BLUR_SIZE = (64, 32)  # pixels of the blurred HDRI copy a bake is lit with
WORLD_GROUND_LIFT = 0.0  # share of the world turned upside down in a bake (lights faces turned down)
GLOSSY_FROM, GLOSSY_FULL = 0.28, 0.45   # spec gloss: non-metal on a metal object gets no / all of the suns
METAL_OBJECT = 0.1       # an object this metallic (mean of its metal map) gets the suns all over
OBJECT_ATTRIBUTE = "keyforce_object"   # face attribute: which object a face of the bake copy came from


def luminance(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def world_output(tree):
    out = next((n for n in tree.nodes if n.type == "OUTPUT_WORLD" and n.is_active_output), None)
    return out or tree.nodes.new("ShaderNodeOutputWorld")


def remove_bake_world(tree):
    """Takes the fill light nodes out of a world and links it up as before."""
    dim = tree.nodes.get(FILL_DIM)
    add = tree.nodes.get(FILL_ADD)
    first = dim.inputs[2] if dim is not None else add.inputs[0] if add is not None else None
    if first is not None and first.links:
        tree.links.new(first.links[0].from_socket, world_output(tree).inputs["Surface"])
    for node in (dim, add, tree.nodes.get(FILL_NODE)):
        if node is not None:
            tree.nodes.remove(node)


def mirror_world(tree):
    """Evens out the world's HDRI for a bake:
    - left/right symmetric: averaged with the image mirrored along X, so the
      left and right halves of a body (and mirrored parts) get the same light;
    - ground lifted: WORLD_GROUND_LIFT of it is the image upside down, so
      faces turned down (a shield's back in the import pose) see some sky
      instead of only the dark ground;
    - less colourful (WORLD_SATURATION).
    Returns what unmirror_world needs, or None when the world has no HDRI."""
    env = next((n for n in tree.nodes if n.type == "TEX_ENVIRONMENT" and n.image and n.outputs["Color"].links), None)
    if env is None:
        return None
    added = []
    if env.inputs["Vector"].links:
        vector = env.inputs["Vector"].links[0].from_socket
    else:
        coords = tree.nodes.new("ShaderNodeTexCoord")
        added.append(coords)
        vector = coords.outputs["Generated"]
    # Blurred: a tiny copy of the HDRI, smoothly interpolated. Glossy metal lit
    # by the world mirrored the image's detail (dark trees against bright sky)
    # as blotches; the overall light stays the same, the suns give the sharp
    # highlights.
    blurred = env.image.copy()
    blurred.name = env.image.name + " (bake blur)"
    blurred.scale(*WORLD_BLUR_SIZE)

    def copy(scale):
        flip = tree.nodes.new("ShaderNodeVectorMath")
        flip.operation = "MULTIPLY"
        flip.inputs[1].default_value = scale
        twin = tree.nodes.new("ShaderNodeTexEnvironment")
        twin.image, twin.interpolation, twin.projection = blurred, "Cubic", env.projection
        tree.links.new(vector, flip.inputs[0])
        tree.links.new(flip.outputs["Vector"], twin.inputs["Vector"])
        added.extend((flip, twin))
        return twin.outputs["Color"]

    def mix(a, b, factor):
        node = tree.nodes.new("ShaderNodeMix")
        node.data_type = "RGBA"
        node.inputs["Factor"].default_value = factor
        tree.links.new(a, node.inputs[6])
        tree.links.new(b, node.inputs[7])
        added.append(node)
        return node.outputs[2]

    targets = [link.to_socket for link in env.outputs["Color"].links]
    # Left/right only: front/back symmetric too was tried (2026-11-13) and
    # flattened cloth (hood spread 0.107 -> 0.088).
    upright = mix(copy((1.0, 1.0, 1.0)), copy((-1.0, 1.0, 1.0)), 0.5)
    if WORLD_GROUND_LIFT > 0.0:
        upside_down = mix(copy((1.0, 1.0, -1.0)), copy((-1.0, 1.0, -1.0)), 0.5)
        upright = mix(upright, upside_down, WORLD_GROUND_LIFT)
    # Half the colour: the sky's blue mirrored in glossy metal baked in as a
    # foggy blue haze, and cloth came out bluer than the user's bakes.
    grey = tree.nodes.new("ShaderNodeHueSaturation")
    grey.inputs["Saturation"].default_value = WORLD_SATURATION
    added.append(grey)
    tree.links.new(upright, grey.inputs["Color"])
    for socket in targets:
        tree.links.new(grey.outputs["Color"], socket)
    return env, targets, [node.name for node in added], blurred.name


def unmirror_world(tree, mirrored):
    if mirrored is None:
        return
    env, targets, names, blurred = mirrored
    for socket in targets:
        tree.links.new(env.outputs["Color"], socket)
    for name in names:
        node = tree.nodes.get(name)
        if node is not None:
            tree.nodes.remove(node)
    image = bpy.data.images.get(blurred)
    if image is not None:
        bpy.data.images.remove(image)


def bake_light_names():
    names = [KEY_LIGHT] + [f"{SURROUND_LIGHT} {index + 1}" for index in range(len(SURROUND_TURNS))]
    return names + [name + NO_SHADOW for name in names]


def setup_bake_light(scene, settings, preview=True):
    """Creates or updates the bake lighting: an even white fill light added to
    the world, and a sun (the key light). The viewport's Rendered mode shows it.
    Every sun has a twin without shadows. preview: the two share the light by
    the Shadows setting, so the viewport shows the suns' shadows as subtle as
    the bake makes them. The bake itself mixes two bakes, so it turns this off
    (twins dark)."""
    shadows = settings.bake_shadows if preview else 1.0

    def suns(name, energy):
        pair = []
        for suffix, share in (("", shadows), (NO_SHADOW, 1.0 - shadows)):
            light = bpy.data.objects.get(name + suffix)
            if light is None:
                light = bpy.data.objects.new(name + suffix, bpy.data.lights.new(name + suffix, "SUN"))
            if light.name not in scene.collection.all_objects:
                scene.collection.objects.link(light)
            light.data.energy = energy * share
            light.data.use_shadow = not suffix
            light.hide_render = False
            pair.append(light)
        return pair

    if scene.world is None:
        apply_world(settings)
    if scene.world is None:
        scene.world = bpy.data.worlds.new(WORLD_NAME)
    tree = node_tree_of(scene.world)
    fill = tree.nodes.get(FILL_NODE)
    if fill is not None and tree.nodes.get(FILL_DIM) is None:
        remove_bake_world(tree)   # set up by an older version
        fill = None
    if fill is None:
        out = world_output(tree)
        links = out.inputs["Surface"].links
        lit_by = links[0].from_socket if links else None
        fill = tree.nodes.new("ShaderNodeBackground")
        fill.name = fill.label = FILL_NODE
        fill.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        add = tree.nodes.new("ShaderNodeAddShader")
        add.name = add.label = FILL_ADD
        # Mixing with nothing dims the world: its bright and dark sides show
        # on metal as bright and dark patches.
        dim = tree.nodes.new("ShaderNodeMixShader")
        dim.name = dim.label = FILL_DIM
        fill.location = (out.location.x - 200, out.location.y - 160)
        add.location = (out.location.x, out.location.y - 160)
        dim.location = (out.location.x - 200, out.location.y - 320)
        tree.links.new(fill.outputs[0], add.inputs[1])
        if lit_by:
            tree.links.new(lit_by, dim.inputs[2])
        tree.links.new(dim.outputs[0], add.inputs[0])
        tree.links.new(add.outputs[0], out.inputs["Surface"])
    fill.inputs["Strength"].default_value = settings.bake_ambient
    tree.nodes[FILL_DIM].inputs[0].default_value = settings.bake_world
    key = suns(KEY_LIGHT, settings.bake_key)
    for sun in key:
        sun.data.angle = settings.bake_soft
        # A sun shines along its -Z: elevation 90 is straight down.
        sun.rotation_euler = (math.pi / 2 - settings.bake_elevation, 0.0, settings.bake_azimuth)
    # Surround lights: one sun from each of the six sides, as in the user's own
    # rig. They mostly light metals (reflections); surround_diffuse is how much
    # of them cloth and leather get.
    # Light Tilt turns the whole rig: around the vertical, then forwards. The
    # rig's suns line up with the body's axes, so broad plates facing one of
    # them were lit evenly and looked flat.
    tilt = (Euler((settings.bake_tilt * 0.5, 0.0, 0.0)).to_matrix()
            @ Euler((0.0, 0.0, settings.bake_tilt)).to_matrix())
    for index, turn in enumerate(SURROUND_TURNS):
        for light in suns(f"{SURROUND_LIGHT} {index + 1}", settings.bake_surround):
            light.rotation_euler = (tilt @ Euler([math.radians(angle) for angle in turn]).to_matrix()).to_euler()
            light.data.diffuse_factor = 1.0
            # Sharp, as in the user's rig: keeps engraved detail crisp on metal.
            light.data.angle = SURROUND_ANGLE
    return key[0]


def remove_bake_light(scene):
    for sun in [bpy.data.objects.get(name) for name in bake_light_names()]:
        if sun is None:
            continue
        data = sun.data
        bpy.data.objects.remove(sun, do_unlink=True)
        if data.users == 0:
            bpy.data.lights.remove(data)
    if scene.world and scene.world.node_tree:
        remove_bake_world(scene.world.node_tree)


def update_bake_light(self, context):
    """The lighting sliders move the lights while the lighting is set up."""
    if bpy.data.objects.get(KEY_LIGHT) is not None:
        setup_bake_light(context.scene, self)


def uv_islands(me, uv):
    """UV island number of every polygon: polygons are joined where they share
    a vertex at the same UV and face the same way in UV space. So an island
    folded onto itself counts as two (the folded half is mirrored), and its
    halves are handled like stacked islands instead of baking over each other."""
    count = len(me.polygons)
    totals = np.empty(count, np.int32)
    me.polygons.foreach_get("loop_total", totals)
    starts = np.empty(count, np.int32)
    me.polygons.foreach_get("loop_start", starts)
    verts = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", verts)
    loop_poly = np.repeat(np.arange(count), totals)
    # Signed UV area of every polygon: negative ones are mirrored.
    following = np.arange(len(verts)) + 1
    following[starts + totals - 1] = starts
    wide = uv.astype(np.float64)
    cross = wide[:, 0] * wide[following, 1] - wide[following, 0] * wide[:, 1]
    mirrored = np.add.reduceat(cross, starts) < 0
    key = np.column_stack((verts, np.round(uv * 1e5).astype(np.int64), mirrored[loop_poly]))
    corner = np.unique(key, axis=0, return_inverse=True)[1].ravel()
    parent = list(range(count))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first = {}
    for c, p in zip(corner.tolist(), loop_poly.tolist()):
        a = first.setdefault(c, p)
        if a != p:
            ra, rp = find(a), find(p)
            if ra != rp:
                parent[rp] = ra
    roots = np.array([find(i) for i in range(count)])
    return np.unique(roots, return_inverse=True)[1].ravel(), loop_poly


def island_mask(tris, grid=BAKE_MASK):
    """(y0, x0, mask) of triangles given in pixels of a grid x grid image: the
    pixels whose centre lies inside one of them."""
    lo = np.floor(tris.reshape(-1, 2).min(axis=0)).astype(int).clip(0, grid - 1)
    hi = np.ceil(tris.reshape(-1, 2).max(axis=0)).astype(int).clip(1, grid)
    mask = np.zeros((max(hi[1] - lo[1], 1), max(hi[0] - lo[0], 1)), bool)
    for (x0, y0), (x1, y1), (x2, y2) in tris:
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-9:
            continue
        ax = max(int(math.floor(min(x0, x1, x2))), lo[0])
        bx = min(int(math.ceil(max(x0, x1, x2))), hi[0])
        ay = max(int(math.floor(min(y0, y1, y2))), lo[1])
        by = min(int(math.ceil(max(y0, y1, y2))), hi[1])
        if bx <= ax or by <= ay:
            continue
        px = np.arange(ax, bx)[None, :] + 0.5 - x2
        py = np.arange(ay, by)[:, None] + 0.5 - y2
        a = ((y1 - y2) * px + (x2 - x1) * py) / den
        b = ((y2 - y0) * px + (x0 - x2) * py) / den
        mask[ay - lo[1]:by - lo[1], ax - lo[0]:bx - lo[0]] |= (a >= 0) & (b >= 0) & (a + b <= 1)
    return lo[1], lo[0], mask


def bake_layers(meshes, owners=None):
    """Sorts the UV islands of meshes sharing one texture into layers without
    overlaps. meshes: {mesh: UV array}; the arrays are changed: islands outside
    the 0-1 tile are moved in by whole units. Islands lying on texels a bigger
    island already has are left out (layer -1): they reuse its texels.
    owners: {mesh: object number of every polygon}. Then the islands of the
    object covering the most UV area claim their texels first, then the next
    object's, and so on: where variants of a part (different shapes on the
    same UVs) overlap, one object bakes the whole overlap, instead of texel by
    texel whichever island is bigger, which left seams across panels.
    Returns ({mesh: layer of every polygon}, layer count, islands left out)."""
    entries = []
    polygon_island = {}
    for me, uv in meshes.items():
        islands, loop_poly = uv_islands(me, uv)
        polygon_island[me] = islands
        loop_island = islands[loop_poly]
        me.calc_loop_triangles()
        tri_loops = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("loops", tri_loops)
        tri_loops = tri_loops.reshape(-1, 3)
        tri_island = loop_island[tri_loops[:, 0]]
        for island in range(islands.max() + 1):
            loops = loop_island == island
            points = uv[loops]
            # Whole units only: the texture repeats, so nothing changes on the model.
            uv[loops] -= np.floor((points.min(axis=0) + points.max(axis=0)) / 2)
            tris = uv[tri_loops[tri_island == island]].astype(np.float64) * BAKE_MASK
            y0, x0, mask = island_mask(tris)
            owner = 0
            if owners is not None and me in owners:
                owner = int(owners[me][np.argmax(islands == island)])
            entries.append((int(mask.sum()), me, island, y0, x0, mask, owner))
    # Coverage: the texels an object's islands cover together, each counted
    # once. Summing the islands let an object with many islands piled on the
    # same texels (helmet_a's lord_b: ~25 fan blades on one plate's UVs) rank
    # first, and its blades baked over the plate as streaks.
    union = {}
    for area, _, _, y0, x0, mask, owner in entries:
        grid = union.setdefault(owner, np.zeros((BAKE_MASK, BAKE_MASK), bool))
        grid[y0:y0 + mask.shape[0], x0:x0 + mask.shape[1]] |= mask
    coverage = {owner: int(grid.sum()) for owner, grid in union.items()}
    del union
    rank = {owner: index for index, owner in enumerate(sorted(coverage, key=lambda o: -coverage[o]))}
    # Contained islands give way: one lying almost wholly inside a clearly
    # bigger island (a variant's waistband inside another variant's skirt
    # panel) goes after every other island, so the panel bakes from one
    # piece instead of showing the small island's outline as a seam.
    label = np.full((BAKE_MASK, BAKE_MASK), -1, np.int32)
    areas = np.array([entry[0] for entry in entries])
    for index in np.argsort(-areas, kind="stable"):
        _, _, _, y0, x0, mask, _ = entries[index]
        window = label[y0:y0 + mask.shape[0], x0:x0 + mask.shape[1]]
        window[mask & (window < 0)] = index
    contained = set()
    for index, (area, _, _, y0, x0, mask, _) in enumerate(entries):
        if area == 0:
            continue
        under = label[y0:y0 + mask.shape[0], x0:x0 + mask.shape[1]][mask]
        under = under[(under >= 0) & (under != index)]
        if len(under) and (areas[under] >= CONTAIN_BIGGER * area).sum() >= CONTAIN_SHARE * area:
            contained.add(index)
    del label
    order = sorted(range(len(entries)), key=lambda i: (i in contained, rank[entries[i][6]], -entries[i][0]))
    entries = [entries[i] for i in order]
    covered = np.zeros((BAKE_MASK, BAKE_MASK), bool)
    layers = []
    layer_of = {}
    skipped = 0
    for area, me, island, y0, x0, mask, _ in entries:
        window = (slice(y0, y0 + mask.shape[0]), slice(x0, x0 + mask.shape[1]))
        if area == 0:
            # Smaller than a mask pixel: goes along with the first layer.
            layer_of[me, island] = 0
            continue
        if (mask & covered[window]).sum() >= 0.98 * area:
            layer_of[me, island] = -1
            skipped += 1
            continue
        # Layers are composited in order, the first to cover a texel keeps it:
        # an island goes after every layer holding an island placed before it
        # (which comes first by object and size) that it overlaps.
        overlaps = [(mask & layer[window]).sum() > max(2, 0.02 * area) for layer in layers]
        first = max((i + 1 for i, hit in enumerate(overlaps) if hit), default=0)
        for index in range(first, len(layers)):
            if not overlaps[index]:
                break
        else:
            index = len(layers)
            layers.append(np.zeros((BAKE_MASK, BAKE_MASK), bool))
        layers[index][window] |= mask
        covered[window] |= mask
        layer_of[me, island] = index
    polygon_layer = {me: np.array([layer_of[me, i] for i in range(islands.max() + 1)])[islands]
                     for me, islands in polygon_island.items()}
    return polygon_layer, max(len(layers), 1), skipped


def metal_object_mask(me, uv, metal, size):
    """(mask, every): mask is 1 on the texels of every object that is metal as
    a whole (its faces' metal map, averaged by UV area, at least
    METAL_OBJECT), else 0; every: all objects are. (size x
    size). me: the bake's joined copy, its faces tagged with OBJECT_ATTRIBUTE;
    uv: its UVs (one row per loop), metal: metal_map."""
    count = len(me.polygons)
    owner = np.zeros(count, np.int64)
    if me.attributes.get(OBJECT_ATTRIBUTE) is not None:
        values = np.empty(count, np.int32)
        me.attributes[OBJECT_ATTRIBUTE].data.foreach_get("value", values)
        owner = values.astype(np.int64)
    totals = np.empty(count, np.int32)
    me.polygons.foreach_get("loop_total", totals)
    starts = np.empty(count, np.int32)
    me.polygons.foreach_get("loop_start", starts)
    wide = uv.astype(np.float64)
    following = np.arange(len(wide)) + 1
    following[starts + totals - 1] = starts
    area = np.abs(np.add.reduceat(wide[:, 0] * wide[following, 1] - wide[following, 0] * wide[:, 1], starts))
    centre = np.add.reduceat(wide, starts) / totals[:, None]
    texel = np.clip((centre % 1.0 * size).astype(int), 0, size - 1)
    face_metal = metal[texel[:, 1], texel[:, 0]]
    me.calc_loop_triangles()
    tri_loops = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("loops", tri_loops)
    tri_face = np.empty(len(me.loop_triangles), np.int32)
    me.loop_triangles.foreach_get("polygon_index", tri_face)
    tri_loops = tri_loops.reshape(-1, 3)
    mask = np.zeros((size, size), bool)
    every = True
    for obj in np.unique(owner):
        faces = owner == obj
        if area[faces].sum() <= 0 or np.average(face_metal[faces], weights=area[faces]) < METAL_OBJECT:
            every = False
            continue
        tris = wide[tri_loops[faces[tri_face]]] * size
        for start in range(0, len(tris), 2000):   # in pieces: one mask per piece's bounding box
            y0, x0, piece = island_mask(tris[start:start + 2000], size)
            mask[y0:y0 + piece.shape[0], x0:x0 + piece.shape[1]] |= piece
    return mask.astype(np.float32), every


def spread_parts(me):
    """Moves every loose part of a mesh to its own place on a grid, so that in
    a bake each part is shadowed by itself only: plates lying over each other
    don't darken each other. Like Parts > Dedupe & Spread, but meant for the
    bake's temporary copy. Returns the number of parts."""
    count = len(me.vertices)
    edges = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", edges)
    parent = list(range(count))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in edges.reshape(-1, 2).tolist():
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    part = np.unique(np.array([find(i) for i in range(count)]), return_inverse=True)[1].ravel()
    parts = int(part.max()) + 1 if count else 0
    if parts < 2:
        return parts
    co = np.empty(count * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    low = np.full((parts, 3), np.inf)
    high = np.full((parts, 3), -np.inf)
    np.minimum.at(low, part, co)
    np.maximum.at(high, part, co)
    # Twice the biggest part apart: far enough to take no light from each other.
    cell = 2.0 * float((high - low).max())
    columns = math.ceil(math.sqrt(parts))
    index = np.arange(parts)
    place = np.column_stack((index % columns, index // columns, np.zeros(parts))) * cell
    co += (place - (low + high) / 2)[part].astype(np.float32)
    me.vertices.foreach_set("co", co.ravel())
    me.update()
    return parts


def metal_map(obj, size, spec_channel=None):
    """How metallic every texel is (0-1, size x size): what feeds the Metallic
    input of the object's material, the spec map's channel or a plain value.
    When Metallic is a plain 0 but the material has a Bannerlord spec map
    (<name>_s, R = metal) in an image node, that map's red channel is used:
    older imports, like the user's Black Numenor scene, don't wire it in.
    spec_channel: another channel of the same spec map instead (1 = gloss);
    0 everywhere when there is no spec map."""
    pick = 0 if spec_channel is None else spec_channel

    def channel_of(image, channel):
        w, h = image.size
        px = np.empty(w * h * 4, np.float32)
        image.pixels.foreach_get(px)
        values = px.reshape(h, w, 4)[:, :, channel]
        return values[np.arange(size) * h // size][:, np.arange(size) * w // size]

    for slot in obj.material_slots:
        material = slot.material
        if material is None or material.node_tree is None:
            continue
        shader = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if shader is None:
            continue
        socket = shader.inputs["Metallic"]
        if not socket.links:
            if socket.default_value == 0.0:
                for node in material.node_tree.nodes:
                    if node.type == "TEX_IMAGE" and node.image and node.image.filepath:
                        if Path(bpy.path.abspath(node.image.filepath)).stem.lower().endswith("_s"):
                            return channel_of(node.image, pick)
                # No spec map in the material: the <base>_s file beside the
                # colour texture <base>_d, as the Import section finds it.
                color = base_color_image(material)
                path = Path(bpy.path.abspath(color.filepath)) if color and color.filepath else None
                if path is not None and path.stem.lower().endswith("_d"):
                    spec = path.with_name(path.stem[:-2] + "_s" + path.suffix)
                    if spec.is_file():
                        image = bpy.data.images.load(str(spec), check_existing=True)
                        image.colorspace_settings.name = "Non-Color"
                        return channel_of(image, pick)
            value = socket.default_value if spec_channel is None else 0.0
            return np.full((size, size), value, np.float32)
        node, channel = socket.links[0].from_node, 0
        if node.type == "SEPARATE_COLOR":
            channel = ("Red", "Green", "Blue").index(socket.links[0].from_socket.name)
            node = node.inputs["Color"].links[0].from_node if node.inputs["Color"].links else None
        if node is not None and node.type == "TEX_IMAGE" and node.image:
            return channel_of(node.image, channel if spec_channel is None else spec_channel)
    return np.zeros((size, size), np.float32)


def save_baked(scene, image, path, alpha, view):
    """Saves a linear float image as an 8 bit PNG through the scene's color
    management, then puts the alpha in. view: with the scene's view transform
    and look (AgX in a new file), so highlights roll off softly; else plain
    sRGB."""
    look, fmt = scene.view_settings, scene.render.image_settings
    saved = (look.view_transform, look.look, look.exposure, look.gamma)
    saved_format = (fmt.file_format, fmt.color_mode, fmt.color_depth)
    try:
        if not view:
            look.view_transform = "Standard"
            look.look, look.exposure, look.gamma = "None", 0.0, 1.0
        fmt.file_format, fmt.color_mode, fmt.color_depth = "PNG", "RGBA", "8"
        image.save_render(str(path), scene=scene)
    finally:
        look.view_transform = saved[0]
        look.look, look.exposure, look.gamma = saved[1:]
        fmt.file_format, fmt.color_mode, fmt.color_depth = saved_format
    if alpha.min() < 1.0:
        written = bpy.data.images.load(str(path))
        px = np.empty(alpha.size * 4, np.float32)
        written.pixels.foreach_get(px)
        px.reshape(-1, 4)[:, 3] = alpha.ravel()
        written.pixels.foreach_set(px)
        written.save()
        bpy.data.images.remove(written)


def show_bake_preview(image, previous):
    """Shows image in every open image editor; previous remembers what each
    showed before ({space pointer: image name})."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "IMAGE_EDITOR":
                continue
            space = area.spaces.active
            if space.image != image:
                previous[space.as_pointer()] = space.image.name if space.image else ""
                space.image = image
            area.tag_redraw()


def hide_bake_preview(image, previous):
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "IMAGE_EDITOR" and area.spaces.active.image == image:
                space = area.spaces.active
                space.image = bpy.data.images.get(previous.get(space.as_pointer(), ""))


def use_gpu(context):
    """Turns on a GPU for Cycles if there is one: the device type already
    chosen in the preferences, else OptiX (RTX cards only), CUDA, HIP, oneAPI
    or Metal, the first that has a GPU. Returns what restore_gpu needs to put the
    preferences back, or None (no GPU: bake on the CPU)."""
    addon = context.preferences.addons.get("cycles")
    if addon is None or os.environ.get("KEYFORCE_CPU"):
        return None
    prefs = addon.preferences
    saved = (prefs.compute_device_type, {d.id: d.use for d in prefs.devices})
    kinds = [prefs.compute_device_type] if prefs.compute_device_type != "NONE" else []
    kinds += [k for k in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL") if k not in kinds]
    for kind in kinds:
        try:
            prefs.compute_device_type = kind
        except TypeError:   # not offered on this system
            continue
        prefs.get_devices_for_type(kind)
        gpus = [d for d in prefs.devices if d.type == kind]
        if kind == "OPTIX" and kind != saved[0] and not any("RTX" in d.name for d in gpus):
            # No RT cores (GTX cards): CUDA bakes faster there (GTX 1650:
            # 25 s instead of 30 s). OptiX only when chosen in the preferences.
            continue
        if gpus:
            for device in prefs.devices:
                device.use = device.type == kind
            return saved
    prefs.compute_device_type = saved[0]
    return None


def restore_gpu(context, saved):
    if saved is None:
        return
    prefs = context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = saved[0]
    for device in prefs.devices:
        if device.id in saved[1]:
            device.use = saved[1][device.id]


def bake_prerendered(*args, **kwargs):
    """bake_prerendered_steps run to the end; returns its results."""
    steps = bake_prerendered_steps(*args, **kwargs)
    while True:
        try:
            next(steps)
        except StopIteration as stop:
            return stop.value


def tint_reflections(tree):
    """For the bake only: non-metal reflections take the material's own hue
    and saturation at full brightness (Specular Tint = base colour with V = 1),
    metal keeps a white tint. White reflections of the world laid a grey veil
    over every colour: reds and browns lost 30-45% of their saturation and a
    dark brown plume baked light grey. Grey materials are unchanged (their
    tint is white, as before); the base colour itself (V below 1) as the tint
    darkened grey leather gloves by 25%. Returns the nodes added (removed
    after the bake, which also removes their links)."""
    added = []
    for shader in [n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"]:
        base, tint = shader.inputs["Base Color"], shader.inputs["Specular Tint"]
        if not base.links or tint.links:
            continue
        separate = tree.nodes.new("ShaderNodeSeparateColor")
        separate.mode = "HSV"
        combine = tree.nodes.new("ShaderNodeCombineColor")
        combine.mode = "HSV"
        combine.inputs[2].default_value = 1.0
        metal = tree.nodes.new("ShaderNodeMix")
        metal.data_type = "RGBA"
        metal.inputs["B"].default_value = (1.0, 1.0, 1.0, 1.0)
        tree.links.new(base.links[0].from_socket, separate.inputs["Color"])
        tree.links.new(separate.outputs[0], combine.inputs[0])
        tree.links.new(separate.outputs[1], combine.inputs[1])
        tree.links.new(combine.outputs[0], metal.inputs["A"])
        metallic = shader.inputs["Metallic"]
        if metallic.links:
            tree.links.new(metallic.links[0].from_socket, metal.inputs["Factor"])
        else:
            metal.inputs["Factor"].default_value = metallic.default_value
        tree.links.new(metal.outputs["Result"], tint)
        added += [separate, combine, metal]
    return added


def bake_prerendered_steps(context, objects, folder, size=2048, samples=32, margin=16, shadows=0.3, settings=None,
                           progress=print):
    """A generator: yields (fraction done, what comes next) before every Cycles
    bake, so a modal operator can show progress; closing it cleans up.

    Bakes the lit look of PBR objects (color, spec, normal, lighting) into one
    color texture per source color texture, on their own UVs:
    <folder>/<source texture name>.png.

    - Lighting: the world plus the fill and key light of setup_bake_light.
    - shadows: 0 bakes with no shadows at all, 1 with full shadows; in between
      the two are mixed, so shadows stay subtle. An object is only shadowed by
      itself, never by the other objects.
    - Stacked UV islands: each texel is baked from one island only, the biggest
      that covers it, so stacked islands can't overwrite each other in patches.
    Returns [(path, layers, islands left out)]."""
    settings = settings or context.scene.keyforce
    groups = {}
    # A fixed order: the objects are joined in it, and where UVs overlap (belts
    # wrapping the texture several times) it decides which part bakes a texel.
    # Import order changes from run to run, and so did the bake. Name order
    # gave props_a's belt the look the user picked (v1.13.0).
    for obj in sorted(objects, key=lambda o: o.name):
        if obj.type == "MESH" and obj.data.uv_layers and obj.data.polygons:
            image = base_color_image(obj.active_material)
            if image:
                groups.setdefault(image, {}).setdefault(obj.data, obj)
    if not groups:
        raise ValueError("Select meshes with a color texture first")
    if context.object and context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    scene = context.scene
    view_layer = context.view_layer
    for group in groups.values():
        for obj in group.values():
            if obj.name not in view_layer.objects or not obj.visible_get() or obj.hide_render:
                raise ValueError(f"{obj.name} is hidden or disabled for rendering: show it first")
    had_light = bpy.data.objects.get(KEY_LIGHT) is not None
    setup_bake_light(scene, settings, preview=False)
    mirrored = mirror_world(scene.world.node_tree)
    bake = scene.render.bake
    saved = (scene.render.engine, scene.cycles.samples, scene.cycles.device, bake.use_pass_direct,
             bake.use_pass_indirect, bake.margin, bake.use_clear, bake.use_selected_to_active, bake.target)
    visible_shadow = {o: o.visible_shadow for o in scene.objects}
    # Everything but the lights is hidden from the bake, not only the meshes
    # being baked: other objects (the rest of an outfit, around the body where
    # the bake copy lies) would still block bounce and reflection rays and bake
    # in as random dark patches.
    hidden = {o: o.hide_render for o in scene.objects if o.type != "LIGHT"}
    selection = [o for o in view_layer.objects if o.select_get()]
    active = view_layer.objects.active
    threads = (scene.render.threads_mode, scene.render.threads)
    denoise = (scene.cycles.use_denoising, scene.cycles.denoising_use_gpu)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    # Leave two CPU threads free, so the computer stays usable while baking.
    scene.render.threads_mode = "FIXED"
    scene.render.threads = max(1, (os.cpu_count() or 4) - 2)
    gpu = use_gpu(context)
    scene.cycles.device = "GPU" if gpu is not None else "CPU"
    # Cycles denoises every bake (on in new scenes). On the CPU that took 8 of
    # every 8.5 s and most of the memory; on the GPU it is the same denoiser.
    scene.cycles.use_denoising = settings.bake_denoise
    scene.cycles.denoising_use_gpu = gpu is not None
    bake.use_pass_direct = True
    bake.use_pass_indirect = settings.bake_indirect
    bake.margin = 0
    bake.use_clear = True
    bake.use_selected_to_active = False
    bake.target = "IMAGE_TEXTURES"
    folder.mkdir(parents=True, exist_ok=True)
    chunks = max(1, size // BAKE_CHUNK) if size % BAKE_CHUNK == 0 else 1
    tile = size // chunks
    px = np.empty(tile * tile * 4, np.float32)
    results = []
    temp_nodes = []
    temp_objects = []   # names: joining removes objects
    temp_meshes = []
    previous = {}
    # Live view in the image editors; a background Blender has none.
    preview = None if bpy.app.background else bpy.data.images.new(BAKE_PREVIEW, size, size, alpha=True,
                                                                   float_buffer=True)
    sun_energy = {light: bpy.data.objects[light].data.energy for light in bake_light_names()}
    fill = scene.world.node_tree.nodes[FILL_NODE]
    dim = scene.world.node_tree.nodes[FILL_DIM]
    target = None

    def joined_copy(group, name):
        """One temporary object holding copies of the group's meshes (modifiers
        applied), spread out in a row so that each is shadowed by itself only.
        Cycles bakes object by object, so one object is one bake instead of one
        per object, and the user's meshes are never touched."""
        depsgraph = context.evaluated_depsgraph_get()
        gap = 4.0 * max(max(obj.dimensions) for obj in group.values()) + 1.0
        copies = []
        for index, obj in enumerate(group.values()):
            me = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
            temp_meshes.append(me.name)
            uv_name = obj.data.uv_layers.active.name
            for other in [layer.name for layer in me.uv_layers if layer.name != uv_name]:
                me.uv_layers.remove(me.uv_layers[other])
            me.uv_layers[0].name = BAKE_UV
            me.uv_layers.active = me.uv_layers[0]
            # Which object each face came from survives the join below.
            owner = me.attributes.new(OBJECT_ATTRIBUTE, "INT", "FACE")
            owner.data.foreach_set("value", [index] * len(me.polygons))
            copy = bpy.data.objects.new(name + " (bake)", me)
            temp_objects.append(copy.name)
            scene.collection.objects.link(copy)
            matrix = obj.matrix_world.copy()
            matrix.translation.x += index * gap
            copy.matrix_world = matrix
            copies.append(copy)
        if len(copies) > 1:
            view_layer.update()
            with bpy.context.temp_override(active_object=copies[0], selected_editable_objects=copies):
                bpy.ops.object.join()
        # As the user did before baking: Dedupe (with the Parts section's
        # settings), then spread. Duplicate and variant parts stacked on the
        # same UVs otherwise bake as seams, dark spots and odd shadows.
        removed = dedupe_parts(copies[0], settings)
        progress(f"[Keyforce] {name}: {removed} duplicate parts left out")
        spread_parts(copies[0].data)
        return copies[0]

    def remove_temp():
        for name in temp_objects:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                bpy.data.objects.remove(obj, do_unlink=True)
        for name in temp_meshes:
            me = bpy.data.meshes.get(name)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
        temp_objects.clear()
        temp_meshes.clear()

    def run(joined, shadow, target):
        """One Cycles bake of the joined copy, with or without its own shadows."""
        for obj in scene.objects:
            obj.visible_shadow = shadow and obj == joined
        for obj in view_layer.objects:
            obj.select_set(obj == joined)
        view_layer.objects.active = joined
        bpy.ops.object.bake(type="COMBINED", uv_layer=BAKE_TARGET_UV)
        target.pixels.foreach_get(px)
        return px.reshape(tile, tile, 4).copy()

    try:
        for obj in hidden:
            obj.hide_render = True
        for group_index, (image, group) in enumerate(groups.items()):
            name = Path(bpy.path.abspath(image.filepath) if image.filepath else image.name).stem + ".png"
            yield group_index / len(groups), f"{name}: sorting UV islands"
            joined = joined_copy(group, name)
            me = joined.data
            # Float: the bake stays linear until it is saved through the color management.
            target = bpy.data.images.new(name + " (bake)", tile, tile, alpha=True, float_buffer=True)
            metal = metal_map(joined, size)
            # Cycles bakes into the active image node of each material.
            for material in {slot.material for slot in joined.material_slots if slot.material}:
                tree = material.node_tree
                temp_nodes.extend((tree, node) for node in tint_reflections(tree))
                node = tree.nodes.new("ShaderNodeTexImage")
                node.image = target
                tree.nodes.active = node
                temp_nodes.append((tree, node))
            uv = np.empty(len(me.loops) * 2, np.float32)
            me.uv_layers.active.data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
            # The bake writes through its own UV map (moved and scaled per layer
            # and chunk below); the textures are still read through the
            # original, which renders.
            me.uv_layers[0].active_render = True
            me.uv_layers.active = me.uv_layers.new(name=BAKE_TARGET_UV)
            owner = np.zeros(len(me.polygons), np.int32)
            if me.attributes.get(OBJECT_ATTRIBUTE) is not None:
                me.attributes[OBJECT_ATTRIBUTE].data.foreach_get("value", owner)
            polygon_layer, layer_count, skipped = bake_layers({me: uv}, {me: owner})
            # Suns by the metal map, and on the whole of every object that is
            # metal as a whole (wood, leather and trim on it too), as the user
            # lit only metal objects with the suns.
            weight = metal + (1.0 - metal) * settings.bake_surround_diffuse
            # Only glossy non-metal (trim, lacquered rims, polished leather):
            # matte cloth on an object that also holds chainmail stays unlit
            # by the suns, else half a panel got them and half didn't.
            gloss = metal_map(joined, size, spec_channel=1)
            glossy = np.clip((gloss - GLOSSY_FROM) / (GLOSSY_FULL - GLOSSY_FROM), 0.0, 1.0)
            # When every object on the texture is a metal object, nothing can
            # disagree, so matte parts (a shield's wooden back, facing down in
            # the import pose) get the suns too.
            objects_mask, every = metal_object_mask(me, uv, metal, size)
            weight = np.maximum(weight, objects_mask * (1.0 if every else glossy))
            # The pass without suns is always needed (metal takes the world from
            # it too); the suns pass only when something gets the suns.
            states = [True, False] if weight.max() > 0.02 else [False]
            totals = np.empty(len(me.polygons), np.int32)
            me.polygons.foreach_get("loop_total", totals)
            starts = np.empty(len(me.polygons), np.int32)
            me.polygons.foreach_get("loop_start", starts)
            face_lo = np.minimum.reduceat(uv, starts)
            face_hi = np.maximum.reduceat(uv, starts)
            result = np.zeros((size, size, 4), np.float32)
            filled = np.zeros((size, size), bool)
            for layer in range(layer_count):
                in_layer = polygon_layer[me] == layer
                if not in_layer.any():
                    continue
                away = np.repeat(~in_layer, totals)
                # Chunks this layer's faces reach; the others are not baked.
                todo = [(i, j) for j in range(chunks) for i in range(chunks)
                        if (in_layer & (face_hi[:, 0] > i / chunks) & (face_lo[:, 0] < (i + 1) / chunks)
                            & (face_hi[:, 1] > j / chunks) & (face_lo[:, 1] < (j + 1) / chunks)).any()]
                progress(f"[Keyforce] {name}: layer {layer + 1}/{layer_count}, {len(group)} objects")
                for chunk_index, (i, j) in enumerate(todo):
                    # This chunk of the texture fills the bake image: UVs scaled
                    # up and shifted so it lies in 0-1. Faces of other layers go
                    # far outside, where nothing is baked.
                    moved = uv * chunks - np.array((i, j), np.float32)
                    moved[away] += BAKE_AWAY * chunks
                    me.uv_layers.active.data.foreach_set("uv", moved.ravel())
                    me.update()
                    where = f"{name} ({group_index + 1}/{len(groups)}), layer {layer + 1}/{layer_count}"
                    if len(todo) > 1:
                        where += f", part {chunk_index + 1}/{len(todo)}"
                    done = layer + chunk_index / len(todo)
                    lit = {}
                    for index, suns in enumerate(states):
                        # Suns pass: every sun's light is split between it (with
                        # shadows) and its twin (without) by the Shadows setting.
                        # Light adds up, and the world is off in this pass, so one
                        # bake gives exactly the mix of a bake with and one without
                        # shadows: a Cycles bake less per layer.
                        for light, energy in sun_energy.items():
                            if not suns:
                                share = 0.0
                            elif light.endswith(NO_SHADOW):
                                share = 1.0 - shadows
                                energy = sun_energy[light[:-len(NO_SHADOW)]]
                            else:
                                share = shadows
                            bpy.data.objects[light].data.energy = energy * share
                        # The suns pass is the suns alone; the other pass is the world
                        # and the ambient fill. Metal takes the brighter of the two per
                        # texel (see below), cloth and leather the second.
                        fill.inputs["Strength"].default_value = 0.0 if suns else settings.bake_ambient
                        dim.inputs[0].default_value = 0.0 if suns else 1.0
                        yield ((group_index + (done + index / len(states) / len(todo)) / layer_count) / len(groups),
                               f"{where}: {'with' if suns else 'without'} suns")
                        if suns:
                            lit[suns] = run(joined, True, target)
                            continue
                        if shadows < 1.0:
                            lit[suns] = run(joined, False, target)
                        if shadows > 0.0:
                            shaded = run(joined, True, target)
                            if suns in lit:
                                both = (lit[suns][:, :, 3] > 0.5) & (shaded[:, :, 3] > 0.5)
                                lit[suns][both] = lit[suns][both] * (1.0 - shadows) + shaded[both] * shadows
                            else:
                                lit[suns] = shaded
                            del shaded
                    window = (slice(j * tile, (j + 1) * tile), slice(i * tile, (i + 1) * tile))
                    baked = lit.pop(False)
                    if len(states) == 2:
                        # Metal: the brighter of suns and world, plus a little of the
                        # other. Adding both washed out rough metal (sword blades) lit
                        # by the suns; the suns alone left glossy parts that catch no
                        # sun (sword guards) dark. Cloth and leather: the world only.
                        sun, world = lit.pop(True), baked
                        both = (sun[:, :, 3] > 0.5) & (world[:, :, 3] > 0.5)
                        a = sun[both][:, :3]
                        b = world[both][:, :3] * settings.bake_world
                        # A smooth pick (the stronger light's share rises steeply with
                        # its lead): a hard switch flipped neighbouring texels between
                        # two differently coloured lights and left blotches.
                        la, lb = luminance(a) ** 4, luminance(b) ** 4
                        pick = (la / np.maximum(la + lb, 1e-12))[:, None]
                        mixed = pick * (a + METAL_OTHER_LIGHT * b) + (1.0 - pick) * (b + METAL_OTHER_LIGHT * a)
                        share = weight[window][both][:, None]
                        baked[both, :3] = mixed * share + world[both][:, :3] * (1.0 - share)
                        del sun, a, b, la, lb, pick, mixed, share
                    new = (baked[:, :, 3] > 0.5) & ~filled[window]
                    result[window][new] = baked[new]
                    filled[window] |= new
                    del baked
                    if preview is not None:
                        # Live view: the texture so far, in every open image editor.
                        preview.pixels.foreach_set(result.ravel())
                        preview.update()
                        show_bake_preview(preview, previous)
            remove_temp()
            # Alpha stays the source texture's. Texels the source cuts out
            # (holes, torn edges) stay empty, as outside the UVs: only what
            # shows on the model is baked.
            w, h = image.size
            source = np.empty(w * h * 4, np.float32)
            image.pixels.foreach_get(source)
            source = source.reshape(h, w, 4)[np.arange(size) * h // size][:, np.arange(size) * w // size]
            alpha = source[:, :, 3]
            # Light floor: no texel darker than LIGHT_FLOOR of its own colour.
            # Faces no light reaches (the inside of a helmet shell) baked
            # black; now they are a dark version of their colour.
            if settings.bake_floor > 0.0:
                colour = source[:, :, :3].clip(0.0, 1.0)
                if not image.is_float and image.colorspace_settings.name == "sRGB":
                    colour = np.where(colour <= 0.04045, colour / 12.92, ((colour + 0.055) / 1.055) ** 2.4)
                lit = filled[:, :, None]
                result[:, :, :3] = np.where(lit, np.maximum(result[:, :, :3], colour * settings.bake_floor),
                                            result[:, :, :3])
                del colour, lit
            del source
            holes = alpha < 0.5
            result[holes] = 0.0
            filled &= ~holes
            # Margin: spread the texels outwards into the empty space.
            for _ in range(margin):
                total = np.zeros_like(result)
                count = np.zeros(filled.shape, np.float32)
                for axis, step in ((0, 1), (0, -1), (1, 1), (1, -1)):
                    moved = np.roll(filled, step, axis=axis)
                    count += moved
                    total += np.roll(result, step, axis=axis) * moved[:, :, None]
                near = (count > 0) & ~filled
                if not near.any():
                    break
                result[near] = total[near] / count[near][:, None]
                filled |= near
            result[:, :, 3] = 1.0
            bpy.data.images.remove(target)
            target = bpy.data.images.new(name + " (bake)", size, size, alpha=True, float_buffer=True)
            target.pixels.foreach_set(result.ravel())
            del result
            path = folder / name
            save_baked(scene, target, path, alpha, settings.bake_view)
            bpy.data.images.remove(target)
            target = None
            results.append((path, layer_count, skipped, image))
    finally:
        if target is not None:   # stopped half way
            bpy.data.images.remove(target)
        if preview is not None:
            hide_bake_preview(preview, previous)
            bpy.data.images.remove(preview)
        remove_temp()
        for tree, node in temp_nodes:
            tree.nodes.remove(node)
        for obj, state in visible_shadow.items():
            obj.visible_shadow = state
        for obj, state in hidden.items():
            obj.hide_render = state
        for obj in view_layer.objects:
            obj.select_set(obj in selection)
        view_layer.objects.active = active
        (scene.render.engine, scene.cycles.samples, scene.cycles.device, bake.use_pass_direct, bake.use_pass_indirect,
         bake.margin, bake.use_clear, bake.use_selected_to_active, bake.target) = saved
        scene.render.threads_mode, scene.render.threads = threads
        scene.cycles.use_denoising, scene.cycles.denoising_use_gpu = denoise
        restore_gpu(context, gpu)
        unmirror_world(scene.world.node_tree, mirrored)
        if had_light:
            setup_bake_light(scene, settings)
        else:
            remove_bake_light(scene)
    return results


def apply_baked(objects, results):
    """Gives the baked meshes a material with the baked color and the Medieval 2
    normal (<name>_m2_norm.dds beside the old _n map, else the old normal)."""
    for path, _, _, image in results:
        new = {}
        for obj in objects:
            if obj.type != "MESH":
                continue
            for slot, old in enumerate(obj.data.materials):
                if base_color_image(old) != image:
                    continue
                if old not in new:
                    normal = None
                    for node in old.node_tree.nodes:
                        if node.type == "NORMAL_MAP" and node.inputs["Color"].links:
                            source = node.inputs["Color"].links[0].from_node
                            while source.type != "TEX_IMAGE" and source.inputs and source.inputs["Color"].links:
                                source = source.inputs["Color"].links[0].from_node
                            if source.type == "TEX_IMAGE" and source.image:
                                normal = Path(bpy.path.abspath(source.image.filepath))
                    if normal is not None and normal.stem.lower().endswith("_n"):
                        m2 = normal.with_name(normal.stem[:-2] + "_m2_norm.dds")
                        normal = m2 if m2.is_file() else normal
                    new[old] = make_material(f"{path.stem} - Baked", path, None, normal)
                obj.data.materials[slot] = new[old]


_fbx_items_cache = {}


def fbx_items(self, context):
    """'All' plus every *_lod<N>.fbx under the folder, for the Object drop-down.
    Cached per folder and LOD: Blender calls this on every redraw, and also
    needs the list kept alive."""
    root = Path(bpy.path.abspath(self.folder)) if self.folder else None
    cache_key = (str(root), self.lod)
    if cache_key not in _fbx_items_cache:
        items = [("ALL", "All", "Import every FBX file under the folder")]
        if root is not None and root.is_dir():
            for fbx, *_ in discover(root, self.lod):
                relative = fbx.relative_to(root).as_posix()
                items.append((relative, fbx.stem, relative))
        _fbx_items_cache.clear()
        _fbx_items_cache[cache_key] = items
    return _fbx_items_cache[cache_key]


class KeyforceStackTexture(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    use: bpy.props.BoolProperty(name="Edit", default=True)
    count: bpy.props.IntProperty()


class KeyforceStackSettings(bpy.types.PropertyGroup):
    textures: bpy.props.CollectionProperty(type=KeyforceStackTexture)
    index: bpy.props.IntProperty()
    queue: bpy.props.StringProperty()                 # texture names, one per line
    step: bpy.props.IntProperty(default=-1)           # -1 = not running
    report: bpy.props.StringProperty()
    unhidden: bpy.props.StringProperty()              # objects to hide again, one per line
    unhidden_collections: bpy.props.StringProperty()  # collections to hide again, one per line
    hidden_others: bpy.props.StringProperty()         # objects to show again, one per line
    hide_others: bpy.props.BoolProperty(name="Hide Other Objects", default=True,
                                        description="While a texture is open, hide the mesh objects that don't "
                                                    "use it (shown again on the next texture or Stop)")
    max_error: bpy.props.FloatProperty(name="Max Error", default=0.01, min=0.0, max=0.2, precision=3,
                                       description="How different a spot may look and still be used "
                                                   "(mean squared colour difference; lower = stricter)")
    split: bpy.props.BoolProperty(name="Split Long Islands", default=True,
                                  description="Cut long thin islands that fit nowhere whole into pieces that do "
                                              "(adds UV seams, no new geometry)")
    halve: bpy.props.BoolProperty(name="Halve Symmetric Islands", default=True,
                                  description="An island that is its own mirror image across a line through its "
                                              "middle: keep the brighter half and mirror the other half onto it")
    merge: bpy.props.BoolProperty(name="Merge Duplicates", default=True,
                                  description="Stack near-duplicate copies (any rotation, mirrored too) onto the copy "
                                              "whose texture fits the others best, snapping close vertices")
    force_move: bpy.props.BoolProperty(name="Always Move Strips & Tiny Islands", default=True,
                                       description="Rectangles, thin strips (4:1 or longer) and tiny islands with no "
                                                   "matching spot still go to the best one there is")

    def queue_list(self):
        return [name for name in self.queue.split("\n") if name]


class KeyforceSettings(bpy.types.PropertyGroup):
    folder: bpy.props.StringProperty(name="Folder", subtype="DIR_PATH",
                                     description="Folder searched (with sub folders) for the FBX files")
    lod: bpy.props.IntProperty(name="LOD", default=0, min=0, max=9,
                               description="Imports the *_lod<N>.fbx files")
    target: bpy.props.EnumProperty(name="Object", items=fbx_items,
                                   description="Import every FBX file, or just one of them")
    world: bpy.props.EnumProperty(name="World", items=[
        ("PREVIEW", "Match Material Preview", "The viewport's Material Preview HDRI, rotation and strength"),
    ] + [(name.upper(), name.title(), f"Blender's built-in {name}.exr studio light") for name in BUILTIN_HDRIS],
        default="PREVIEW")
    show_hdri: bpy.props.BoolProperty(name="Show HDRI in Background", default=False,
                                      description="Off: the HDRI only lights the scene and the camera sees dark grey")
    world_on_import: bpy.props.BoolProperty(name="Set World on Import", default=True)
    use_baked: bpy.props.BoolProperty(name="Use Baked Textures", default=False,
                                      description="Color from the baked texture folder (<name>.png) and the "
                                                  "Medieval 2 *_m2_norm.dds beside each FBX as the normal, "
                                                  "instead of the original _d, _s and _n maps")
    baked_folder: bpy.props.StringProperty(name="Baked", subtype="DIR_PATH",
                                           description="Folder with the baked color textures, "
                                                       "e.g. New Textures\\Enhanced_Detail_v2")
    rename: bpy.props.BoolProperty(name="Clean Up Names", default=True,
                                   description="sm_md_num_barding_elite_a.1 -> barding_elite_a: drop the mesh type, "
                                               "faction code and the .lod2 / .1 suffixes")
    static: bpy.props.BoolProperty(name="Remove Armatures and Nodes", default=False,
                                   description="Delete the armatures, armature modifiers and empty nodes on import, "
                                               "leaving static meshes in place")
    gap: bpy.props.FloatProperty(name="Gap", default=1.0, min=0.0, subtype="DISTANCE",
                                 description="Space between the parts after spreading")
    match: bpy.props.EnumProperty(name="Match", default="UV", items=[
        ("UV", "Vertex Count + UVs", "Same vertex and face count and the same UVs, wherever the parts are"),
        ("SHAPE", "Same Shape + UVs", "Same shape and UVs, wherever the parts are"),
        ("EXACT", "Exact (Position + UVs)", "Only parts lying exactly on top of each other with the same UVs"),
    ])
    precision: bpy.props.IntProperty(name="Precision", default=3, min=1, max=8,
                                     description="Decimal places compared for UVs (and positions)")
    tolerance: bpy.props.FloatProperty(name="Tolerance", default=10.0, min=0.0, max=50.0, subtype="PERCENTAGE",
                                       description="Vertex Count + UVs: parts still match when their vertex and "
                                                   "face counts and UV layouts differ by up to this much "
                                                   "(e.g. mirrored parts). 0 = exact counts and UVs")
    into_tile: bpy.props.BoolProperty(name="Move UVs into 0-1", default=True,
                                      description="Move every UV island by whole units into the 0-1 UV space "
                                                  "(before deduping). Islands crossing a tile border are reported")
    select_inner: bpy.props.BoolProperty(name="Select Inner UV Islands", default=True,
                                         description="Afterwards: open UV Editing with UV Sync Selection and select "
                                                     "the UV islands lying inside a bigger island")
    bake_folder: bpy.props.StringProperty(name="Folder", subtype="DIR_PATH", default="//Pre-rendered",
                                          description="Where the pre-rendered color textures are written, "
                                                      "one <source texture name>.png per texture")
    bake_size: bpy.props.EnumProperty(name="Size", default="2048",
                                      items=[(s, f"{s} x {s}", "") for s in ("512", "1024", "2048", "4096")])
    bake_samples: bpy.props.IntProperty(name="Samples", default=32, min=1, max=4096)
    bake_margin: bpy.props.IntProperty(name="Margin", default=0, min=0, max=64, subtype="PIXEL",
                                       description="Pixels the baked colour is spread out past the UV islands' "
                                                   "edges. 0 bakes the exact UVs and leaves the rest empty")
    bake_denoise: bpy.props.BoolProperty(name="Denoise", default=True,
                                         description="Smooth out the sampling noise (on the GPU when there is one). "
                                                     "Off bakes about twice as fast, a little grainier")
    bake_indirect: bpy.props.BoolProperty(name="Bounce Light", default=True,
                                          description="Also bake light bounced off the part itself, as a plain "
                                                      "Cycles bake does. It fills recesses with soft light")
    bake_view: bpy.props.BoolProperty(name="Scene Color Management", default=True,
                                      description="Save the textures with the scene's view transform and look "
                                                  "(Render properties > Color Management; AgX in a new file): "
                                                  "bright highlights roll off instead of clipping to white. Off "
                                                  "saves plain sRGB")
    bake_ambient: bpy.props.FloatProperty(name="Ambient", default=0.05, min=0.0, max=5.0, update=update_bake_light,
                                          description="Even white light from every direction added to the world's, "
                                                      "so faces turned away from the light are not baked black. "
                                                      "On metal it counts as part of the world's light")
    bake_world: bpy.props.FloatProperty(name="World", default=0.6, min=0.0, max=1.0, subtype="FACTOR",
                                        update=update_bake_light,
                                        description="Strength of the world's light (with Ambient) on metal in the "
                                                    "bake. Metal takes the brighter of the suns and the world, texel "
                                                    "by texel, plus a little of the other. Leather and cloth always "
                                                    "get the full world")
    bake_key: bpy.props.FloatProperty(name="Key Light", default=0.0, min=0.0, max=20.0, update=update_bake_light,
                                      description="Strength of the key light (a sun). 0 leaves the lighting to "
                                                  "the world (World panel) and the ambient light")
    bake_surround: bpy.props.FloatProperty(name="Surround Lights", default=1.0, min=0.0, max=20.0,
                                           update=update_bake_light,
                                           description="Strength of eight sharp suns shining from above, below and "
                                                       "the four sides. They make metal look like metal")
    bake_surround_diffuse: bpy.props.FloatProperty(name="Suns on Cloth & Leather", default=0.0, min=0.0, max=1.0,
                                                   subtype="FACTOR",
                                                   description="How much of the suns (surround and key) non-metal "
                                                               "surfaces get. Metal always gets them in full; what "
                                                               "is metal is read from the spec map, texel by texel. "
                                                               "0 keeps leather and cloth from washing out. The "
                                                               "viewport preview shows the suns on everything")
    bake_azimuth: bpy.props.FloatProperty(name="Direction", default=math.radians(30), min=-math.pi, max=math.pi,
                                          subtype="ANGLE", update=update_bake_light,
                                          description="Turns the key light around the model")
    bake_elevation: bpy.props.FloatProperty(name="Height", default=math.radians(50), min=math.radians(-90),
                                            max=math.radians(90), subtype="ANGLE", update=update_bake_light,
                                            description="Height of the key light: 90 is straight above")
    bake_soft: bpy.props.FloatProperty(name="Softness", default=math.radians(40), min=0.0, max=math.pi,
                                       subtype="ANGLE", update=update_bake_light,
                                       description="Size of the key light: bigger gives softer shadow edges")
    bake_tilt: bpy.props.FloatProperty(name="Light Tilt", default=math.radians(15), min=math.radians(-45), max=math.radians(45),
                                       subtype="ANGLE", update=update_bake_light,
                                       description="Turns all the surround suns off the body's axes, so broad plates "
                                                   "get a gradient instead of even light")
    bake_floor: bpy.props.FloatProperty(name="Light Floor", default=0.2, min=0.0, max=1.0, subtype="FACTOR",
                                        description="No texel bakes darker than this share of its own colour: "
                                                    "faces no light reaches (inside a helmet) become dark, not black")
    bake_shadows: bpy.props.FloatProperty(name="Shadows", default=1.0, min=0.0, max=1.0, subtype="FACTOR",
                                          update=update_bake_light,
                                          description="0 bakes no shadows at all, 1 full shadows. In between the "
                                                      "two are mixed (the bake takes longer than with 0). "
                                                      "The viewport shows the mix for the key and surround lights; "
                                                      "shading from the world and ambient light shows in full")
    bake_progress: bpy.props.FloatProperty(default=-1.0, options={"SKIP_SAVE"})   # below 0: no bake running
    bake_status: bpy.props.StringProperty(options={"SKIP_SAVE"})
    bake_apply: bpy.props.BoolProperty(name="Use Baked Textures", default=True,
                                       description="Afterwards give the meshes a material with the baked color and "
                                                   "the Medieval 2 *_m2_norm.dds normal (else the old normal)")
    auto_source: bpy.props.EnumProperty(name="Bake", default="SELECTED", items=[
        ("SELECTED", "Selected Meshes", "Bake the selected meshes"),
        ("SCENE", "All Meshes in the Scene", "Bake every visible mesh with a color texture"),
        ("IMPORT", "Import, Then Bake", "Import with the Import section's settings, then bake what was imported"),
    ])
    auto_background: bpy.props.BoolProperty(name="In Background", default=True,
                                            description="Bake in a separate, hidden Blender at low priority, so "
                                                        "you can keep working. Off: bake here (Esc stops it)")
    stack: bpy.props.PointerProperty(type=KeyforceStackSettings)


# Settings Automatic Bake takes at their defaults, whatever Manual Bake's are
# set to: lighting, bake quality and the Dedupe & Spread matching the bake
# runs on its copy.
RECOMMENDED_KEYS = ("world", "bake_samples", "bake_margin", "bake_denoise", "bake_indirect", "bake_view",
                    "bake_ambient", "bake_world", "bake_key", "bake_surround", "bake_surround_diffuse",
                    "bake_azimuth", "bake_elevation", "bake_soft", "bake_shadows", "bake_tilt", "bake_floor",
                    "match", "precision", "tolerance", "into_tile")
LIGHTING_KEYS = ("world", "bake_ambient", "bake_world", "bake_key", "bake_surround", "bake_surround_diffuse",
                 "bake_azimuth", "bake_elevation", "bake_soft", "bake_shadows", "bake_tilt", "bake_floor")


def recommended_settings(settings):
    """A stand-in for settings with RECOMMENDED_KEYS at their defaults; the
    scene's own settings stay as they are."""
    from types import SimpleNamespace
    values = {p.identifier: getattr(settings, p.identifier) for p in settings.bl_rna.properties
              if p.identifier != "rna_type"}
    for key in RECOMMENDED_KEYS:
        values[key] = settings.bl_rna.properties[key].default
    return SimpleNamespace(**values)


def apply_world(settings):
    choice = "PREVIEW" if settings.world == "PREVIEW" else settings.world.lower()
    return set_world(choice, settings.show_hdri)


class KEYFORCE_OT_import(bpy.types.Operator):
    bl_idname = "keyforce.import_folder"
    bl_label = "Import"
    bl_description = "Import every *_lod<N>.fbx under the folder, or the chosen one, with its _d, _s and _n textures"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.keyforce
        root = Path(bpy.path.abspath(settings.folder))
        if not settings.folder or not root.is_dir():
            self.report({"ERROR"}, "Choose an existing folder first")
            return {"CANCELLED"}
        only = None if settings.target in ("ALL", "") else root / settings.target
        baked = None
        if settings.use_baked:
            baked = Path(bpy.path.abspath(settings.baked_folder))
            if not settings.baked_folder or not baked.is_dir():
                self.report({"ERROR"}, "Choose an existing baked texture folder first")
                return {"CANCELLED"}
        try:
            files, meshes, missing = import_folder(root, settings.lod, self.report, settings.static, only, baked,
                                                   settings.rename)
        except Exception as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if settings.world_on_import:
            apply_world(settings)
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    shading = area.spaces.active.shading
                    if baked:
                        # Baked color already holds the lighting: show it unlit.
                        shading.type = "SOLID"
                        shading.light = "FLAT"
                        shading.color_type = "TEXTURE"
                    else:
                        shading.type = "MATERIAL"
        self.report({"INFO"}, f"Imported {files} FBX files, {meshes} meshes"
                    + (f", {missing} missing textures (see Info log)" if missing else ""))
        return {"FINISHED"}


class KEYFORCE_OT_world(bpy.types.Operator):
    bl_idname = "keyforce.set_world"
    bl_label = "Apply World"
    bl_description = "Set the scene world to the chosen lighting"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            name = apply_world(context.scene.keyforce)
        except Exception as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, f"World lit by {name}")
        return {"FINISHED"}


class KEYFORCE_OT_dedupe_spread(bpy.types.Operator):
    bl_idname = "keyforce.dedupe_spread_parts"
    bl_label = "Dedupe & Spread Parts"
    bl_description = ("On the selected meshes: move UV islands into 0-1, delete loose parts that duplicate another part, lay the rest out "
                      "in a grid, then select the UV islands lying inside bigger ones in UV Editing")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(obj.type == "MESH" for obj in context.selected_objects)

    def execute(self, context):
        settings = context.scene.keyforce
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
        removed, spread, crossing = dedupe_and_spread(objects, settings.gap, settings.match, settings.precision,
                                                      settings.tolerance / 100.0, settings.into_tile)
        message = f"Removed {removed} duplicate parts, spread {spread} parts {settings.gap:g} apart"
        if crossing:
            # Each mesh on its own line in the Info editor; the summary in the status bar.
            for name, count in sorted(crossing.items()):
                self.report({"WARNING"}, f"{name}: {count} UV island{'s' if count > 1 else ''} "
                                         "cross a UV tile border and weren't moved into 0-1")
            message += (f", {sum(crossing.values())} UV islands on {len(crossing)} meshes cross a tile border "
                        "(not moved, see Info editor)")
        if settings.select_inner:
            message += ", " + self.select_inner_islands(context, objects)
        self.report({"INFO"}, message)
        return {"FINISHED"}

    @staticmethod
    def select_inner_islands(context, objects):
        # "Clearly smaller": under 95% of the bigger island's UV area, so two
        # islands stacked exactly on top of each other aren't picked.
        found = find_inner_islands(objects, smaller=0.95)
        if not found:
            return "no UV islands inside bigger ones"
        for obj in objects:
            select_faces(obj, found.get(obj, []))
        if context.view_layer.objects.active not in objects:
            context.view_layer.objects.active = next(iter(found))
        tool_settings = context.scene.tool_settings
        tool_settings.use_uv_select_sync = True
        tool_settings.mesh_select_mode = (False, False, True)
        bpy.ops.object.mode_set(mode="EDIT")
        workspace = bpy.data.workspaces.get("UV Editing")
        if context.window is not None and workspace is not None:
            context.window.workspace = workspace
        faces = sum(len(f) for f in found.values())
        return (f"selected {faces} faces of UV islands inside bigger ones on {len(found)} meshes "
                + ("(UV Editing, UV Sync Selection on)" if workspace else "(no UV Editing workspace: open a UV Editor)"))


def bake_folder_path(settings):
    """The absolute bake folder, or None. "//" means beside the .blend, which
    an unsaved file doesn't have: then the import folder is used."""
    folder = Path(bpy.path.abspath(settings.bake_folder))
    if folder.is_absolute():
        return folder
    root = Path(bpy.path.abspath(settings.folder)) if settings.folder else None
    if root is None or not root.is_absolute() or not root.is_dir():
        return None
    return root / (settings.bake_folder.strip("/\\") or "Pre-rendered")


# --------------------------------------------------------------------------
# Bake in background: a separate, hidden Blender bakes a copy of the scene
# --------------------------------------------------------------------------

BACKGROUND = {}   # the running background bake: process, job folder, objects
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
CREATE_NO_WINDOW = 0x08000000


def run_background_job(job_path):
    """Runs in the background Blender (started by KEYFORCE_OT_bake_background):
    bakes the job's objects in the saved copy of the scene and writes progress
    and results next to the job file."""
    import json
    job = json.loads(Path(job_path).read_text())
    folder = Path(job_path).parent

    def write(name, data):
        temp = folder / (name + ".tmp")
        temp.write_text(json.dumps(data))
        temp.replace(folder / name)

    try:
        register()
        context = bpy.context
        objects = [bpy.data.objects[name] for name in job["objects"] if name in bpy.data.objects]
        for obj in context.view_layer.objects:
            obj.select_set(obj in objects)
        settings = context.scene.keyforce
        if job.get("recommended"):
            settings = recommended_settings(settings)
        steps = bake_prerendered_steps(context, objects, Path(job["folder"]), job["size"], settings.bake_samples,
                                       settings.bake_margin, settings.bake_shadows, settings, progress=print)
        while True:
            try:
                fraction, status = next(steps)
            except StopIteration as stop:
                results = stop.value
                break
            write("progress.json", {"fraction": fraction, "status": status})
        write("result.json", {"results": [[str(path), layers, skipped, image.name]
                                          for path, layers, skipped, image in results]})
    except Exception as error:
        import traceback
        traceback.print_exc()
        write("result.json", {"error": str(error)})


def poll_background_bake():
    """Timer: shows the background bake's progress in the panel, and applies
    its textures when it is done. Returns seconds to the next poll, or None."""
    import json
    if not BACKGROUND:
        return None
    scene = bpy.data.scenes.get(BACKGROUND["scene"])
    settings = scene.keyforce if scene else None
    folder = BACKGROUND["folder"]
    process = BACKGROUND["process"]
    try:
        progress = json.loads((folder / "progress.json").read_text())
        if settings is not None:
            settings.bake_progress = progress["fraction"]
            settings.bake_status = "In background: " + progress["status"]
    except (OSError, ValueError, KeyError):
        pass
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    if process.poll() is None:
        return 1.0
    result = {}
    try:
        result = json.loads((folder / "result.json").read_text())
    except (OSError, ValueError):
        result = {"error": f"the background Blender stopped (exit code {process.returncode}); "
                           f"see {folder / 'log.txt'}"}
    objects = [bpy.data.objects[name] for name in BACKGROUND["objects"] if name in bpy.data.objects]
    BACKGROUND.clear()
    if settings is not None:
        settings.bake_progress = -1.0
        settings.bake_status = ""
    if "error" in result:
        message = "Background bake failed: " + result["error"]
    else:
        results = []
        for path, layers, skipped, image_name in result["results"]:
            path = Path(path)
            for image in bpy.data.images:   # an earlier bake of it, already loaded
                if image.filepath and Path(bpy.path.abspath(image.filepath)) == path:
                    image.reload()
            image = bpy.data.images.get(image_name)
            if image is not None:
                results.append((path, layers, skipped, image))
        if settings is not None and settings.bake_apply and results:
            apply_baked(objects, results)
        message = f"Background bake done: {len(result['results'])} textures"
        if result["results"]:
            message += f" in {Path(result['results'][0][0]).parent}"
        import shutil
        shutil.rmtree(folder, ignore_errors=True)
    print("[Keyforce]", message)
    if not bpy.app.background and bpy.context.window_manager.windows:   # a popup needs a window
        bpy.context.window_manager.popup_menu(lambda menu, _: menu.layout.label(text=message), title="Keyforce")
    return None


class KEYFORCE_OT_bake_background(bpy.types.Operator):
    bl_idname = "keyforce.bake_background"
    bl_label = "Bake in Background"
    bl_description = ("Bake the selected meshes in a separate, hidden Blender at low priority, on the GPU if there "
                      "is one: you can keep working while it runs. A copy of the scene is saved for it to bake")

    recommended: bpy.props.BoolProperty(options={"HIDDEN", "SKIP_SAVE"},
                                        description="Bake with the recommended settings (Automatic Bake)")

    def execute(self, context):
        import json
        import subprocess
        import tempfile
        settings = context.scene.keyforce
        if BACKGROUND or settings.bake_progress >= 0.0:
            self.report({"WARNING"}, "A bake is already running")
            return {"CANCELLED"}
        objects = [o for o in context.selected_objects if o.type == "MESH"]
        if not objects:
            self.report({"ERROR"}, "Select meshes with a color texture first")
            return {"CANCELLED"}
        target = bake_folder_path(settings)
        if target is None:
            self.report({"ERROR"}, "Save the file first, or choose a full path as the bake folder")
            return {"CANCELLED"}
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if self.recommended:
            apply_world(recommended_settings(settings))
        folder = Path(tempfile.mkdtemp(prefix="keyforce_bake_"))
        blend = folder / "scene.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True, relative_remap=True, compress=False)
        job = folder / "job.json"
        job.write_text(json.dumps({"objects": [o.name for o in objects], "folder": str(target),
                                   "size": int(settings.bake_size), "recommended": self.recommended}))
        script = folder / "run.py"
        script.write_text("import sys\n"
                          f"sys.path.insert(0, {str(Path(__file__).parent)!r})\n"
                          f"import {__name__} as keyforce\n"
                          f"keyforce.run_background_job({str(job)!r})\n")
        log = open(folder / "log.txt", "w")
        process = subprocess.Popen(
            [bpy.app.binary_path, "-b", "--factory-startup", str(blend), "--python", str(script)],
            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
        log.close()
        BACKGROUND.update(process=process, folder=folder, objects=[o.name for o in objects],
                          scene=context.scene.name)
        settings.bake_progress = 0.0
        settings.bake_status = "In background: starting"
        bpy.app.timers.register(poll_background_bake, first_interval=1.0)
        self.report({"INFO"}, "Baking in the background; you can keep working")
        return {"FINISHED"}


class KEYFORCE_OT_bake_background_stop(bpy.types.Operator):
    bl_idname = "keyforce.bake_background_stop"
    bl_label = "Stop Background Bake"
    bl_description = "Stop the background bake; textures it already finished stay on disk"

    def execute(self, context):
        if BACKGROUND:
            BACKGROUND["process"].kill()
        return {"FINISHED"}


class KEYFORCE_OT_bake_prerendered(bpy.types.Operator):
    bl_idname = "keyforce.bake_prerendered"
    bl_label = "Bake Pre-rendered Textures"
    bl_description = ("Bake the lit look of the selected meshes (color, spec, normal and the lighting below) "
                      "into one color texture per source texture, on their own UVs")
    bl_options = {"REGISTER", "UNDO"}

    recommended: bpy.props.BoolProperty(options={"HIDDEN", "SKIP_SAVE"},
                                        description="Bake with the recommended settings (Automatic Bake)")

    def start(self, context):
        """The bake as a generator of steps, or None when it can't start."""
        settings = context.scene.keyforce
        self.objects = list(context.selected_objects)
        folder = bake_folder_path(settings)
        if folder is None:
            self.report({"ERROR"}, "Save the file first, or choose a full path as the bake folder")
            return None
        size = int(settings.bake_size)
        if self.recommended:
            settings = recommended_settings(settings)
            apply_world(settings)
        return bake_prerendered_steps(context, self.objects, folder, size,
                                      settings.bake_samples, settings.bake_margin, settings.bake_shadows, settings)

    def done(self, context, results):
        settings = context.scene.keyforce
        if settings.bake_apply:
            apply_baked(self.objects, results)
        left_out = sum(r[2] for r in results)
        self.report({"INFO"}, f"Baked {len(results)} textures into {results[0][0].parent}"
                    + (f"; {left_out} stacked islands reuse another island's texels" if left_out else ""))

    def execute(self, context):
        """The whole bake in one go (scripts, no progress shown)."""
        steps = self.start(context)
        if steps is None:
            return {"CANCELLED"}
        try:
            while True:
                next(steps)
        except StopIteration as stop:
            self.done(context, stop.value)
        except Exception as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context, event):
        """From the button: one step per timer tick, so the panel can show
        progress in between and Esc can stop it."""
        if bpy.app.background:
            return self.execute(context)
        settings = context.scene.keyforce
        if settings.bake_progress >= 0.0:
            self.report({"WARNING"}, "A bake is already running")
            return {"CANCELLED"}
        self.steps = self.start(context)
        if self.steps is None:
            return {"CANCELLED"}
        self.shown = False
        settings.bake_progress = 0.0
        settings.bake_status = "Starting"
        self.timer = context.window_manager.event_timer_add(0.2, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def finish(self, context):
        settings = context.scene.keyforce
        settings.bake_progress = -1.0
        settings.bake_status = ""
        context.window_manager.event_timer_remove(self.timer)
        context.workspace.status_text_set(None)
        for area in context.screen.areas:
            area.tag_redraw()

    def modal(self, context, event):
        settings = context.scene.keyforce
        if event.type == "ESC":
            self.steps.close()
            self.finish(context)
            self.report({"WARNING"}, "Bake stopped")
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        if not self.shown:
            # Leave one tick for the panel to draw the step before it runs.
            self.shown = True
            return {"RUNNING_MODAL"}
        try:
            settings.bake_progress, settings.bake_status = next(self.steps)
        except StopIteration as stop:
            self.finish(context)
            self.done(context, stop.value)
            return {"FINISHED"}
        except Exception as error:
            self.finish(context)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.shown = False
        context.workspace.status_text_set(f"Keyforce bake {settings.bake_progress:.0%}: {settings.bake_status}"
                                          "   (Esc stops after this step)")
        for area in context.screen.areas:
            area.tag_redraw()
        return {"RUNNING_MODAL"}


class KEYFORCE_OT_bake_auto(bpy.types.Operator):
    bl_idname = "keyforce.bake_auto"
    bl_label = "Bake Automatically"
    bl_description = ("Bake with the recommended settings (World: Match Material Preview). Manual Bake's lighting, "
                      "Dedupe & Spread and quality settings are left as they are and not used. Dedupe & Spread "
                      "runs on the bake's own copy; your meshes and UVs are not changed")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.keyforce
        if BACKGROUND or settings.bake_progress >= 0.0:
            self.report({"WARNING"}, "A bake is already running")
            return {"CANCELLED"}
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if settings.auto_source == "IMPORT":
            if settings.use_baked:
                self.report({"ERROR"}, "Import: turn off Use Baked Textures to bake the original textures")
                return {"CANCELLED"}
            before = set(context.scene.objects)
            if bpy.ops.keyforce.import_folder() != {"FINISHED"}:
                self.report({"ERROR"}, "Import failed (see Info log)")
                return {"CANCELLED"}
            candidates = [o for o in context.scene.objects if o not in before]
        elif settings.auto_source == "SCENE":
            candidates = list(context.view_layer.objects)
        else:
            candidates = list(context.selected_objects)
        objects = [o for o in candidates if o.type == "MESH" and o.name in context.view_layer.objects
                   and o.visible_get() and not o.hide_render and o.data.uv_layers
                   and base_color_image(o.active_material) is not None]
        if not objects:
            self.report({"ERROR"}, "No visible meshes with a color texture to bake")
            return {"CANCELLED"}
        for obj in context.view_layer.objects:
            obj.select_set(obj in objects)
        context.view_layer.objects.active = objects[0]
        if settings.auto_background:
            result = bpy.ops.keyforce.bake_background(recommended=True)
        else:
            result = bpy.ops.keyforce.bake_prerendered("INVOKE_DEFAULT", recommended=True)
        if not result & {"FINISHED", "RUNNING_MODAL"}:
            self.report({"ERROR"}, "The bake didn't start (see Info log)")
            return {"CANCELLED"}
        return {"FINISHED"}


class KEYFORCE_OT_lighting_reset(bpy.types.Operator):
    bl_idname = "keyforce.lighting_reset"
    bl_label = "Reset to Recommended"
    bl_description = ("Put the World and every lighting setting back to the recommended values "
                      "(what Automatic Bake uses)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.keyforce
        for key in LIGHTING_KEYS:
            settings.property_unset(key)
        if bpy.data.objects.get(KEY_LIGHT) is not None:
            setup_bake_light(context.scene, settings)
        return {"FINISHED"}


class KEYFORCE_OT_bake_light(bpy.types.Operator):
    bl_idname = "keyforce.bake_light"
    bl_label = "Preview Lighting"
    bl_description = ("Set up the bake lighting (ambient and key light) and show it in the viewport's Rendered "
                      "mode. The sliders then change it live")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        setup_bake_light(context.scene, context.scene.keyforce)
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    area.spaces.active.shading.type = "RENDERED"
        return {"FINISHED"}


class KEYFORCE_OT_bake_light_remove(bpy.types.Operator):
    bl_idname = "keyforce.bake_light_remove"
    bl_label = "Remove Lighting"
    bl_description = "Remove the key light and the ambient light from the scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        remove_bake_light(context.scene)
        return {"FINISHED"}


class KEYFORCE_OT_stack_refresh(bpy.types.Operator):
    bl_idname = "keyforce.stack_refresh"
    bl_label = "Refresh Textures"
    bl_description = "List the color textures used by mesh objects"

    def execute(self, context):
        stack = context.scene.keyforce.stack
        ticked = {texture.name: texture.use for texture in stack.textures}
        stack.textures.clear()
        for image, objects in sorted(meshes_by_image().items(), key=lambda item: item[0].name):
            texture = stack.textures.add()
            texture.name, texture.count, texture.use = image.name, len(objects), ticked.get(image.name, True)
        return {"FINISHED"}


class KEYFORCE_OT_stack_start(bpy.types.Operator):
    bl_idname = "keyforce.stack_start"
    bl_label = "Start"
    bl_description = "Go through the ticked textures one by one, opening their objects in Edit Mode"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(texture.use for texture in context.scene.keyforce.stack.textures)

    def execute(self, context):
        stack = context.scene.keyforce.stack
        stack.queue = "\n".join(texture.name for texture in stack.textures if texture.use)
        go_to_texture(context, stack, 0)
        if stack.step < 0:
            self.report({"WARNING"}, "None of the ticked textures' objects can be shown")
        return {"FINISHED"}


class KEYFORCE_OT_stack_unselected(bpy.types.Operator):
    bl_idname = "keyforce.stack_unselected"
    bl_label = "Stack Unselected"
    bl_description = ("Keep the selected UV islands exactly as they are. Unselected ones: halve symmetric "
                      "islands, merge near-duplicate and mirrored copies, then stack them onto the spot inside "
                      "the selected islands where the texture looks the same")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.keyforce.stack.step >= 0 and context.mode == "EDIT_MESH"

    def execute(self, context):
        stack = context.scene.keyforce.stack
        image, objects = texture_objects(context, stack.queue_list()[stack.step])
        objects = [obj for obj in objects if obj.data.is_editmode]
        img = load_pixels(image)
        bms, islands = collect_islands(objects, np.array(img.shape[1::-1], float))
        keep = self.keep_faces(bms, islands, img)
        if not keep:
            self.report({"ERROR"}, self.nothing_kept)
            return {"CANCELLED"}
        if len(keep) == sum(len(island.faces) for island in islands):
            self.report({"ERROR"}, "Every UV island would be kept: nothing to stack")
            return {"CANCELLED"}
        for bm in bms.values():   # show the UVs hidden in the UV editor again
            for face in bm.faces:
                if not face.hide:
                    face.select_set(True)
        wm = context.window_manager
        wm.progress_begin(0, 1)
        stats, left = optimise_uvs(bms, img, stack.max_error, keep, stack.halve, stack.merge, stack.split,
                                   stack.force_move, progress=wm.progress_update)
        wm.progress_end()
        # Show what is left: pieces without a match selected, everything else not.
        for bm in bms.values():
            if bm.loops.layers.uv.active is not None:
                set_uv_selected(bm.faces, bm.loops.layers.uv.active, False)
        for island in left:
            set_uv_selected(island.faces, island.uv, True)
        for obj in objects:
            bmesh.update_edit_mesh(obj.data)
        stack.report = (f"{stats['halved']} halved, {stats['merged']} copies merged, {stats['stacked']} stacked, "
                        f"{stats['split']} split, {stats['forced']} pieces forced, "
                        f"{stats['strips_stacked']} strips stacked on strips ({stats['strips_kept']} kept), "
                        f"{len(left)} pieces left (selected)")
        self.report({"INFO"}, stack.report)
        return {"FINISHED"}

    nothing_kept = "Select the UV islands to keep first"

    def keep_faces(self, bms, islands, img):
        return {face for island in islands if self.keeps(bms[island.obj], island) for face in island.faces}

    @staticmethod
    def keeps(bm, island):
        return uv_selected(bm, island)


class KEYFORCE_OT_stack_strips(KEYFORCE_OT_stack_unselected):
    bl_idname = "keyforce.stack_strips"
    bl_label = "Stack Strips"
    bl_description = ("No selection needed: find the strips (thin rectangles of trim, edge bands, rivet rows) and "
                      "keep every other UV island as it is. Strips go onto the kept islands where the texture "
                      "matches; the rest stay where they are and stack onto each other, each onto the most alike "
                      "longer strip (all metal, half dark / half metal, ...)")
    bl_options = {"REGISTER", "UNDO"}

    nothing_kept = "Every UV island is a strip: nothing to stack them onto"

    def keep_faces(self, bms, islands, img):
        return strip_keep(bms, img)


class KEYFORCE_OT_stack_onto_hidden(KEYFORCE_OT_stack_unselected):
    bl_idname = "keyforce.stack_onto_hidden"
    bl_label = "Stack Visible onto Hidden"
    bl_description = ("Keep the UV islands hidden in the UV editor (H) exactly as they are. Visible ones: halve "
                      "symmetric islands, merge near-duplicate and mirrored copies, then stack them onto the spot "
                      "inside the hidden islands where the texture looks the same. Shows everything again after")
    bl_options = {"REGISTER", "UNDO"}

    nothing_kept = "Hide the UV islands to keep first (H in the UV editor)"

    @staticmethod
    def keeps(bm, island):
        # With UV sync off, hiding UVs deselects their faces.
        return any(face.hide or not face.select for face in island.faces)


class KEYFORCE_OT_stack_next(bpy.types.Operator):
    bl_idname = "keyforce.stack_next"
    bl_label = "Next Texture"
    bl_description = "Hide again what was unhidden and open the next texture (or finish)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        stack = context.scene.keyforce.stack
        go_to_texture(context, stack, stack.step + 1)
        return {"FINISHED"}


class KEYFORCE_OT_stack_stop(bpy.types.Operator):
    bl_idname = "keyforce.stack_stop"
    bl_label = "Stop"
    bl_description = "Stop going through the textures, back to Object Mode"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        stack = context.scene.keyforce.stack
        stack.step = -1
        leave_texture(context, stack)
        return {"FINISHED"}


class KEYFORCE_OT_uv_fold(bpy.types.Operator):
    bl_idname = "keyforce.uv_fold"
    bl_label = "Fold at Cut"
    bl_description = ("Select the faces of the half to keep (or just the edges to cut along, to keep the bigger "
                      "half): the island is cut there and the other half mirrored onto the kept one; the "
                      "mirrored vertices snap onto the kept half")
    bl_options = {"REGISTER", "UNDO"}

    flip: bpy.props.BoolProperty(name="Keep Other Half",
                                 description="Keep the unselected (or the smaller) half and move the other one")
    snap: bpy.props.FloatProperty(name="Snap Distance", default=0.05, min=0.0, max=0.5,
                                  description="Mirrored vertices this close to the kept half (fraction of the "
                                              "island's size) snap onto its vertices, or else its edges")
    force: bpy.props.BoolProperty(name="Force Snap",
                                  description="Snap every mirrored vertex onto its own vertex of the kept half, "
                                              "however far, after lining the halves up (Snap Distance is ignored)")

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        folded, snapped, problems = 0, 0, []
        for obj in context.objects_in_mode_unique_data:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.active
            if uv_layer is None:
                continue
            changed = False
            for faces in visible_uv_islands(bm, uv_layer):
                island = set(faces)
                keep = {face for face in faces if not face.hide and uv_face_selected(bm, face, uv_layer)}
                if keep and len(keep) < len(faces):
                    # Faces selected: keep them, cut where they meet the rest of the island.
                    if self.flip:
                        keep = island - keep
                    cut = [loop for face in keep for loop in face.loops
                           if any(f in island and f not in keep for f in loop.edge.link_faces)]
                else:
                    keep = None
                    cut = [loop for face in faces if not face.hide for loop in face.loops
                           if uv_edge_selected(bm, loop, uv_layer)]
                if not cut:
                    continue
                count, why = fold_island(faces, uv_layer, cut, self.flip, self.snap, keep, self.force)
                if why:
                    problems.append(f"{obj.name}: {why}")
                    continue
                folded, snapped, changed = folded + 1, snapped + count, True
            if changed:
                bmesh.update_edit_mesh(obj.data)
        for problem in problems:
            self.report({"WARNING"}, problem)
        if not folded:
            if not problems:
                self.report({"ERROR"}, "Select the faces of the half to keep, or the edges to cut along")
            return {"CANCELLED"}
        self.report({"INFO"}, f"{folded} island(s) folded, {snapped} UV points snapped")
        return {"FINISHED"}


class KEYFORCE_OT_uv_snap_islands(bpy.types.Operator):
    bl_idname = "keyforce.uv_snap_islands"
    bl_label = "Snap to Active"
    bl_description = ("Stack the selected UV islands onto the active one (the island clicked last; the biggest "
                      "selected one if none is active): turned to fit its outline best, vertices snapped onto its "
                      "vertices")
    bl_options = {"REGISTER", "UNDO"}

    mirror: bpy.props.BoolProperty(name="Allow Mirror", default=True,
                                   description="Also try the island flipped (its texture then shows mirrored)")
    force: bpy.props.BoolProperty(name="Force Snap", default=True,
                                  description="Snap every vertex onto its own vertex of the active island, however "
                                              "far, after lining the islands up")
    snap: bpy.props.FloatProperty(name="Snap Distance", default=0.05, min=0.0, max=0.5,
                                  description="Without Force Snap: vertices this close to the active island "
                                              "(fraction of its size) snap onto its vertices, or else its edges")

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        scale = np.ones(2)
        bms, selected = {}, []
        for obj in context.objects_in_mode_unique_data:
            bm = bms[obj] = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.active
            if uv_layer is not None:
                for faces in visible_uv_islands(bm, uv_layer):
                    island = StackIsland(obj, faces, uv_layer, scale)
                    if uv_selected(bm, island):
                        selected.append(island)
        if len(selected) < 2:
            self.report({"ERROR"}, "Select two or more UV islands; the one clicked last is snapped onto")
            return {"CANCELLED"}
        obj = context.active_object
        active = bms[obj].faces.active if obj in bms else None
        target = next((island for island in selected if island.obj == obj and active in island.faces),
                      max(selected, key=lambda island: island.area))
        snapped, fits = 0, []
        for island in selected:
            if island is not target:
                count, iou = snap_island(island, target, self.mirror, self.force, self.snap)
                snapped += count
                fits.append(iou)
        for obj in {island.obj for island in selected}:
            bmesh.update_edit_mesh(obj.data)
        level = "INFO" if min(fits) >= STACK_MATCH_IOU else "WARNING"
        self.report({level}, f"{len(fits)} island(s) snapped onto {target.obj.name}, {snapped} points snapped, "
                             f"outline overlap {min(fits):.0%} or better")
        return {"FINISHED"}


def draw_fold(layout):
    col = layout.column()
    col.label(text="Select the half to keep, then:")
    col.operator(KEYFORCE_OT_uv_fold.bl_idname, icon="MOD_MIRROR")
    col.separator()
    col.label(text="Select islands, the target last, then:")
    col.operator(KEYFORCE_OT_uv_snap_islands.bl_idname, icon="SNAP_ON")


class KEYFORCE_UL_stack_textures(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "use", text="")
        row.label(text=item.name, icon="IMAGE_DATA")
        row.label(text=f"{item.count} obj")


def draw_stacker(layout, context):
    stack = context.scene.keyforce.stack
    col = layout.column()
    col.prop(stack, "max_error")
    col.prop(stack, "halve")
    col.prop(stack, "merge")
    col.prop(stack, "split")
    col.prop(stack, "force_move")
    col.prop(stack, "hide_others")
    if stack.step < 0:
        col.operator(KEYFORCE_OT_stack_refresh.bl_idname, icon="FILE_REFRESH")
        col.template_list("KEYFORCE_UL_stack_textures", "", stack, "textures", stack, "index", rows=6)
        col.operator(KEYFORCE_OT_stack_start.bl_idname, icon="PLAY")
        if stack.report:
            col.label(text=stack.report, icon="INFO")
        return
    queue = stack.queue_list()
    col.label(text=f"Texture {stack.step + 1} of {len(queue)}")
    col.label(text=queue[stack.step], icon="IMAGE_DATA")
    col.separator()
    col.label(text="Select (or hide) the UV islands to KEEP, then:")
    col.operator(KEYFORCE_OT_stack_unselected.bl_idname, icon="UV_ISLANDSEL")
    col.operator(KEYFORCE_OT_stack_onto_hidden.bl_idname, icon="HIDE_ON")
    col.label(text="Or, no selection needed:")
    col.operator(KEYFORCE_OT_stack_strips.bl_idname, icon="ALIGN_JUSTIFY")
    if stack.report:
        col.label(text=stack.report, icon="INFO")
    row = col.row(align=True)
    last = stack.step == len(queue) - 1
    row.operator(KEYFORCE_OT_stack_next.bl_idname, text="Finish" if last else "Next Texture",
                 icon="CHECKMARK" if last else "FORWARD")
    row.operator(KEYFORCE_OT_stack_stop.bl_idname, icon="CANCEL")


class KEYFORCE_PT_panel(bpy.types.Panel):
    bl_label = "Keyforce"
    bl_idname = "KEYFORCE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Keyforce"

    def draw(self, context):
        pass


class KeyforceSubPanel:
    """Collapsible section of the Keyforce panel."""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Keyforce"
    bl_parent_id = "KEYFORCE_PT_panel"
    icon = "NONE"

    def draw_header(self, context):
        self.layout.label(icon=self.icon)


def draw_bake_progress(layout, settings):
    """The running bake's progress and how to stop it; False when none runs."""
    if settings.bake_progress < 0.0:
        return False
    col = layout.column()
    if hasattr(col, "progress"):
        col.progress(factor=settings.bake_progress, text=f"{settings.bake_progress:.0%}")
    col.label(text=settings.bake_status)
    if BACKGROUND:
        col.operator(KEYFORCE_OT_bake_background_stop.bl_idname, icon="CANCEL")
    else:
        col.label(text="Esc stops after this step", icon="INFO")
    return True


def draw_bake_output(col, settings):
    col.prop(settings, "bake_folder")
    col.prop(settings, "bake_size")
    col.prop(settings, "bake_apply")


class KEYFORCE_PT_import(KeyforceSubPanel, bpy.types.Panel):
    bl_label = "1. Import"
    bl_idname = "KEYFORCE_PT_import"
    icon = "IMPORT"

    def draw(self, context):
        settings = context.scene.keyforce
        col = self.layout.column()
        col.prop(settings, "folder")
        col.prop(settings, "lod")
        col.prop(settings, "target")
        col.prop(settings, "world_on_import")
        col.prop(settings, "static")
        col.prop(settings, "rename")
        col.prop(settings, "use_baked")
        if settings.use_baked:
            col.prop(settings, "baked_folder")
        col.operator(KEYFORCE_OT_import.bl_idname, icon="FILE_FOLDER")


class KEYFORCE_PT_auto(KeyforceSubPanel, bpy.types.Panel):
    bl_label = "2. Automatic Bake"
    bl_idname = "KEYFORCE_PT_auto"
    icon = "AUTO"

    def draw(self, context):
        settings = context.scene.keyforce
        col = self.layout.column()
        col.prop(settings, "auto_source", text="")
        if settings.auto_source == "IMPORT":
            col.label(text="Uses the folder, LOD and object of 1. Import", icon="INFO")
        draw_bake_output(col, settings)
        col.prop(settings, "auto_background")
        if not draw_bake_progress(self.layout, settings):
            self.layout.operator(KEYFORCE_OT_bake_auto.bl_idname, icon="RENDER_STILL")
        self.layout.label(text="Recommended settings; tune them in 3. Manual Bake", icon="INFO")


class KEYFORCE_PT_manual(KeyforceSubPanel, bpy.types.Panel):
    bl_label = "3. Manual Bake (selected meshes)"
    bl_idname = "KEYFORCE_PT_manual"
    icon = "TOOL_SETTINGS"

    def draw(self, context):
        self.layout.label(text="Work through the steps below in order")


class KeyforceManualPanel(KeyforceSubPanel):
    """A step of Manual Bake."""
    bl_parent_id = "KEYFORCE_PT_manual"
    bl_options = {"DEFAULT_CLOSED"}


class KEYFORCE_PT_parts(KeyforceManualPanel, bpy.types.Panel):
    bl_label = "1. Dedupe & Spread"
    bl_idname = "KEYFORCE_PT_parts"
    icon = "MESH_DATA"

    def draw(self, context):
        settings = context.scene.keyforce
        col = self.layout.column()
        col.prop(settings, "gap")
        col.prop(settings, "match", text="")
        if settings.match == "UV":
            col.prop(settings, "tolerance")
        if settings.match != "UV" or settings.tolerance == 0:
            col.prop(settings, "precision")
        col.prop(settings, "into_tile")
        col.prop(settings, "select_inner")
        col.operator(KEYFORCE_OT_dedupe_spread.bl_idname, icon="MOD_ARRAY")
        col.label(text="The bake also dedupes and spreads its own copy", icon="INFO")


class KEYFORCE_PT_lighting(KeyforceManualPanel, bpy.types.Panel):
    bl_label = "2. Lighting"
    bl_idname = "KEYFORCE_PT_lighting"
    icon = "LIGHT_SUN"

    def draw(self, context):
        settings = context.scene.keyforce
        col = self.layout.column()
        col.prop(settings, "world")
        col.prop(settings, "show_hdri")
        col.operator(KEYFORCE_OT_world.bl_idname, icon="WORLD")
        col.separator()
        col.prop(settings, "bake_world")
        col.prop(settings, "bake_ambient")
        col.prop(settings, "bake_surround")
        col.prop(settings, "bake_surround_diffuse")
        col.prop(settings, "bake_tilt")
        col.prop(settings, "bake_key")
        sub = col.column()
        sub.active = settings.bake_key > 0.0
        sub.prop(settings, "bake_azimuth")
        sub.prop(settings, "bake_elevation")
        sub.prop(settings, "bake_soft")
        col.prop(settings, "bake_shadows")
        col.prop(settings, "bake_floor")
        row = col.row(align=True)
        row.operator(KEYFORCE_OT_bake_light.bl_idname, icon="SHADING_RENDERED")
        row.operator(KEYFORCE_OT_bake_light_remove.bl_idname, text="", icon="X")
        col.operator(KEYFORCE_OT_lighting_reset.bl_idname, icon="LOOP_BACK")


class KEYFORCE_PT_uv(KeyforceManualPanel, bpy.types.Panel):
    bl_label = "3. UV (optional)"
    bl_idname = "KEYFORCE_PT_uv"
    icon = "UV"

    def draw(self, context):
        self.layout.label(text="Stack and fold UV islands to free space")


class KEYFORCE_PT_bake(KeyforceManualPanel, bpy.types.Panel):
    bl_label = "4. Bake"
    bl_idname = "KEYFORCE_PT_bake"
    icon = "RENDER_STILL"

    def draw(self, context):
        settings = context.scene.keyforce
        col = self.layout.column()
        draw_bake_output(col, settings)
        col.prop(settings, "bake_samples")
        col.prop(settings, "bake_margin")
        col.prop(settings, "bake_denoise")
        col.prop(settings, "bake_indirect")
        col.prop(settings, "bake_view")
        if not draw_bake_progress(self.layout, settings):
            self.layout.operator(KEYFORCE_OT_bake_background.bl_idname, icon="RENDER_STILL")
            self.layout.operator(KEYFORCE_OT_bake_prerendered.bl_idname, text="Bake Here (blocks Blender)")


class KEYFORCE_PT_uv_stacker(KeyforceSubPanel, bpy.types.Panel):
    bl_label = "UV Stacker"
    bl_idname = "KEYFORCE_PT_uv_stacker"
    bl_parent_id = "KEYFORCE_PT_uv"
    bl_options = {"DEFAULT_CLOSED"}
    icon = "UV"

    def draw(self, context):
        draw_stacker(self.layout, context)


class KEYFORCE_PT_uv_stacker_image(bpy.types.Panel):
    """The same UV Stacker panel in the UV Editor's sidebar."""
    bl_label = "UV Stacker"
    bl_idname = "KEYFORCE_PT_uv_stacker_image"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Keyforce"

    def draw_header(self, context):
        self.layout.label(icon="UV")

    def draw(self, context):
        draw_stacker(self.layout, context)


class KEYFORCE_PT_uv_fold(KeyforceSubPanel, bpy.types.Panel):
    bl_label = "UV Fold & Snap"
    bl_idname = "KEYFORCE_PT_uv_fold"
    bl_parent_id = "KEYFORCE_PT_uv"
    bl_options = {"DEFAULT_CLOSED"}
    icon = "MOD_MIRROR"

    def draw(self, context):
        draw_fold(self.layout)


class KEYFORCE_PT_uv_fold_image(bpy.types.Panel):
    """The same UV Fold & Snap panel in the UV Editor's sidebar."""
    bl_label = "UV Fold & Snap"
    bl_idname = "KEYFORCE_PT_uv_fold_image"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Keyforce"

    def draw_header(self, context):
        self.layout.label(icon="MOD_MIRROR")

    def draw(self, context):
        draw_fold(self.layout)


classes = (KeyforceStackTexture, KeyforceStackSettings, KeyforceSettings,
           KEYFORCE_OT_import, KEYFORCE_OT_world, KEYFORCE_OT_dedupe_spread,
           KEYFORCE_OT_stack_refresh, KEYFORCE_OT_stack_start, KEYFORCE_OT_stack_unselected,
           KEYFORCE_OT_stack_onto_hidden, KEYFORCE_OT_stack_strips,
           KEYFORCE_OT_stack_next, KEYFORCE_OT_stack_stop, KEYFORCE_OT_uv_fold,
           KEYFORCE_OT_uv_snap_islands, KEYFORCE_UL_stack_textures,
           KEYFORCE_OT_bake_prerendered, KEYFORCE_OT_bake_background, KEYFORCE_OT_bake_background_stop,
           KEYFORCE_OT_bake_auto, KEYFORCE_OT_lighting_reset, KEYFORCE_OT_bake_light, KEYFORCE_OT_bake_light_remove,
           KEYFORCE_PT_panel, KEYFORCE_PT_import, KEYFORCE_PT_auto, KEYFORCE_PT_manual,
           KEYFORCE_PT_parts, KEYFORCE_PT_lighting, KEYFORCE_PT_uv, KEYFORCE_PT_uv_stacker, KEYFORCE_PT_uv_fold,
           KEYFORCE_PT_bake, KEYFORCE_PT_uv_stacker_image, KEYFORCE_PT_uv_fold_image)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.keyforce = bpy.props.PointerProperty(type=KeyforceSettings)


def unregister():
    del bpy.types.Scene.keyforce
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
