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
  * **Bake light**, in the viewport bar: an object with a spec or normal
    map, not baked yet, is drawn live as the Cycles bake (Bake in Blender)
    will bake it: the bake's world, its surround suns, each part's shadows
    on itself, the metal mix, the light floor and AgX. The world and the
    AgX curve are measured in your own Blender once (a few seconds, then
    about half a minute per world the first time it is used). Untick it
    while modelling if the viewport slows down. Import previews of a PBR
    file are drawn the same way, without shadows;
  * the Pre-render panel draws its own bake live too: the spec map, the
    normal map and the key light's soft shadow, as it will write them.

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
