# v2.4.14

**Model folders bring their unit sprites.** One fix since v2.4.13, for
importing a folder of models into a mod.

A portable install of v2.4.13 fetches this one by itself at the next start.

## Fixed

* **Importing a folder of models left out the unit sprites.** A model entry
  names its `.spr` sprites, and a folder exported with them (beside the mesh
  or in its `unit_sprites/` folder) still had them listed as missing, so a
  mod without those sprites got an entry pointing at nothing. The import now
  finds each sprite like a texture sheet and copies it where the entry
  names it.

## Licence

The toolkit is under the GPLv3. See LICENSE and NOTICE.
