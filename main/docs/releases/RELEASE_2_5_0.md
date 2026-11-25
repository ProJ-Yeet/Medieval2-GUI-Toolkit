# v2.5.0

**The Campaign Map, Armory Studio and the unit card maker leave beta.**
All three are on the menu for everyone now, with no box to tick in Settings.
The base game can be made editable, the card maker and Armory Studio had a
long round of the testers' requests, and animations can be kitbashed into new
skeletons.

A portable install of v2.4.14 fetches this one by itself at the next start.

## New

* **Out of beta: the Campaign Map editor, Armory Studio and the unit card
  maker.** *Opt into beta features* in Settings now only shows the Guided
  unit designer and the Lua tab in Scripts.
* **Settings: Let me edit the base game.** The plain game stays read only
  by default. Ticked, its data folder takes edits like any mod and it is
  offered as a destination: each change is saved there as a loose file,
  which the game reads over its packs, backed up and undoable as usual.
  Making a mod from the game is still the safer way. The Kingdoms campaigns
  in its mods folder were always editable.
* **Unit Editor: Delete for one faction only.** The unit stays for everyone
  else: the faction comes out of its ownership and era lines, out of the
  recruit and retrain lines that name it in the buildings file, and out of
  its armies in the campaign files. One Undo for all of it.
* **Models Editor: Import models from a folder shows each model as a
  turning tile**, its options under it, with a switch to the old list. A
  click on a tile ticks or unticks it. Gallery by default.
* **Animation kits.** A new skeleton from a base, with actions taken from any
  skeleton, slot or mod, bones matched by name or by a map picked from two
  lists; add to a kit made earlier and point the model at it. MilkShape
  `.ms3d` animations convert to `.cas` keeping weapon and shield bones, and
  one dropped on a slot is saved into the pack. A weapon bone can be hidden.
* **Unit card maker:**
  * every man is posed by his soldier line's skeleton, as the game does: an
    elephant's driver and crew where the game puts them, a siege engine's
    crew at its stations, and Crouch or Stand for any man;
  * Mounted off stands a rider on foot, with a Mount action list beside the
    rider's;
  * the unit picker with cards, a docked 3D view, camera and experience
    overlays, a Save menu with a card gallery, Apply now and a Mercenary
    tile, and sessions a new card can start from;
  * the model wears its owner's texture sheet, and one texture choice lists
    the factions it is for.
* **Armory Studio:**
  * Animation Scale saves a whole skeleton at a new size, with Troll, Dwarf
    and Goblin presets measured on DaC's own skeletons, and the export takes
    a Body scale;
  * a bow mesh cloned from an entry with no bow bones takes an archer's entry;
  * Blender-style Edit Mode (vertex, edge, face), Solid, Wireframe and
    X-ray, outlined selection, the Objects panel reworked, UV edge and face
    modes, and the bar in two rows with Sessions, Library and Export;
  * Into a mod picks the unit from card tiles;
  * **Lighting settings** (the panel called Pre-render lighting before)
    offer two bakes. **Light Bake** is the quick one: the light set there,
    with up to three more lights beside the key light, each a sun or a
    point as in the card maker, painted into each colour texture with its
    spec and normal maps and each light's shadow. **PBR Bake** is the
    Keyforce Tools add-on's Cycles bake in a hidden Blender, its settings
    in the panel. After a bake the objects show their baked textures as
    they are. Parts that share texels (head variants, a collar UV'd over
    the legs) are baked to separate textures, so each keeps its own light;
  * **Render mode**, in the viewport bar, draws every object the bake can
    light in the light the chosen bake will paint in, live: Light Bake's
    own, or for PBR Bake the Cycles bake's look (its world, surround suns,
    metal mix, light floor and AgX, measured once in your own Blender).
    Off by default; with it off the viewport draws as quickly as before.
    Import previews of a PBR file use the chosen bake's light, without
    shadows;
  * the list of objects folds away under its own heading.

## Fixed

* **Armory Studio's import from a folder showed the wrong textures.** Each
  tile wore its first object's sheet over the whole model, so an export
  whose first object was a bag or a cape showed its attachment sheet
  everywhere. A tile now puts on the main and attachment sheets as a model
  entry's tile does. The From disk tab has the List and Gallery switch too
  (Gallery by default), and a mod's list that finished loading after you
  moved to From disk no longer paints over the folder.
* **An error in Firefox was logged with no message**, so a report from it
  said nothing. The page log now keeps the message.

## Licence

The toolkit is under the GPLv3. See LICENSE and NOTICE.
