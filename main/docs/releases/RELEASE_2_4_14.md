# v2.4.14

**PBR bakes in Armory Studio, and model folders bring their unit sprites.**
Two new ways to turn a PBR texture set into one lit colour texture, and a fix
for importing a folder of models into a mod.

A portable install of v2.4.13 fetches this one by itself at the next start.

## New

* **Armory Studio (beta)**, in the Pre-render panel:
  * **Bake texture files...** bakes any PBR set into one lit colour texture
    from the textures alone, with no mesh and no Blender. Pick any one map
    and the rest of the set is found by name: colour, metallic, roughness or
    gloss, normal (OpenGL or DirectX), AO, opacity, emission, or a packed
    Bannerlord `_s`, ORM/ARM or mask map. A live preview, then
    `<name>_lit.png` beside the colour map.
  * **Bake a TpacTool export (Blender)...** runs the Keyforce Tools add-on's
    own Cycles bake in a hidden Blender 5.2: every `*_lod<N>.fbx` of a
    gallery export with its `_d`, `_s` and `_n` maps, one lit colour texture
    per source texture in the folder's `Pre-rendered` subfolder, with a
    progress bar and Stop. The add-on's Manual Bake settings are in a fold,
    and *Write a .glb* gives the export wearing its baked textures, ready
    to import.
  * **Bake in Blender (Cycles)** does the same for the Armory's own
    objects.

## Fixed

* **Importing a folder of models left out the unit sprites.** A model entry
  names its `.spr` sprites, and a folder exported with them (beside the mesh
  or in its `unit_sprites/` folder) still had them listed as missing, so a
  mod without those sprites got an entry pointing at nothing. The import now
  finds each sprite like a texture sheet and copies it where the entry
  names it.

## Licence

The toolkit is under the GPLv3. See LICENSE and NOTICE.
