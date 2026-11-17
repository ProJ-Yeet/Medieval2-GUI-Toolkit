# v2.4.13

**Lua scripts, river and diplomacy tools for the campaign map, and building
imports into released mods.** Everything since v2.4.12: Lua scripts over the
toolkit's data, five tools ported from Mylae's M2TW Editor, recruitment as an
editable sheet, duplicate animations found and merged, and a run of fixes.

A portable install of v2.4.12 fetches this one by itself at the next start.

## New

* **Lua scripts (beta)**, a Lua tab on the Scripts screen, offered with
  *Opt into beta features*.
  * A Lua 5.4 script reads and edits the mod's units, model entries,
    mounts, factions, building levels, mercenary pools, traits and
    ancillaries, and can clone a unit.
  * Every run is a preview first: applied, compared and undone. *Apply*
    makes the whole run one entry in My Changes with one Undo. A refused
    edit or a script error undoes the run.
  * Scripts run in a sandbox: no file or system access, and time and
    memory limits.
  * The guide (`web/lua/guide.html`, also the tab's Guide link) goes from a
    first script to every function and field, and ten commented examples
    sit in `web/lua/examples`. `unittransfer/lua_cli.py` runs the same scripts from a
    command line.
* **Campaign Map (beta)**, five tools ported from Mylae's M2TW Editor:
  * **Rivers from a HydroRIVERS file** you download from hydrosheds.org,
    in place of OpenStreetMap's, so the Features card works offline.
  * **Repair rivers**, a fix offered on the river checks: bridges a
    corner-only tile, thins blocks, opens loops and gives a sourceless
    course a source, without moving a course's ends or fords.
  * **The diplomacy check**: an unknown faction, a relation the game cannot
    read (M2EX's protectorate and client states included), contradictions,
    a standing outside -1 to 1, and subject chains.
  * **Update every faction's standings** on the Diplomacy tab, from
    religion, culture, alliances and wars, the weights editable.
  * **Fill every faction from the map** on the Winning tab.
* **Recruitment in Unit sheets**: a recruit_pool line's four numbers edited
  in a cell, pasted, or imported from CSV/XLSX, checked against its unit,
  building and level, and shown as the EDB diff before *Apply*.
* **Duplicate animations** on Home's Animation packs card: one path holding
  different animations is compared and played so you can pick, one
  animation under several paths is merged, with Undo.
* **The unit designer (beta)** gains a Mercenary pools section, and Unit
  sheets a *Design selected unit* button.
* The Unit Editor and the Unit Creator share one armour-tier panel.
* **Armory Studio (beta)**: *Into a mod* opens without a bake first, normal
  maps default to the source models' own, and *Add to a unit* defaults to a
  new armour tier where the unit has one.

## Fixed

* **Bringing building lines from another mod refused a released mod** with
  no `data/text/export_buildings.txt` ("the levels would have no names").
  Creating a tree and renaming a level did the same. All three now read
  the names where the game does: the mod's `.strings.bin`, its packs, or
  the base game.
* **A released mod that draws its buildings from the base game showed no
  building pictures**, and lines brought into it copied no cards: it has no
  culture folders of its own. Such a mod now takes the base game's cultures.
* **A unit transferred from the base game or its campaigns wrote its model
  entry as one 9000-character line.** It is now laid out one value per line,
  as the mod's own entries are.
* **Red paint on dark cloth broke into ragged blocks with dark specks** in
  game. Armory bakes, Art Recolour and the Banner Maker now encode with
  the bundled nvcompress.
* **Half a model drew with the wrong texture** after an Armory install
  baked over two sheets and cloned from an entry with no attachment
  records (every horse in DaC). The clone now gets them.
* **A transferred unit renamed itself to a name whose old cards were still
  on disk**, so France showed England's card. Those names are skipped.
* **Kingdoms campaigns reported false errors** on hold_regions lines that
  give turns to hold, and saving one victory slot dropped an empty
  hold_regions line.
* A faction clone now gets the unit file's era lines as well as ownership.
* The card maker's game art never matched the real sheets.
* The frozen ID column overlapped the next column in every sheet view.
* The designer dropped a unit's own attributes outside its vocabulary.

## Licence

The toolkit is under the GPLv3. See LICENSE and NOTICE.
