# v2.1.0

Adds a 3D battle model viewer. Previously a model entry could only be inspected
as a list of file paths; viewing one required exporting through IWTE, importing
into Blender and assigning materials manually.

## Added

* **3D model viewer** on the model card in both the Unit Editor and BMDB mode.
  Drag to rotate, wheel to zoom, right-drag to pan. Renders in the browser with
  no external dependencies.
* **Part list** with triangle counts and a checkbox each. Parts the engine
  applies to only some soldiers are marked optional.
* **Variant selection.** A model typically carries several heads, helmets and
  shields and the engine picks one per soldier, so rendering all of them at once
  is not representative. The viewer selects one and offers the rest in a
  dropdown. **Randomize variations** re-rolls the selection.
* **Skins are deduplicated.** An entry listing 29 factions against one pair of
  textures is shown as one skin rather than 29 identical ones.
* **Both textures are composited the way the engine does**, so attachments such
  as scabbards and capes render with their own texture rather than sampling the
  main sheet.
* **A LOD the mod does not ship is greyed out and labelled**, which makes the
  viewer a quick way to find entries pointing at missing files. A file that
  cannot be read reports the reason on the canvas.
* `.texture` files now decode for every screen, not just the viewer, and images
  are downscaled in transit.
* `dev/diagnose/meshdump.py` for inspecting a `.mesh` that will not open.

## Notes

The `.mesh` format is undocumented and was decoded from the files themselves.
4,700 of the 4,702 `.mesh` files across Divide and Conquer and Third Age
Reforged decode successfully, covering every unit model, mount, settlement piece
and siege engine in both. The remaining two are sky domes containing several
models in one file and are refused by name rather than partially read.
