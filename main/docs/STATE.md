# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-24 - **The rest of the roadmap is scheduled and under way**, on the user's word ("finish all phases remaining"): Phases 56-73, then 74-76 (added 2026-09-23: a settlement model imported and assigned, the Strat models 3D view, a building tree from another mod), then 25-27, table under *Phases 56-76* in `ROADMAP.md` (finished write-ups now go to `ROADMAP_ARCHIVE.md`). **56 to 75 are done** (several factions at once and the faction zip; the animation editor and the model converter; will this mod launch; settlement mechanics; add a religion; delete, create and copy a settlement; one file in or out; populace and off-map models; animals, standards and advice; battle banners; hero abilities; area effects; walls and towers; agents and generals; every tile as text; a campaign as a zip and any data/ zip loaded back; a horde start for a new faction; a campaign imported from another mod; a settlement model imported and put on a culture's level; the `.cas` model view placed by its skeleton); **76 is next** (a building tree from another mod). Phase 55 is done: the Models viewer plays a model's animations. Latest cut is **v2.3.8 and beta 2026-09-23** (2026-09-23), carrying everything through 67 and the effect-set fix. **Releasing is on-request only**: commit to master and stop_

## Next up
**Phase 75 is done - the `.cas` model view placed by its skeleton,
2026-09-24, committed and uncut.** A skinned strat model is now drawn in its
bind pose (each node's pivot chained from the root, each vertex moved by its
bone) instead of piled on the origin; all 296 characters in both mods stand,
and all 1,190 settlements and other static models are served byte for byte as
before. A model with no pivots of its own borrows a skeleton `.cas` beside it.
53 ROCSS models with a baked animation, its diplomat among them, now decode
at all. **76 is next.**

**Phase 74 is done - a settlement model imported and assigned, 2026-09-24,
committed and uncut.** *Import…* beside each level's model on the Cultures
screen (and the fort, fort wall, fishing village and watchtower lines) copies
a settlement `.cas` from another mod or from disk with the textures it names,
into a folder where nothing is written over, and puts it on that line keeping
its settlement plan. One backup, one Undo.

**Phase 73 is done - M7, a campaign imported from another mod, 2026-09-24,
committed and uncut.** *From another mod* under *New campaign* in the
campaign browser brings a campaign of another installed mod in as a new
campaign, with its map in its own folder so the base map is untouched. Each
faction is mapped onto a slot this mod declares (same slot, else a free one of
the same culture); a unit it lacks is substituted or left out, and a general
left with nobody gets his slot's bodyguard; buildings, traits, ancillaries,
resources, forts, abilities and battle models it lacks are left out and
counted; religions and rebel types are mapped; names, portraits, region names,
event text and menu keys come across. ROCSS into DaC plans in about 4 seconds.
One backup, one Undo.

**Phase 72 is done - D13, a horde start for a new faction, 2026-09-24,
committed and uncut.** The People panel's new *Horde start* tab (also on the
map's Create screen) fills a faction that holds nothing, the shape 16j-2's
*New faction* leaves. Two modes, both measured on the game's own files: *on
the map from turn one* writes a leader, an heir and more named characters,
each leading one army on free land in a chosen province (D10's grid, two
tiles apart), names from the faction's pool, and the family line; *arrives
later* is vanilla's Mongols: `dead_until_resurrected`, an `event
emergent_faction` in `descr_events.txt` with its provinces, and
`spawned_on_event` on the faction's head line. Both write the seven horde keys
and a roster when the faction has none (its own, else the first complete
horde in the file, else vanilla's). No script is written. Up to three files,
one Undo. **73 is next.**

**Phase 71 is done - D12, a campaign as a zip and any `data/` zip loaded back,
2026-09-24, committed and uncut.** The map's Export tab downloads one
campaign (the base map, the campaign folder, the region names) at its `data/`
paths with a `project.json`, leaving out `map.rwm` and the side copies (22 in
ROCSS, 84 MB of them). *My changes* loads any `data/` zip back (that one, the
changed files, a faction's files): each file planned through Phase 62's put
and shown as new, the same, replacing (records named) or refused; stale
compiled maps deleted; one Undo. **72 is next.**

**Phase 70 is done - T6, every tile as text, 2026-09-24, committed and
uncut.** The map's Export tab writes a `.tsv`, a row per tile: both
coordinates, region, settlement, owner, marker, ground, feature, climate,
height, sea, optionally each layer's colour; land only or the query's
provinces only. A whole map is about a second (ROCSS 260 100 rows, DaC
248 370), and every sampled row agrees with the tile probe. **71 is next.**

**Phase 69 is done - agents and generals, 2026-09-24, committed and uncut.** A
tab edits `descr_character.txt` (each type's actions, wage and action points;
each faction's strat models, battle model and kit), with a grid of which
faction has which type. **The join**: a strat model's card lists every
character block it stands in for, as links, and each model in the tab links
to its own card; routes can now open a Strat models card or a Models editor
entry. Both mods' models and factions all resolve; DaC has two `england`
inquisitor blocks. **70 is next.**

**Phase 68 is done - walls, gates and towers, 2026-09-24, committed and
uncut.** A tab edits `descr_walls.txt`, which is per wall level (0 to 4), not
per culture as the roadmap row said: the wall, the gateway and its gate types,
the tower's firing levels, the gatehouse. Held against the EDB: every
`wall_level` has a block, and every building's `tower_level` has enough firing
levels on its wall. Both mods clean but ROCSS's three empty `shot_gfx` lines
(notes). **69 is next.**

**Animations from an unpacked pack play, 2026-09-24, committed and uncut.**
Asked for by the user: DaC's `pack.dat` had been unpacked in place, which
keeps each file under the path it was packed from, so its 10 427 files sit
under `data/animations/mods/<nine mods>/data/animations/` and the viewer
found none of DaC's 14 735 `descr_skeleton.txt` paths. `casanim.find` now
looks where the game reads (`data/animations/...`), then at the whole path
nested under `data/animations`, then by what follows the last `data/` when
only one file matches, and never by file name alone: 10 396 + 226 found.
**The unpacked files are not `.cas`**: they are pack entries with a `.cas`
name, so `casanim.read_packed_bytes` reads them with the bones of the
unpacked skeleton (`animations/skeleton/<name>`), 40 460 of 41 501 on DaC
(the rest name a skeleton the unpack lacks). MTW2_Mace's walk out of the pack
measures what the loose file did (0.9 s, 1.62 of travel), and the .glb export
still matches Blender. An edit saves as a loose `.cas` beside the entry,
never over it. **68 is next.**

**Cut v2.3.8 and beta 2026-09-23, 2026-09-23, on the user's word
("subrelease it").** Everything since v2.3.7: 55b, 56 to 67, the routes and
trail, the campaign-constants wording, the texture-import fix and the
effect-set fix. Settlements (61), the people panel's ability picker and the
side-panel typing fix are the beta's alone. **68 is next.**

**Phases 77-86 added 2026-09-23, after 25-27**: animations that travel with a
unit, appended to the destination's packs with no unpack or repack. Plan,
measurements and the Discord facts are under *Phases 77-86* in `ROADMAP.md`.

**Effect sets read from every file the engine loads, 2026-09-23, committed and
uncut.** The follow-up Phase 67 found. The effect index and the placeholder
rule read the files `descr_effects.txt` lists (18 on both mods, plus
`descr_oil_effect.txt`, which the executable loads by name) instead of four
fixed ones: ROCSS goes from 112 sets to 344, DaC from 118 to 218, and a
transfer stops blanking the 165 ROCSS projectile lines that point at sets DaC
has outside the four. A listed file the mod does not ship is read from the
install's `data` folder when it is there; when it is packed (this install),
a name nothing can check is still blanked, and the plan says so apart. An M2EX
import never creates an effect file the destination leaves to the base game,
since a mod's copy replaces the base game's whole file. Write-up under Phase
67 in `ROADMAP_ARCHIVE.md`.

**Phase 67 is done - area effects, 2026-09-23, committed and uncut.** A tab
edits `descr_area_effects.xml`, which is battle effects (sickness, fire,
explosions, split shots, holy auras, sets of them), not the interdict the
roadmap row said. The one warning on each mod is a projectile naming an area
effect never declared: ROCSS's `ae_fearcommand_arrow`, DaC's
`ae_poison_javelin`. Found that the effect-set index reads 4 of the 18 files
`descr_effects.txt` lists, which blanks real projectile effects on transfer;
fixed the same day (below). **68 is next.**

**Phase 66 is done - hero abilities, 2026-09-23, committed and uncut.** A tab
edits `descr_hero_abilities.xml` over a new shared reader (`leafxml.py`, also
67's), and the people panel's Hero ability picker now offers what the file
declares, warns on a name it lacks, and links to the ability. Every ability a
character names in either mod is declared; ROCSS's Heart of the Lion has its
selected sprite twice. **67 is next.**

**Phase 65 is done - battle banners, 2026-09-23, committed and uncut.** A tab
edits `descr_banners_new.xml`, the faction audit has its Battle banners row,
and the faction clone writes its thirteenth file. Found DaC's thirteen lines
after `</Banners>` and ROCSS's two broken texture paths. **66 is next.**

**Phase 64 is done - animals, standards and advice, 2026-09-23, committed and
uncut.** One tab, three files: `descr_animals.txt` (checked against the EDU's
`animal` lines and the battle modeldb), `descr_standards.txt` (the flag models,
six rectangles, the symbol sheets) and `export_descr_advice.txt` (threads,
items, and the triggers that fire them). Found ROCSS's Princess carrying
`animal wardogs` where the file declares `wardog`. **65 is next.**

**Phase 63 is done - populace and off-map models, 2026-09-23, committed and
uncut.** A tab edits `descr_lbc_db.txt` (each faction's townsfolk, shares
totalled to 100) and `descr_offmap_models.txt` (navy, settlement and port, read
as the brace tree they are). It found DaC's `faction egypt` with no opening
brace, which ends DaC's navy section fourteen factions early. **64 is next.**

**Phase 62 is done - B3, one file in or out, 2026-09-23, committed and
uncut.** Raw text downloads the open file, replaces it from disk, or puts any
file at any path under `data/`, each a plan (encoding changes, the file's own
reader, `.strings.bin`, a DDS wrapped onto a `.texture`) and one Undo. **63
is next.**

**Phase 61 is done - B2, settlements deleted, created and copied, 2026-09-23,
committed and uncut.** The settlement panel deletes a settlement (the
province stays, as vanilla's Durazzo does; a moving capital and a faction left
with nothing are said), creates a village in a province nobody holds, and
copies a settlement into the same province of another mod's campaign,
leaving out and naming buildings that mod lacks. **62 is next.**

**Phase 60 is done - add a religion, 2026-09-23, committed and uncut.**
Adding a religion now also gives every region's `religions` line `name 0`
in every `descr_regions.txt`, can start it with a share in chosen regions
(taken from the others in proportion so each line stays exactly 100), gives
the share back on a delete, and can copy another religion's pip. **61 is
next.**

**Phase 59 is done - settlement mechanics, 2026-09-23, committed and
uncut.** A tab beside Campaign constants edits
`descr_settlement_mechanics.xml`: the growth, order and income factors
(`SIF_MINING` is the mines) and the two population ladders. DaC's
`large_city` upgrading below its own base is why "upgrade above base" is not
a rule; an upgrade above `max` is. Both mods clean. **60 is next.**

**Phase 58 is done - will this mod even launch, 2026-09-23, committed and
uncut.** Each Home card has a *Launch* row: every way the mod folder offers to
start the game (a `.bat`, the M2TWEOP launcher's `uiCfg.json`, a bare `.cfg`)
and, for each, whether its `.cfg` names this folder, sets `file_first`, and
starts an executable that is there and Large Address Aware. Both installed
mods will start. **59 is next.**

**Phase 57 is done - edit an animation, and get a model out, 2026-09-23,
committed and uncut.** The Models viewer's Animation section has an *Edit*
fold (trim, speed, in place, scale, turn a bone, set a bone at a key) over a
writer that puts all 1 751 loose files back byte for byte, and saves beside
the original with an optional `descr_skeleton.txt` repoint and one Undo; every
save says a loose file reaches the game only once `pack.dat` is rebuilt
(`xidx`). *Export* gives a `.glb` (skeleton, skin, texture, actions; stock
Blender imports it and its posed man matches the viewer's within 0.4 mm), an
`.obj` zip, and `.texture`/`.dds` conversion. **58 is next.**

**Phase 56 is done - several factions at once, and the faction files as a zip,
2026-09-23, committed and uncut.** The first of the phases scheduled when the
user asked for the rest of the roadmap (56-73, then 25-27). *Add a faction*
takes several rows from one donor, planned one on top of the other and written
as one job with one Undo; each row can set its titles and strengths, and a
checkbox turns the donor's name in its copied text into the new one ("Mordor
Scout" to "Rhûn Scout"). *⇩ Faction files* downloads every faction file, and
the open faction's art, as a zip laid out under `data/`. **57 is next.**

**Phase 55b is done - a battle model that moves, 2026-09-23, committed and
uncut.** The viewer's new *Animation* section lists every action the entry's
skeletons name, plays the ones the mod ships loose (DaC's MTW2_Mace: 156 of
195) and marks the rest packed (ROCSS: all of them, and it says so). Play,
pause, scrub, speed; a cycle is played in place. **It found a defect in 55a**:
an animated file's pivots come after its key block, not before, and both
orders fit every byte count, so 55a's checks passed while every key was read
`nodes x 12` bytes late. Read right, w is last and every rotation is unit
length; 55a's "the exporter does not normalise" was the misread too. The skin
is two bones a vertex, packed like the normals (first bone in the third
byte), done on the CPU at 1.7 ms a frame. Not done: `pack.dat`, the
skeleton's `scale`, a rider on his mount. Write-up under *Phase 55*.

**Routes, tabs and a breadcrumb trail, 2026-09-23, committed and uncut.**
Asked for after a Health run: open the file behind a finding in a NEW tab, and
get back to the list where you left it. A screen and the record in it are now
one object, a **route** - `{mode, name, tab, rel, line, key}`, which is the
shape `health.py` already hung on every finding as `open`. It has an address
(`?go=<mode>&name=…`, the general case of the hand-rolled `?edit=` and
`?building=`), so a link to one is a real `<a href>` and **middle click opens
it in a new tab without a line of JavaScript** - only the plain left button is
intercepted, so ctrl-click and the context menu come free. Under the header,
the **trail**: where you have been, as links, with ← →. It is a list with a
finger rather than a stack, which is what makes Forward exist, and each entry
keeps the screen's scroll, so fixing a finding and coming back puts the row you
opened it from under the cursor. `hlOpen`'s walk moved into `navGo` in core.js,
`state.modeTrail` became `state.trail`, and the browser's Back button walks the
new one. Two things it found: **Health crashed when a repaint reached it before
its report did**, which is what a tab opened straight on `?go=health` does, and
**a dialog survived a mode switch** and sat over the screen that came next -
the crumb bar is under it, so both are fixed. `test_back_button` covers the
trail, the address and the shutting.

**Campaign constants: two findings that were not what they said, 2026-09-23.**
Reported off a Health run. `bool="true "` was called "not true or false", which
is no help in front of a box that reads true: blank space inside the quotes is
now named as blank space, as a warning, with the trimmed value in the sentence.
And `int="100.0"` was called "not a whole number" when it is a hundred: a whole
number spelled as a decimal is taken, as a **note**, so it is out of Health's
default list; `100.5` in the same box is still an error. `cdbBad` in the UI was
taught the same two, so the box no longer paints red for what the server takes.
A campdb finding also carries its `key` now, so Health's Open → lands on the
tag instead of the top of the screen.

**A tester's pass on the building editor, 2026-09-22, committed and uncut.**
Eight reports, two of them real defects. **Hiding the code view dropped its
text** while the rows still counted lines from it, so Probe and Save planned
those numbers against the whole EDB: "capability line 8 is no longer there -
skipped" for every row, and the edits to them were lost (the pane is now kept,
only hidden). **Resource names were matched by spelling**: the vocab keyed each
hidden resource as the region file wrote it, so an EDB declaring `Resl` found no
region carrying `ResL`. The rest: a faction picked brings its culture, the grid
card's buttons wrap, the resource picker is a suggestion list instead of a
`<datalist>` (Chrome hid the exact match and matched region names), an
**Interface size** setting (CSS `zoom`, every vh/vw divided back by it), and the
editor's scrolling lists and Probe fold to their headings, closed by default.

**Phase 44 is done - the EDB's tree, checked, closed 2026-09-20, BOTH lines.**
Nine rules ship, **three are refused, and the refusals are the phase.** The
scoping said six go in as stated; measuring found that **one of the six could
not either**. His "a level nothing upgrades into is unreachable" assumes every
line is a chain, and **42 lines across the two installed mods are not** - their
levels are alternatives picked by a hidden resource, so "reachable" means
nothing on them. Reshaped to `tree.second_entry` at `note`, excluding those,
which leaves three real multi-entry chains on DaC, and DaC ships.

The two level-count ceilings are refused on Phase 12's ruling, **a count from a
wiki is not a fact about a mod**: his "vanilla limit is 9" fires on two DaC
lines at 13 and 12 levels and that mod plays, and his "approaching 50" has
nothing to measure against. Both are in `buildings.RULES_REFUSED` and travel
out to the panel, because the next person to read his validator will find them
in it.

**The five reference rules find nothing on either mod, which is what they are
for** (Phase 31's precedent). The reassuring number is **336
`building_present_min_level` references, all resolving both the line and the
level** - the one condition in the EDB that can dangle twice and had nothing
checking it. Write-up under *Phase 44* in `ROADMAP.md`. **45 leads.**

**Phase 51 is done - order, insert below, a still code view and every gate at
once, closed 2026-09-21, both lines, cut as v2.3.6 and beta 2026-09-21.** Recruit pools and
capabilities drag and step, and the file gets the list's order; `＋` puts rows
under the one it was pressed on; the code view scrolls on click only (a
setting); and each clause says which regions pass all its resource gates.
**It found a shipped defect: trade resources were never in any region**, so the
clause picker has said "nowhere" for every `requires resource` since Phase 12.
They are placed by `descr_strat.txt`, and `edbvocab` now joins them in. With
that fixed, three real DaC pools can be met nowhere, and now say so.
Write-up under *Phase 51* in `ROADMAP.md`.

**Phase 52 is done - change sets, closed 2026-09-21, both lines, committed and
uncut.** A **My changes** screen: every save to a mod is recorded as it happens
(the original on first touch, yours on every write, both outside the mod), the
change list is worked out record by record, and a port onto the mod after an
update, or onto another folder, is a three-way merge per record with a
checklist, a side-by-side and one Undo. Export and import as one file. The hook
is `logutil.file_op`, the one function every writer passes. Undoing a port puts
the set back as well as the files. Write-up under *Phase 52* in `ROADMAP.md`.

**Phase 53 is done - change sets switched in place, closed 2026-09-21, both
lines, committed and uncut.** *Versions of this mod* on My changes: several sets
per mod, one on, and a switch that takes one set's records out and puts
another's in as one job with one Undo. Off is the port run backwards against
the disk, not the baseline written back, so an update is never thrown away with
your edits; a switch that would conflict is refused and names the records. With
every set off, the next save starts a new version. Write-up under *Phase 53*.

**Phase 45 is done - the hidden resources line, closed 2026-09-21, both lines,
committed and uncut.** A panel on the Buildings screen adds names to the EDB's
`hidden_resources` line and takes them off; a removal first lists every
province that carries the name and every clause line that gates on it (on DaC,
`Eregion` is 10 provinces and 636 lines) and is refused until that is
acknowledged. The count is stated beside TWCenter's 63-or-64 ceiling, which DaC
(75) and ROCSS (74) both pass. Write-up under *Phase 45*.

**Phase 46 is done - Cultures gets a screen, closed 2026-09-21, both lines,
committed and uncut.** Cultures is its own mode with a four-tab form, the port
ladder is editable at last, **Duplicate** writes a new culture from one that
works and names the text keys, factions and art it still needs, and the Factions
form is on five tabs. The scoping's "three EMT_<CULTURE>_PRIEST keys" was wrong:
a culture has one to five, and the common ones are per faction. Write-up under
*Phase 46*.

**Phase 47a is done - the six export sound banks, closed 2026-09-21, both
lines, committed and uncut.** A **Sound banks** screen beside Unit Sounds opens
soldier voices, strat map voices, battle events, pre-battle speech, advice and
narration: each a tree of blocks, each block's events editable, and any block
duplicated, renamed or removed. It is a new parser, not `sounds.py`: those files
set depth by keyword rather than indent, carry `VnV` as a line of its own, and
put attributes on sample lines. All twelve files on both mods round-trip byte
for byte. Write-up under *47a*.

**Phase 47b is done - the sound scripts, closed 2026-09-21, both lines,
committed and uncut.** A **Sound scripts** tab beside the banks opens the 31
`descr_sounds_*.txt` files and music types: every event, `DEFAULT:` line and
setting editable, a selector's values changed in place, a named event copied,
renamed or removed. Attributes are typed off what the two mods write. All 64
files round-trip byte for byte. A selector's block is never cut, because its
extent is set by indentation these files do not keep to. Write-up under *47b*.

**Phase 48 is done - the strings screen adds and removes, closed 2026-09-21,
both lines, committed and uncut.** A tagged archive takes new entries and loses
rows in the same save as its edits, with the count before and after shown; an
archive addressed by position says why it takes neither, in the backend's own
sentences. A new tag with a space or a brace is refused (none of the 36,219
installed tags has either). Write-up under *Phase 48*.

**The 2026-09-13 pass is finished, and so is everything scheduled.** Phases 45,
46, 47a, 47b and 48 are all committed and uncut, each a subrelease on both
lines; what comes next is the user's call. Write-ups under *Phases 51-53*
in `ROADMAP.md`.
**This repo takes outside contributions now, in two shapes.** **Demircan
pushes directly to `origin/master`** - `865c22f`, "campaign map editor v0.1",
2026-09-20. **Check `origin` and pull before starting any work**: the two port
commits were sitting unpushed on top of his and had to be rebased.
**WalhallaZ contributes by pull request** - `4ca984e` is
`Medieval2-GUI-Toolkit#1`, ported rather than merged, and he is credited by
name in v2.3.5's notes. Two different habits, and only the first one can
surprise a session mid-edit.

**Nothing of ours was overwritten by it.** His commit branched from `4ca984e`,
before both port commits, and touches `unittransfer/server.py` only inside the
campaign-paint handler. It never goes near `app.py`, `unittransfer/startup.py`
or `dev/release/build_release.py`, which is where the port work is. The rebase
was clean and `WSAEACCES = 10013` and the move-rather-than-refuse preflight are
both still in the tree.

**His commit closes no open roadmap item.** It extends seven that are already
done - 17d's markers, 17e's hover, 20b's find box, 20c's labels and pin,
22a/22b's placement, and 28a/28b/49/50's workspace - and adds one thing that
was never tracked at all, **character editing on the campaign map**. The
searchable region browser is **not** M10 arriving: M10 is an OSM backdrop and
a region search together, three stars, and it is `Phase 25` in the Future list.
Write-up in `ROADMAP.md` under *The contributor's campaign map editor*.

**M18 is done - the map in 3D, closed 2026-09-20, asked for outright.** A
**mode** on the campaign map, not a second screen: `⛰ 3D` on the toolbar or
`D`, and the mesh is textured with `cmapPaint`'s own stack, so it has no layer,
opacity, season or colouring controls of its own and cannot drift from the flat
map. One vertex per tile with no decimation (248,370 on DaC), sea by
`mapvocab.is_sea_height` alone where his rule is two, and the ground is 23a's
composite blitted rather than sampled per tile in the browser. Two faults found
while testing it and both now in the suite: a bare `requestAnimationFrame`
hangs the build in a hidden tab, and `loseContext()` does not free a canvas to
be drawn on again. `tests/test_map3d.py`, 34 checks, the mesh run for real in
node against both installed maps. Write-up under *M18* in `ROADMAP.md`.

**Phases 44 to 48 are still what is next by the order**, and none of them is
campaign-map work, so neither the contributor's commit nor M18 moved the queue.

**Cut 2026-09-17 on request: v2.3.4 and beta 2026-09-17.**
The user asked mid-session for two more things on the mercenary panel, both in
these builds: each unit's card on every line and list row, and picking a
mercenary lights every province selling it at once, with a toggle beside the ◉
button, on by default.

**Both blocks the user set are finished.** Phase 39 closed the mercenary block
on 2026-09-17, after 32a, 32b and 32c the same day and 38 before them. Next by
the order is Phases 44 to 48, which have their own table in `ROADMAP.md`. 38
and 39 are subreleases (both lines); 32a to 32c are beta only. All of that is
cut - it is in v2.3.4 and beta 2026-09-17.

**Phase 39 is done - the engine ceilings, closed 2026-09-17, BOTH lines,
committed and uncut.** **The scoped list was Rome: Total War's**: its "max 60
men" flagged 300 DaC units and 113 Reforged units on mods that play. What is
checked now has a Medieval II source each (the archive's M2TW EDU guide and
Docudemons 5.3): 500 units (M2EX lifts it), 4 to 100 men, attack 63, HP 15,
three officers, three mount effects, two formations and how they pair. Rome's
charge/armour/shield/turns/per-faction numbers are not checked, and neither is
the 20,000-face strat limit - DaC ships three models at 30,252. Shown on the
unit editor's fields tab and as a save warning for a ceiling the edit crosses;
never refused. DaC 29 of 924 units, Reforged 6 of 427. Write-up under *Phase
39 / Done* in `ROADMAP.md`.

**Phase 32c is done - six mercenary rules and the two-pools repair, closed
2026-09-17, beta line, committed and uncut.** 39 is next and last in the block.

All six are warnings: Fellowship 49 unit lines not in the EDU and
`Mt-Gram_Province` in two pools, Reforged imperial 2 years outside the
campaign, DaC 4 events nothing in its campaign folder sets. The repair is a
**Keep in X** button per pool on the Mercenaries panel, through `region_move`,
because which pool is a choice. Write-up under *32c done* in `ROADMAP.md`.

**Phase 32b is done - who can hire what, and where, closed 2026-09-17, beta
line, committed and uncut.** The user asked for the whole mercenary block, so
32c and 39 follow straight on.

`mercpools.hire_view` resolves five gates per unit line for a faction or for
nobody, with `unknown` for an event nothing in the campaign sets. The Province
tab's **Mercenaries** sub-tab shows both directions and edits a pool entry
through 32a's writer; three new colourings (`merc_count`, `merc_any`,
`merc:<unit>`). **Reforged's imperial campaign has two lines no faction ever
hires** (`start_year 2986`, campaign ends 2984); DaC's two "dead" units are in
its EDU now. Write-up under *32b done* in `ROADMAP.md`.

**Phase 32a is done - `descr_mercenaries.txt` has one reader and it keeps the
whole line, closed 2026-09-17, beta line, committed and uncut.** 32b leads.

`mercpools.py` reads every gate - `exp`, `cost`, `replenish lo - hi`, `max`,
`initial` and the optionals - and writes by splicing at character positions.
`mapquery.parse_mercenaries` and G3's `campfiles` names are calls into it, and
every campaign reads the same pools as before. 363 unit lines on this machine,
none with a fault; the scoping's counts held exactly.

**Read before 32b: the gates are five, not four.** `factions { }` is an
optional the file's header never mentions and **41 of Fellowship's 51 lines
carry it**, so on that campaign a faction can be named outright rather than
reached through its religion. No screen in this phase, by the write-up's own
split. Write-up under *32a done* in `ROADMAP.md`.

**Phase 38 is done - `descr_campaign_db.xml` is a tab of Minor Files, closed
2026-09-17, BOTH lines, committed and uncut.** It was 16th in the order and the
last of block one, so **the campaign map block is finished and 32a leads**.

**The file types itself**, so the form needed no vocabulary: each value is one
attribute named `uint`, `int`, `float`, `bool` or `string`, and the box comes
off that. Divide and Conquer is 262 tags, Reforged 217, the same 18 sections,
and 25 tags in the first and not the second. **ElementTree is the gate, not
the parser** - a save is a splice between two quotes and a result it cannot
parse is refused; both real files round-trip byte for byte with no findings.

**Fourteen tags have words under them and they are the archive's**: the three
fort switches, the Britannia piety mode and its three values, the seven ransom
chances. Seven of them are printed whole, and those are the only ones that can
be added to a file that lacks them - **Reforged lacks all four piety tags**.
The fort permanence 22a could not reach is `destroy_empty_forts false`, and
both mods already have it. There is **no vanilla copy on this machine**.

One defect beside it, found by reading: a mod switch inside Guilds did not
clear `state.gu`. Write-up under *Phase 38* in `ROADMAP.md`.

**The upstream review of 2026-09-17 is done and nothing is scheduled off it.**
`187d9ed..439aa9b`, 34 commits, 49 files, the largest sync since the mirror was
set up; the manifest is at 342 files with none untriaged. **Four candidates are
filed as M18 to M21 in `REFERENCE_GAPS.md` and none of them is rated** - the
next action on this is the user's stars, not code. The write-up is in
`ROADMAP.md` under *The 2026-09-17 pass*.

**His `.cas` and `.mesh` readers are ours.** `m2CasCodec.js` and
`m2MeshCodec.js` carry our constant names, our values and one of our comments
verbatim, dated two days after Phase 29; the header of the reader he deleted to
make room says his own spec was invented. Those four files are `skip` now and
the asset half of the port-concept set is closed. Nothing to do about it - the
traffic has gone the other way all year - but do not audit his model code for
format knowledge again.

**Phase 50 is done - the map opens the way it is used, and the stack comes off
the column, closed 2026-09-16, beta line, committed and uncut.** Asked for as
two requests, both of them about what the screen is like before you have touched
it.

**Four switches were defaults from the first day nobody had changed since.**
The settlement names and the terrain textures both opened OFF, which is right
for a reading that costs something and wrong for the two that are how this map
is read - the first thing done on opening was turning both on, every session, on
every mod. They open ON now, in summer, with a gap drawn **neutral** rather than
pink; the tooltip already did. Each one is `saved.x === undefined` and not
`!!saved.x`, so **turning one off is still a habit that sticks** - the new
default is what a mod with nothing saved gets, not a switch that flips back
every session.

**A named view is untouched by all four**, because `mapviews.js` carries its own
fallbacks (`!!p.terrain`, `'magenta'`) and a preset saved before 23a still looks
like it did when it was saved. That separation was already there and this is the
first thing that needed it.

**The server's `GAP_DEFAULT` stays pink**, and that is the interesting half: the
browser's opening habit and "what a request that names no gap is drawn with" are
two different questions, and six checks in `test_mapterrain` are about the
second one. The browser sends `&gap=` on every fetch, so nothing but an API
caller sees the difference.

**20a's ruling finally cost more than it was worth in the column.** The layer
stack is not a tab and still is not one, but it was pinned under the tab body at
45% of the column's height on every errand and it **vanished with the column**
when that was collapsed. It is a button at the foot of the map now - `▤ Layers
2/10`, the count so a shut panel is not a hidden one - and a panel over the art
it is about. Same markup, same `#cmLayers`, so `cmapRepanel` and
`cmapWireLayers` did not move with it; `s` opens it, Escape closes it last
(after the pin and the selection), and **the ten number keys tick a layer with
it shut**, which is the ruling standing rather than being repealed. `layer_panel`
is a habit in `cmapLayerState` like the tab strip above it.

New: `cmapLayPop`, `cmapLayerCount`, `CMAP_GAP_DEF`, `#cmLayPop`, `#cmLayBtn`,
`#cmLayN` and `.cmfoot`/`.cmlaypop`/`.cmlaybtn`; `.cmside>.cmlayers` is gone.
`tests/test_web_modules.py` **105/105** (was 92). Checked live against DaC with
`map_layers` cleared: the map opens with the terrain drawn, 100 of 200
settlements named at fit, **15 tiles with no texture drawn neutral**, and the
foot reading `2/10`.

**Phase 49 is done - two strips, the colours on the left, and one place for
models, closed 2026-09-16, BOTH lines, committed and CUT as v2.3.3 and beta
2026-09-16.** Asked for directly, with a screenshot of Mylae's map screen
attached and three more requests beside it.

**28a built half the shape and this is the other half.** It grouped sixteen
panels behind six tabs and then stacked every panel of a group down one scroll,
which is the column again the moment a group has seven of them - Province did.
A tab is a group of **sub-tabs** now and one of them is showing: `CMAP_TABS` is
two levels deep, `cmapTabPanels` flattens it, and **every panel of every group
is still in the DOM with its own state**, which is the property 28a's grouping
rests on and the reason the sixteen panel modules cost nothing to move.

**Choosing a sub-tab presses that panel's own toggle.** Nine of them read
nothing until their own button is pressed, which was right stacked and wrong
behind a tab - clicking `Forts` and getting a button that says `Forts` is a
click the screen owes you. `open: {fn, at}` names the toggle and the key its
module keeps `open` on, so it is pressed once and only when the panel is shut.
**Nothing is read until the tab is chosen**, so a restored tab still opens
closed and the validator still does not run itself.

**The palette is a column on the other side of the map.** It was behind the
Paint tab, which is two clicks from the map on every stroke and took the right
column away from the region record or the validator each time. It holds the
three things a stroke needs and nothing else, it is there only while the brush
is armed, and it is wired by `cpaintWireIn` - the same function that wires the
panel and 28b's toolbar - so all three behave the same. **The layer is a toggle
rather than a `<select>`**: the one control on the screen you could not read
without opening it, and it sits on top of the colours that change with it.

**BMDB + Sprites is the Models Editor, and two things moved to make the name
true.** The Strat map tab gained the BMDB browser's own 3D panel - same split,
same saved width, same detach-and-reattach - and **206 of DaC's 237 entries**
carry a mesh the mod really ships, which is what the 🧊 is offered on; an entry
whose `.CAS` files are all in a `.pack` gets no button rather than a 404. And
**16k's model browser came here from the campaign map**, where it edited nothing
and sat beside nothing else about models. That half matters most: a settlement
is picked by level and culture out of the folder tree with nothing naming the
file, so **DaC declares 237 entries and ships 926 model files** and Amon Hen and
Minas Tirith are in none of them.

**One defect found on the way, and it was already shipped.** A docked viewer
whose host the next screen wrote over was never stopped - a WebGL context and an
animation loop drawing to an element no longer on the page. True of the BMDB
panel since it was built; a second dock is what made it worth fixing rather than
noticing. `v3DropOrphan` runs once from `applyMode`, after the render that puts
back every dock that is still real.

`tests/test_web_modules.py` **92/92** (was 86 before this phase, and 34 when
28a wrote it). **108 suites run, 96 green, and the twelve reds all fail
identically on a stashed tree**, same suites and same checks - they are the
three installed mods, not this work. `test_mapcheck` is 100/101 either way; its
other two reds in the full sweep are the one-second timing bar under load and
are not there when it runs on its own.

**Phase 37b is done - the front-end picture, framed, closed 2026-09-16, beta
line, committed and uncut.** The scoping named the frame first and was right to;
what it did not know is that there is no size `map_FE.tga` wants.

**Eight files, six distinct, four distinct sizes, three mods, and not one of
them is its own map's shape** - the closest, BCBuff's, is 3.6% out. **Two of the
eight are not maps at all** (DaC's base picture is its logo, its Shattered
Alliances one is four faction emblems) and **one of the six that are does not
fill its own frame**, because BCBuff's is a map inside a painted border.

**So the frame carries the picture's aspect, not the map's, and that is what
makes one zoom enough.** The view transform is a single scalar and stays one; a
frame shaped like the picture is exactly what lets one number draw the picture
at one image pixel per screen pixel with the map undistorted under it. **The
proposed frame is what the artists used**: registering each real picture against
its own `map_regions.tga` by the moments of the two land masks gives 1.524 px
per tile for DaC against the 1.506 proposed (**1.2% apart**) and 0.566 for
Reforged against 0.565 (**0.2%**). Only one axis of each is quotable - Reforged's
sepia painting has the same parchment for sea and land and its mask reads 98.2%
land - and **that a picture cannot be registered from its own pixels in general
is the reason the frame is proposed and then dragged**.

**The phase turned out to be a fix for a defect that was already on the
screen.** `cmapCompose` draws every layer into a canvas that is one pixel per
*tile* and the view scales that onto the stage, so DaC's 768x768 front-end
picture was being squeezed into 510x487 and scaled back up - the exact "scaling
up and then scaling down again" T3 exists to avoid, happening every frame. The
picture is out of the composite now: **100 of 100 sampled pixels reach the
canvas byte for byte identical to the file**. Lifting it out exposed a second
one, the composite's opaque backdrop painting over it, and the suite holds both
halves of that guard.

`tests/test_mapfe.py` **75/75**, new. Five suites re-run green. **Twelve suites
fail and all twelve fail identically on a stashed tree** - **a third mod is
installed now**, BCBuff, whose `map_regions.tga` is 295x189 against a
`descr_terrain.txt` saying 420x290, and the numbers moved from 37a's figures
because the mod set changed rather than because anything here did.


**Phase 37a is done - the spawn export, closed 2026-09-16, beta line, committed
and uncut.** The scoping held in full, and the distinction it rests on is why
the phase works at all: 19b refused to WRITE the campaign script because its
grammar is nothing this toolkit models, 24 kept the refusal, and reading
coordinates out of one is not writing it.

**Four fifths of what DaC's imperial campaign puts on the map was invisible on
this screen.** Its script spawns **1,324** things - 1,317 armies carrying 3,822
units - against the 305 characters `descr_strat.txt` places. Shattered Alliances
is another 1,131. The markers layer's counts now read settlement 200, character
305, fort 105, watchtower 295, resource 1,131 and **spawn 1,324**, which is why
this is the one category that opens OFF: switching it on quadruples what is
drawn.

**Every one of the 2,510 `spawn_army` blocks carries a coordinate**, so the
reading is complete rather than a sample and the export has no silent remainder.

**The reading is validated, which matters more than the feature.** Resolved
through `stratobj.Vocabulary.province_at`: **1,322 of DaC imperial's 1,324 land
in a named province and both misses are admirals**, which is correct because an
admiral is a fleet; Shattered Alliances is 1,127 of 1,131. And **all 3,822 of
DaC's unit names are in its EDU**.

**That EDU join is what found the parse bug.** A `character` line inside a spawn
is comma-separated and the `unit` line beside it is not - 4,253 unit lines over
both mods, not one with a comma. Six of DaC's carry `soldiers` as an attribute,
and stopping only at `exp` made those six "Moria Balrog soldiers 1". They were
exactly the six dead references the join reported, so **the six false findings
were the bug's own alarm**.

**Three states, not one.** A spawn that is not in a province is at sea, on a
colour no record declares (two of Shattered Alliances'), or off the map, and the
suite checks the unresolved count never exceeds the three together on every
installed campaign. **A spawn with no coordinate is not resolved at all** - a
test caught it being resolved at the `(0,0)` its fields default to, which on a
real map is ocean, so a missing field was being counted as a spawn at sea.

**Reforged's Fellowship, counted and not judged**: 45 of its 98 spawns are on
sea tiles carrying a land character, and 247 of its 431 unit names are not in
its own EDU. Its `descr_strat.txt` does the same with 72 of 150 characters. The
reason is not established here and 32c's baseline rule is why it refuses
nothing.

`tests/test_spawns.py` **41/41**, new. Seven suites green; `test_campmap`
108/112 and `test_campstrat` 96/100 are the DaC-build numbers and **both are
identical on a stashed tree**.


**Phase 36 is done - a region's colour, changed, closed 2026-09-16, beta line,
committed and uncut.** The write-up's premise is withdrawn.

**A recolour does not renumber, and that is the whole finding.** It was scoped
on "changing one colour can renumber every region after it", which is the one
thing a recolour cannot do: a region ID is the order a colour is **first met**
in a row-major scan, so it is a fact about where a province's pixels ARE, and a
recolour moves no pixel. Measured by renumbering both installed maps with one
province recoloured, the first in the scan and one in the middle: **not one ID
moved in any of the four cases**, and zero again off disk after a real save. So
the panel does not show which regions move, **it says that none do** - which is
the reason to press the button, because the create wizard and the delete both
warn that they renumber and anyone who has read those will assume this does too.

**The one case that renumbers is a merge, and it is refused.** Painting a
province in another province's colour makes two colours one and takes a province
off the map: measured on DaC, **51 IDs move and `Celebrant_Province` is gone**.
The other three refusals are the ones `start_region` already makes, because a
colour is a key and the ways a key can be wrong do not depend on the record
being new.

**Every tile of the colour, not a bucket.** 8 of DaC's 200 regions and 10 of
Reforged's 199 are not one connected blob; a bucket from `Forodwaith_Province`'s
anchor reaches 27,083 of its 40,995 tiles and would leave **13,912 behind in the
old colour**, which is Phase 40's undeclared province made on purpose.

**One real defect, and the existing guard found it by refusing its own save.**
`_emptied` compares declared colours against painted ones, and mid-recolour the
pixels are the new colour while the record still names the old - exactly the
fault it looks for. It now reads the pending record change for that one
province and judges every other one as before, so a recolour that painted over a
neighbour still empties it and still refuses. The mirror case, undoing the
stroke and then saving, is caught by name rather than half-written.

**And the thing that makes IDs matter was counted for the first time.** The
create and delete warnings both end "a script that names a region by number now
names a different one". That script exists: **141 live numeric region references
on DaC** - 76 in `export_descr_ancillaries.txt`, 62 in
`export_descr_character_traits.txt`, 3 in `campaign_script.txt` - and 3 on
Reforged. Whether DaC's 141 are still *correct* is not claimed: the comments
beside them are informal and a string match against the scan order produced
disagreements that were the matcher's fault.

`tests/test_recolour.py` **47/47**, new. Eight suites green; `test_campmap`
108/112 with its four pre-existing failures, and `test_mapcheck`'s only red is
the one-second timing bar, which **a stashed tree fails harder on the same
machine** (1,522 and 1,840 ms against 1,214 and 1,227).


**Phase 35 is done - rebels right in place, closed 2026-09-16, beta line,
committed and uncut.** The scoping was right that this is a join and a screen
rather than a format, and wrong about how much of it was missing.

**Three of the four things it called missing already existed.** What a rebel
faction can field is the Minor Files rebel form, which lists the `unit` lines
and resolves each against the EDU. Changing the assignment from the province
end is the `rebels` box on `cmPick`. Lighting its provinces is `info_rebels`
through `_by_value`, which builds one group per faction - measured at 38 groups
on DaC, one per named faction - and the group filter is the highlight. **The one
thing nothing anywhere did is the reverse: take a rebel faction and see its
provinces.** So what landed is that list plus the one operation the rebel end
has and the province end does not, assigning many provinces at once. **Not a
rebel faction editor**, which is 32c's ruling made again: that record is Minor
Files' and works there.

**There is no rule here and the measurement is why.** The tutorial this was
scoped from complains of Bulgarian rebels spawning in Serbia. On both installed
mods **not one province names a rebel faction that is not declared** (DaC's 200
records name 38 of 42 blocks, Reforged's 199 name 27 of 30) and **not one of the
248 `unit` lines names a unit the EDU does not have**, in any case. A wrong
assignment is a *valid* assignment somebody did not mean and no rule separates
the two. So this ships no `mapcheck` rule and no repair, which is more honest
than a rule that fires on a correct file.

**What it did turn up is `chance`, and it lives in the other file.** **Reforged
sets `chance 0` on all 27 of the blocks its provinces name**, so every one of its
199 provinces points at a faction that will never spawn - province rebels are
switched off across that whole mod, uniformly. DaC spreads it: 2 on 29 blocks, 4
on 7, 6 on one, 10 on one, and `No_Rebels` at 0 on the 9 provinces meant to have
none. So `chance 0` is an idiom, a rule flagging it would be wrong 208 times,
and what it earns is the number on every row.

**Three blocks no province names are not orphans.** Each mod declares exactly one
block per non-`peasant_revolt` category, named after the category, and the engine
spawns those by category. Without that exemption the reverse list calls three
correct blocks dead on every mod. What survives it is real: **two on DaC**,
`Ent_Rebels` and `Saralainn_Rebels`, declared with units and named by nothing.

**The defect it led with is in shipped work.** The region record editor wrote the
base `descr_regions.txt` whatever campaign was on the screen, while the delete
beside it has always honoured 22c. **Reforged's Fellowship ships its own copy and
the two differ in eleven records**, so a save there wrote a file that campaign
does not read. Its other half: `apply_region` deleted `base/map.rwm` alone and
Fellowship ships its own, 14 KB different, so the stale one stayed where the
engine looks first. Fixed at four levels.

`tests/test_rebelpools.py` **68/68**, new. Ten other suites green;
`test_campmap` is 108/112 and **a stashed tree gives the same four failures by
name**, all DaC-number checks against a mod build that has moved.


**Phase 34 is done - a climate is a slot, not a thirteenth name, closed
2026-09-15, beta line, committed and uncut.** The scoping was right about the
files and wrong about the operation.

**The tutorial it names withdraws its own central claim, eighteen posts later,
and the installed mods agree with the thread rather than with the how-to.**
wilddog: a climate the engine does not already know by name is not read by
`descr_geography_new.txt`, the exe looks to be hard coded to those names, and
the answer is to amend an existing one "including the unused1 and unused2
names". Measured here that is not an opinion: **all four installed mods declare
exactly twelve climates, the same twelve in the same order**, and not one added
a thirteenth. **Divide and Conquer has a wholly custom 248,370-tile map and took
a slot over** - `unused1` on 18,970 tiles and `unused2` on 192, called Harondor
and Lorien in `text/climates.txt`. Reforged did the same at 5,466 and 182. So
the operation this adds is the one both big mods performed by hand.

**`descr_geography_new.txt` is the ceiling and it can be read on one mod.**
Vanilla Redux is the only one here shipping the text file rather than just the
compiled `.db`: fifteen top-level blocks, three of them settings sections and
**twelve of them the twelve climates**, four as a bare name and eight as
`<name> modifies <base>`. Taking a slot over is therefore offered first and a
new name second, with that file named as the reason - as a warning, not a
refusal, because three mods in four ship only the `.db` and the strat map draws
a new name perfectly well.

**Four writes, and `map_climates.tga` is not one of them.** The two text files,
the UTF-16 display name (or the `.strings.bin` - two of the four have no `.txt`
at all), and the lookup list when the mod has one. **Painting stays the
brush's**, which is 28b's ruling: what this writes is the colour the brush can
then use.

**Three facts the write-up did not have.** The lookup file is **already wrong in
the wild and it is the tutorial's fault** - its step 4 prints `volcanic` in the
lookup while its step 3 leaves it out of the declared list, and Reforged and
Vanilla Redux ship exactly that; reported, never repaired. A take-over
**strands** the tiles its old colour is on and the count is said out loud, which
is why `claimed_tiles` and `orphan_tiles` are two numbers. And the ground types
in a new block are **the mod's own**: three mods name sixteen and Vanilla Redux
names seventeen, the extra one `impassable_shrouded`, so a constant would be a
line short on one mod in four.

**One defect found on the way, and it is in `mapvocab` rather than in this.**
The climate-block regex took `climate <name>` followed by whitespace and a
brace, so **a comment after the header dropped the whole block** and a declared
climate read as undeclared. No mod annotates `descr_climates.txt` - but all
thirteen of Divide and Conquer's blocks in
`descr_aerial_map_ground_types.txt` are annotated that way, and the two files
are edited together. It mattered now because `climatenew`'s own block finder
skips the comment: the panel would have offered to add a climate that was there
and then overwritten it. All four mods read identically before and after.

`tests/test_climatenew.py` **110/110**, new. Six suites re-run clean after the `mapvocab` fix and all green - `test_mapterrain` 84/84, `test_campaint` 185/185, `test_mapquery` 118/118, `test_campevents` 86/86, `test_web_modules` 75/75. `test_campmap` is 143/148 and `test_mapcheck` 104/105, both **the pre-existing failures and no others**: campmap's five are the DaC-number checks this file already records, and mapcheck's one is `every finding carries a place to go and look`, which a stashed tree produces identically. **One of those two was nearly believed wrongly** - the first sweep had `test_mapcheck` at 103/105 with the rule set taking 1085 ms against a one-second bar, and it was the dev server and a browser running beside it: 804 and 817 ms with them stopped.


**Phase 30 is done - a missing texture without the pink, closed 2026-09-15,
beta line, committed and uncut.** The feature is as scoped and the premise
underneath it is now wrong.

**"This is not the installed mods at rest. It is the paint tool" was true when
it was written and is not true now.** `vanilla_kingdoms_uncompromised` has
**159,855 pink tiles - every land tile it has, 57.6% of its map** - because it
ships **no `terrain/aerial_map/ground_types` folder at all**; its aerial
textures are inside the packed data the way the stock game's are, and nothing
here reads a `.pack`. Tick the terrain on and the whole land mass is magenta.
That is what the report is about, and it is a mod at rest rather than the brush.

**One sentence instead of thirty.** `plan` checks the folder before the
filenames and says it once, naming the folder and the count, rather than writing
a row per texture that blames the aerial file for a folder that is absent. Ten
rows against thirty-nine, pink total unchanged at 159,855.

**The colour.** `GAP_FILLS` is magenta (the default), a neutral dark grey, and
the sea - the honest answer for the case every gap on DaC is. **A choice of how
a gap is drawn and never a choice to hide one**: the count stays on the row and
`terrain.texture` stays in the Check panel, and the suite checks that the count,
the gap rows and every tile that did draw are identical whichever fill is asked
for. It is in the server's disk-cache token and in the browser's own key, or two
colours share one picture.

**One pre-existing red was this all along.** `test_mapterrain`'s "every texture
it draws with is really in terrain/aerial_map/ground_types" was asserting a fact
about the mod rather than the tool. **84/84 against 72/73**, and
`tests/test_web_modules.py` **75/75** against 66.


**Phase 33 is done - T10, G2 and G4 in one sitting, closed 2026-09-15, beta
line, committed and uncut.** Three S items that were separately rated five
stars. Each of the three turned up a measured fact the write-up did not have.

**T10:** `c` copies the tile under the pointer, or the centre of the view when
the pointer is off the map, as `x 109, y 147` - the form **measured off
vanilla's own `descr_strat.txt`**, where every `character` line ends that way.
It copies the **game** y and not the image one; the two differ by counting from
the bottom, and a copy of the image y would put a general on the wrong side of
the map. *The write-up's "the shift-X detail is the model" has no referent
anywhere in this tool or its history.*

**G2:** `mapquery.set_music_region` is the third and last call against
`descr_sounds_music_types.txt`, and it is the drop and the add in order.
`campfiles` has a fourth `what`, and it is the odd one - the file is beside the
map layers rather than in the campaign folder, so **no campaign is sent** and
`map.rwm` is not deleted. A move changes **exactly two lines** and the line
count does not. Two states reported rather than tidied away, both real here:
**58 provinces of `vanilla_kingdoms_uncompromised` are under two music types**
and **2 of Vanilla Redux are named twice inside one**.

**G4:** the legion is the third key a province is read through, and **the only
one that need not name this province**. DaC is the one installed mod that writes
the line - 199 of its 200 records - and only **80** point at the record's own
name; the rest point at another province's key or a settlement's. So the row
follows the line and the label says when the key is somebody else's. **115 of
DaC's 116 distinct legion values already have a line in the names file**; the
one that does not is `Thorenhad_Province`, on `Suduri_Province`, which the panel
now says out loud.

`tests/test_web_modules.py` **66/66** (was 54), `tests/test_campfiles.py`
**101/101** (was 92), `tests/test_mapquery.py` 118/118,
`tests/test_namekeys.py` 64/68 against a clean tree's 63/67.


**Phase 28b is done - the brush is over the map and the tooltip stops moving,
closed 2026-09-15, beta line, committed and uncut.** `.cmbar` is two rows: the
view controls it has carried since 16c, and the arm button, the five tools, the
size and shape and the target layer. A stroke is made with the eyes on the map,
and a control you look away from to reach is a control you lose the stroke to.
The panel keeps what is read rather than reached for - the palette, the wizard,
undo and redo, the save, the unsaved count. `cpaintWire()` became
`cpaintWireIn(box)` so both places wire the same controls.

**`paint_row` is a habit and rides in `cmapLayerState`; `p.on` does not.** A
named view that armed the brush would be a view that starts editing a map, and
the suite checks the snapshot reads the settings and never the paint session.

**The tooltip's frame is exact, not nearly right.** Four causes removed as
scoped - a head of two lines whether or not it has them, a row per layer the
manifest names, a markers block of `CMAP_TIP_MARKS` lines while that layer is
ticked, and a width rather than a maximum with everything clipped on its line.
**The fifth was not in the write-up and it was the last pixel**: `.count` is
11px against 11.5 under `align-items:baseline`, so any row carrying a code moved
every row below it by one. Six probes now give the same 320px width, the same
246px height and the same ten row positions **to the pixel**.

**Three layout rules the scoping did not have**, all about what a toolbar does
to controls built for a 336px column: the tools are a five-column glyph-over-word
grid and on a strip that was 107px of covered map; `.cptg` is `flex:1 1 100%`,
which is what gives the layer picker its own row in the panel and what pushed it
onto a second line here; and an absolutely positioned flex column with wrapping
rows picks a narrower width and wraps inside it, so the bar needs
`width:max-content`. Two rows, 73px, 844 of 1202px on DaC.

**The same lesson as this morning, twice in one day.** Both halves passed every
check while the bar was three rows tall and the tooltip still drifted. The
checks read the source and the source was right; the browser said otherwise.
`tests/test_web_modules.py` **54/54** against 34/34.


**Phase 28a is done - the campaign map's side column is a tab strip, closed
2026-09-15, beta line, committed and uncut.** `#cmSide` was sixteen panels
appended one under the last, and on a 1600px window the strat models sat four
screens below the fold. `CMAP_TABS` is the grouping table - Map, Validate,
Query, Paint, Province, Campaign - and a tab is a **group** of panels, because
sixteen tabs would be the same column laid on its side. Validate is a tab of its
own, which the user asked for by name. The layer stack is in **no** tab and the
suite asserts it, which is 20a's ruling standing.

**Grouping cost the fifteen panel modules nothing.** Each group is a `<div>`
that is hidden or not and every panel keeps the id its own module already writes
into, so only `campforts.js` changed, by one line.

**"Switched to, once" is once per map, and the first draft had it wrong.** It
re-armed the automatic switch on every manual tab pick, which is the obvious
reading: somebody on Paint clicking province after province would be dragged to
Province each time. `cmapSurface` switches once and marks the tab with a dot
after that, which is also what gives the dot any work to do.

**The layer stack had to be capped, and the scoping did not say so.** At its
natural height it is **794px on DaC** in an 842px column, so the tab body got
nothing. `.cmside > .cmlayers` is `flex:0 1 auto` with `max-height:45%` and its
own scroller; `.cmbody` scrolls between the strip and it.

**Two faults only the browser found**, both invisible to the checks because the
checks read the table rather than the layout: `.cmgroup{display:flex}` beats the
UA sheet's `[hidden]`, so all six groups showed at once; and the collapse
control was on the end of a strip that wraps to two rows at 336px, so it landed
wherever the wrap left it. `tests/test_web_modules.py` is **34/34** against
22/22.

**A repair that was not the phase.** Two CSS blocks in `web/index.html` had been
written one character per line by a bad edit earlier in the session - valid CSS,
which is why nothing went red. Both rebuilt, and the whole file scanned for the
shape.


**Phase 43 is done, and almost all of it was already built - closed 2026-09-15,
beta line, committed and uncut.** The write-up said the toolkit reads the three
rosters and will not write any of them. It has written all three since 16j:
`stratcamp.plan_campaign` takes `what="rosters"`, `_roster_splice` replaces each
list where it stands, `roster_block` keeps the block's own indent, the campaign
is a query parameter so it is per campaign, and the Who plays tab is already the
three-way radio per faction the phase asked for.

**"Missing four times over" was four guards read as four refusals.** The line
*"this would change the playable, unlockable or nonplayable lists"* is a
settlement edit, a character edit and a delete each refusing to touch a roster
nobody asked about. `_guard` already exempts the three saves that may move a
name. No writer was owed.

**What was genuinely missing is the refusal, and that landed.**
`camp.no_playable` was a warning, so a save that moved every faction into
`nonplayable` went through. It is fatal now, **and only when the save is what
empties the list** - `check_rosters` takes the lists the save started from as a
third argument, and passed nothing, which is the whole read path, an empty
`playable` list is still only reported. A flat fatal would have refused the save
of a campaign that already had none, which is the one file where this screen is
the repair: 40's ruling, a second time. All six campaigns here write at least one
playable faction - 26, 27, 31, 18, vanilla's 5, the prologue's one - and the
prologue also writes an empty `unlockable` block, so an empty list stays a shape
the writer keeps. `tests/test_stratcamp.py` is **114/115** against 112/113.

**The one failure is older than the phase.** Vanilla Redux writes
`random_persona_weights 15 42 25 18` on its campaign header and `stratcamp` does
not know the word, so part 2's header-words check is red on that mod. The line
round-trips; it is a reporting gap of the `marian_reforms_activated` shape, and
it is not scoped anywhere yet.


**Phase 31 is done - three rules, one repair, no web change, fixed 2026-09-13,
beta line, committed and uncut.** `river.fourway` is a river tile with river on
all four sides; `river.no_source` is a four-connected component with no white
source anywhere along it; `feature.ford_in_sea` is a crossing whose own
altitude reads sea and whose four neighbours do too. **All three find nothing
on any of the five maps installed here**, which is the point of them - they are
rules for a map being drawn, not faults anything ships. The whole set still
runs on DaC in about 650 ms against the 659 measured before, so the one-second
bar has lost nothing.

**The scoping's numbers held this time.** DaC's 95 river components and Third
Age Reforged's 86 came back exactly; two more maps were added to the
measurement, `vanilla_kingdoms_uncompromised` at 73 and `Vanilla_Redux` at 46.

**`feature.ford_in_sea` needed a half the write-up did not have.** "A cyan tile
whose four neighbours are all sea" is what separates a ford in the ocean from a
legitimate coastal crossing, and on its own it is not the defect: `sea_mask`
subtracts **every** cyan pixel unconditionally, so the hole in the ocean only
exists where the tile's **own** altitude reads sea. The rule asks both, and the
message and the repair are true because it does.

**One repair of the three, and the other two are refused on the record.** A
four-way crossing is repaired by removing one arm, and which arm is the map
author's intent; a sourceless river is repaired by painting a source at the
head of the course, and which end is the head needs `map_heights.tga`, the same
second layer that put Geomod's coastline rule out of scope. `ford_none` clears
the crossing to no feature, the heights already say sea, and the suite asserts
the sea mask closes over the tile afterwards. `map_features.tga` is one pixel a
tile, so `_plan_fords` has no block to fill.

**And the new rule found a flaw in the old fixtures.** All three existing river
fixtures painted courses with no source pixel on them, so each began reporting
two findings and tripped `broken(...)`'s "did breaking one thing report only
that thing" check. Each now paints its source. `river.isolated` is better for
it: it is a lone **source** pixel now, which is Mylae's check 4 and the vanilla
`(175,14)` case the rule was measured against.

`tests/test_mapcheck.py` is **104/105** against 93/94 before, the one failure
being the documented `every finding carries a place to go and look`. Eighteen
suites were run against a clean checkout of the previous commit as well as
against this tree and every failing check name is identical in both.

**Two things still to pass back to Mylae**, both from the scoping and both
still true: vanilla trips his orphan-source check at image (175,14) and his
port makes it an `error`, so his validator calls vanilla broken; and the tool
he ported from cannot open either installed map, because both ship
`map_features.tga` as RLE.

**Phase 40 is done, and it was four defects rather than one - fixed 2026-09-13,
both lines, committed and uncut.** The scoped fix is one line and it is the
smallest of the four: `campaint.new_record_lines` wrote the resources line only
when the list was non-empty, so a province created without resources reached
`descr_regions.txt` as an eight-line record in a file of nine-line records, and
the record is read by position. It always writes the line now, `none` when
there is nothing to put on it.

**Three of the write-up's premises were wrong, and measuring them is most of
what the session was.** It said no real record uses the literal `none`: vanilla
writes it on **18 of its 112** records, Vanilla Redux on **78 of 252** and
`vanilla_kingdoms_uncompromised` on **all 853** of its own. So `none` is not a
stand-in chosen here, it is what the empty case already looks like in the files
this writes beside. It said not one of the 510 records omits the resources
line: DaC's last record, `lol`, has 662 painted tiles and no resources line.
And the crash was inferred from the format being positional - **which the
installed DaC contradicts, because it ships exactly that record and the mod
plays.** The crash claim is withdrawn. A game run was named as the first thing
this session should do and it is not owed any more: the mod on this machine is
the experiment, and it already answered.

**Which is why the new check is a warning and not a refusal.** `check_record`
now takes a third argument, `campmap.file_shape(rf)`, and reports a record
short a line its neighbours all write - the check that would have caught the
writer. Fatal was wrong twice over: DaC ships a short record that plays, and
`plan_region` turns a fatal finding into a refusal, so it would have trapped
the one person who could fix it, because **the save is what rewrites the
record**. The shape is counted off the records rather than off their line
counts, which is the distinction the phase turns on: `legion:` is keyed rather
than positional, comments and blank lines sit inside a span, and DaC's records
run to ten lines where vanilla's run to nine. It fires **once** across the
1,616 records installed here, on `lol`, which is right.

**The same defect was in the edit path, and the write-up never looked there.**
`render_block` *dropped* the resources line when the last resource was cleared
off a record - the identical eight-line record, reached from the region panel
rather than from the wizard. It writes `none` there now, and
`tests/test_campedit.py` had a check asserting the old behaviour, which is the
defect written down as an expectation.

**`none` was being read as a resource named `none`.** That put "neither a
hidden resource the EDB declares nor a trade resource descr_sm_resources.txt
names" on **931 records** of the two installed mods that write it - every one
of `vanilla_kingdoms_uncompromised`'s 853, and 78 of Vanilla Redux's - and
listed it among a province's hidden resources in the query table. A lone `none`
is the empty list now; `none, gold` is still two resources. The line on disk is
untouched, so all five installed files still round-trip byte for byte, and the
region panel already drew the word "none" under an empty chip list.

**And the largest of the four was ours rather than the format's: DaC has 200
regions and this read 199.** DaC writes one name line with a stray leading
space, ` Erebor_Province`, and the indent is the whole of the first reading -
so it was body to the record above it and `Withered_Province` swallowed
Erebor whole, twenty lines, **reporting no problems**. Erebor's **517 painted
tiles** came out of here as land declared nowhere: no name in the hover,
nothing to click, a fatal `region.undeclared`, and its settlement marker
reported as an orphan. That orphan was **written into the source as a fact
about DaC** - `RegionIndex.orphan_settlements` said "a province painted on the
map and never written down", and `tests/test_campmap.py` asserted
`== [(339, 65)]`. It was a fact about this module's reader. `_resplit_runs`
splits any record holding two colour lines, which is a signal no well-formed
record can give, so every other file passes through untouched; `parse_block`
reads a record back whose own name line is indented, since `record_text` hands
out the file's own bytes. All **1,504** records of the four installed mods go
`record_text` -> `parse_block` -> `render_block` unchanged, and a block that
has genuinely lost its name line is still refused.

`tests/test_campaint.py` has sections 4c and 4d (**185/185**, was 168),
`tests/test_campmap.py` section 1 has the run-on record (**143/148** against
136/141 stashed, the same five DaC-build failures), `tests/test_campedit.py` is
**139/139** against 138. **Eighteen suites were run against a clean checkout of
the last commit as well as against this tree, and every failing check name is
identical in both.** Nothing regressed.

**One thing left as it is, deliberately.** `test_campview` asserts "the other
undeclared colour is the 517-tile province - the hole 16a found, now measured".
That province is Erebor and it is declared now, so the sentence describes a bug
that is gone - but the check fails on this DaC build either way, for the
hard-coded numbers beside it, so rewriting it would not turn it green. It is
one of the documented DaC-number checks and it needs the build sorted out, not
a new assertion.

**A colour in `map_regions.tga` is not a province - fixed 2026-09-13, beta
line, committed and uncut.** A second report of *no region*, this time on
`Vanilla_Redux`, and the ceiling fix below did not cover it. That map is
295x189 with **252 records and 258 colours**: the 252, black for the 252
settlement markers, white for 146 port pixels, the sea, and **three more shades
of the sea** - `(41,141,243)`, `(41,140,235)`, `(41,141,237)`, within ten of it
on one channel, 591 pixels between the three. The ceiling was measured against
`rgb.getcolors()`, so 591 pixels of paint-program noise refused a map that is
comfortably inside it, and the screen said no region on every tile.

**The two questions had been one number.** How wide a label has to be is ours
and is about the file: every distinct colour needs one, markers and sea and
noise included. How many regions a map may have is the engine's and is about
`descr_regions.txt`. `_label_image` now takes no limit at all - it picks `bytes`
or `array("H")` off the census and refuses only past `MAX_LABELS`, which is the
width of the label - and the ceiling moved into `build_index`, counted off the
records it already had in hand. `mapcheck`'s `layer.colour_cap` had the same
conflation and the same fix: it counted `by_key`, which is 202 on DaC against
199 records, and 202 is over the engine's 200 - a false fatal on a map that
plays. Both now count declared regions.

Vanilla Redux indexes unmarked in **84 ms**: 252 regions, 252 settlements, 146
ports, 16-bit labels with nothing ticked anywhere, and the four sea shades land
in the manifest's `sea_colours`, which has always known what to make of them -
the refusal never let it look. `vanilla_kingdoms_uncompromised` is still refused
unmarked and the refusal now says *declares 853 regions* rather than *856
distinct colours*. DaC and Reforged are byte for byte what they were.

**mapcheck could not see that map at all, and now can.** Eleven rules that read
`not checked - map_regions.tga: ...` on Vanilla Redux now run, and they have
things to say: five second settlement pixels, five provinces with no settlement
pixel anywhere on them, four ports on tiles the engine reads as sea, one
settlement standing on Impassable, and the region cap at 252 against 200.
Sixteen fatal findings about a real map that were invisible while the index
refused to build.

**`text/export_units.txt` saved as anything but UTF-16 took the whole unit list
down - fixed 2026-09-13.** From the same report: `Couldn't open the transfer`,
`UnicodeDecodeError: 'utf-16' codec can't decode bytes in position 0-1: Stream
does not start with BOM`. `Mod.loc` called `localization.parse_file` with no
guard while `Mod.building_loc` twenty lines below it had one, and `loc` is
warmed inside the registry lock on every `/api/units` - which is the first thing
`openComposer` awaits. One names file saved out of Notepad as UTF-8 and the
destination mod could not be read at all.

`localization.read_file` now reads the file off its byte-order mark and returns
what it found with it; `save_encoding` writes it back that way, because
`utf-8-sig` reads a BOM-less file perfectly well and then adds a byte on the way
out. The one exception is an 8-bit file and an edit that puts a character in it
8 bits cannot hold, where "as found" is a crash on save: that goes out as UTF-16
and the warning says so. The three write sites - `transfer.py` and `edit.py`
twice - carry the encoding through `plan.loc_encoding` rather than the module
constant. All four shapes round-trip byte-identical;
`tests/test_parsers.py` has the section, 18 checks.

**The map ceilings are the mod's engine's, not ours - fixed 2026-09-13, beta
line, committed and uncut.** Reported from use: `vanilla_kingdoms_uncompromised`
read *no region* on every tile. It is 823x337 with 856 colours in
`map_regions.tga`, and the label image `campmap._label_image` builds was one
byte a tile with a hard refusal over 256. The refusal raised out of `cm.index`,
`campmap.view` fell to its degraded branch, the manifest carried
`"regions": []`, and the browser's `byKey` was empty - so every tile honestly
reported what the manifest said, which was nothing. The 510-a-side cap said the
same thing about the same map in the layer findings.

Both numbers are in the **vanilla executable**, which is what M2EX replaces, so
both now hang off the mark a person already ticks on the Home card:
`CampaignMap.uncapped` is the one place the map half asks, `label_limit` is what
`build_index` is given, and past 256 the labels are a 16-bit `array("H")`.
Everything that reads them subscripts and does not care; the two that handed the
buffer to Pillow do - `mapquery.render`'s palette swap, now `mapquery._paint`
with a second form, and `regiondel._mask`, now one `map` through a table as long
as the label range. `mapcheck`'s `layer.colour_cap` and `campaint`'s paint
warning are dropped for a marked mod the way the record caps already were.

**Unmarked, the refusal now says what lifts it** and the manifest leads with it:
`view`'s degraded branch used to write `cm.check_layers() or [str(exc)]`, so on
this map - which had a layer complaint of its own - the reason the index would
not build was thrown away. That one `or` is why the screen said "no region"
with nothing anywhere saying why.

Measured on the mod: index 472 ms, manifest 600 ms, adjacency 119 ms, legend
856 rows in 23 ms, `_paint` 28 ms against 1 ms for DaC's palette path, `_mask`
9 ms against 6. Driven through the running server end to end: 854 regions, 853
settlements, 333 ports, and a click names `Kaiwa_Bikeyand_province` on every
layer at once. `tests/test_campmap.py` has a new section 6, 800 one-tile
provinces written here, and its real-mod loop no longer assumes a map is inside
the vanilla ceilings.

**The mod on this machine is still unmarked**, so the map screen still says no
region on it - with the reason at the top of the side panel now. One tick on
its Home card is the whole of it. Six suites that tracebacked on it were fixed
on the way past; see **In-progress detail**, which also has the one real bug
this turned up and did not fix.

**Two blocks, set by the user on 2026-09-12 after rating 38 of 39 candidates:
the whole campaign map first, then the mercenaries.** Everything else is in
`ROADMAP.md`'s *Future roadmap*, rated and unscheduled, to be started when both
blocks are done. Twenty sessions in all; **29, 40, 31, 42 and 41 are done**,
so fifteen are left and two of those are subreleases.

**Block one, the campaign map** - ~~29~~, ~~40~~, ~~31~~, ~~42~~, ~~41~~,
**43**, 28a, 28b, 33, 30, 34, 35, 36, 37a, 37b, 38.

**And six sessions that are in neither block, added 2026-09-13** after the user
asked for a pass over Mylae's non-map screens: Phases **44-48**, all six
subreleases on both lines, sitting after block two until the user moves them.
Write-ups and their own order table in `ROADMAP.md`.

**Phase 42 is done - the per-location art report, fixed 2026-09-14, both
lines when a cut happens, committed and uncut.** The copier was never at fault
and the re-measurement held: `_asset_hits` finds every symbol file for all 31
DaC slots, `want_art` defaults on, `apply` copies each hit and logs it for undo.
A clone simply gets what the donor has, and **the one warning this module had
fires only when the whole scan comes back empty** - banners and unit-card
folders are almost always found, so it never fired however many individual
places came back with nothing. `ART_PLACES` is the nine places a faction's art
lives and `art_gaps` names every one the clone came away from empty-handed,
with which of four reasons: the donor has none either, the destination already
exists, a longer-named faction owns the name, or the mod has no such folder.

**The scoping's four-folder table came back exactly, and one fact under it was
wrong.** It said Reforged's `fe_symbols_80` holds 17 files named for vanilla
slots. It does not - **Reforged's copy of that folder is empty**, and the 17
vanilla-named files are **DaC's**, which is why DaC scores 17 of its own 31:
DaC keeps the vanilla slot names and puts LOTR factions in them. Same
conclusion, different fact underneath.

**And the report is far wider than the report was.** Nine places, four mods,
**every one of the 121 faction slots swept as a donor: 253 empty places, and
only 50 of the 121 donors get art everywhere.** Not one of Reforged's thirty
factions fills every place - all 30 miss the 80px symbol, 16 the captain card -
and `vanilla_kingdoms_uncompromised` is worse than any of them at 146, with 22
of its 35 donors missing the 24px button, the 80px symbol, the in-game symbol
and the banners each. **All 253 are the same reason**, the donor having none;
`exists`, `rival` and `absent` are real, reachable and produced by no installed
mod, so all three get a fixture rather than a claim. `exists` is the
leftover-art case - a mod still shipping a file named for a faction it no
longer has - and was the silent branch before this. Measured on the way past
and worth knowing: **the repair path copies no art at all**, because
`factionaudit.repair_plan` builds its plan by hand and never scans.

`tests/test_factionclone.py` is **74/74** against 64, checking the report both
ways - no place reported empty that got art, no empty place left unreported -
and each reason against the disk rather than on trust.
`tests/test_factionclone_apply.py` is **39/39** against 30, a second synthetic
mod producing all four reasons at once and proving the `exists` skip leaves the
file that was already there byte for byte and out of the undo manifest. Driven
end to end on Reforged through the running server: cloning `aztecs` names four
places with their reasons and the header reads *4 art place(s) empty*.

**Still open on 42: the reporter's own mod.** The user does not have which mod
or which donor, so the end-to-end reproduction against the report itself was
not done. If a second cause exists, this report is what will show it - a clone
that comes back with **no** empty places and still has a blank button is a
different bug from the one closed here.

**Phase 41 is done - the names merge, and the rule that made 58 factions
unsaveable - fixed 2026-09-15, both lines when a cut happens, committed and
uncut.** `merge_section` / `merge_names` / `merge_block` sit in `minorfiles.py`
beside `check_names`, behind that module's own plan/apply pair, with `merge` and
`dedupe` as real actions on the names tab. Three of Mylae's are deliberately not
copied and each is a check: his preview calls a source name *skipped* when
dedupe is off and it is in fact appended (`present` is 0 whenever nothing was
skipped); his Merge button is live with no source, where the only thing it can
do is dedupe, so that is its own button and merging nothing is refused; and his
serializer drops `settlements`, which ours carries. A section only the donor has
is created rather than dropped, indented to match the target's own and with the
blank line real files put between sections.

**The phase could not run its own suite, and that is the bigger half.**
`test_minorfiles` had been dying in the real-mod sweep on `Owaib Cyfeiliog`
since the two vanilla mods were installed, and nobody saw it because **stderr
and buffered stdout interleave** - the traceback landed mid-output and the suite
merely looked like it had one failing check. That is also why the 2026-09-14
sweep listed it as failing with no count.

**`render_names` refused any name with a space, and 2,513 of the four mods'
34,923 names have one**: 45% of every surname (`de Avena`, `of Anglesey`), and
90 characters and 10 women that are not mistakes either - `al Adid`, `Imad ad
Din`, `Arigh Boke`, `Yax Kuk Mo`, `Hywel Dda`. **58 factions across Vanilla
Redux and `vanilla_kingdoms_uncompromised` could not be saved at all**, because
the save refused the very list the form had just handed it; all 121 of all four
mods save now. The rule is replaced by the one real constraint - a name may not
BE a section keyword, since `parse_names` would read it back as a heading - in
one place, `name_fault`, because the old rule was enforced in three and wrong in
all three. **The first draft of the fix relaxed it for `surnames` alone**, on a
sample that happened to be all surnames; the per-section count caught it and the
source says so.

`tests/test_minorfiles.py` is **221/224** against 153 green with a crash before,
including a merge applied to the fixture and undone with every other faction
byte for byte on both sides. Driven end to end on Vanilla Redux: `egypt` taking
`turks` and `moors` previews characters 80 -> 207, surnames 55 -> 246, women
36 -> 116.

**The three the crash was hiding were `descr_sm_resources.txt`, were handed on
as their own job, and are done - `test_minorfiles` is 225/225, green for the
first time.** Neither `is_slave` nor `localised_name` is in `Reference/`, so
both were measured off the mods. `is_slave` is a bare flag like `has_mine`.
**`localised_name` turned out to be the answer to a bug rather than a keyword to
tolerate**: the two mods that write it use it for exactly the three resources
`resource_tag` derives wrongly, because `camels`, `elephants` and `dogs` are
keyed **singular** (`SMT_RESOURCE_CAMEL`) where every other resource including
`slaves` matches its own plural. The tab had been showing **no name at all for
those three in every installed mod** while reporting nothing wrong - "The
Carrock", "Beacon of Gondor", "Horses" in DaC, "Mumakils" in Reforged. And the
31-resource mod **strengthens** the edit-only refusal instead of disproving it:
`glass`, `honey` and `salt` appear in exactly one file in the whole mod, their
own definition, so an unknown `type` being read and ignored is now demonstrated
rather than asserted. The behaviour stands; the sentence was what needed
fixing.

**Start with 43.** 41 is Mylae's names merge. 43 is the playable / unlockable /
nonplayable toggle the user asked for: we parse all three rosters, print their
counts on the campaign card, and refuse the edit in four separate modules with
the same sentence, which is one writer owed rather than four.

**31 and 41 both come from Mylae's 2026-09-12 push and were asked for by the
user on the day.** 31 shrank from four river rules to two when the diff was
measured against our own (`river.rejoin` already catches the 2x2 block,
`river.isolated` already catches the orphan white source) and gained a third
that is ours rather than his, `feature.ford_in_sea`. 41 is his names merge,
which we have no equivalent of at all.

**Then 28, the right menu as a tab strip**, and it is still the enabler: every
later panel lands on it, Phase 32's screen goes onto the right-hand column, and
building it in the old sixteen-panel stack is work done twice. 40, 31 and 41 go
in front of it only because none of the three lands a panel. **Then 33**, three
separate five-star S items in one session (T10, G2, G4), the cheapest five-star
work on the list. The rest of block one is in `ROADMAP.md`'s order table, and
two of its placements are deliberate rather than arbitrary: **30 before 34**,
because declaring a climate without its textures is the largest field of pink
anybody will ever produce here, and **35 before 32**, because it is the same
two-way panel over a file that is already fully parsed.

**Block two, the mercenaries** - 32a, 32b, 32c, then 39. The big one.
`mapquery.parse_mercenaries` keeps a pool's name, its regions and its unit names
and throws away every gate on the line, so 32a is a real record in a new
`mercpools.py` that becomes the one parser; 32b is the two directions and the
four joins, all against modules we already own; 32c is five `mapcheck` rules and
the one repair that has a safe answer. Already measured: DaC names 2 mercenaries
absent from its EDU, Third Age Reforged names 33, and `Mt-Gram_Province` is in
two pools in one campaign, which that file's own header forbids.

**The cut-as-it-lands rule of 2026-09-09 is SUSPENDED AGAIN**, from
2026-09-12, immediately after Phase 29 went out under it. The user: *"from now
on unless i mention it dont move to releasing it and just commit to master"*.
So a phase now ends at **commit to master** - no build, no tag, no upload and
no Discord post - and the user says when a cut happens. When one does, 38 and
39 are the remaining subreleases on both lines because they touch something
outside the campaign map; the other twelve are the beta alone.

**Mylae pushed on 2026-09-12 and the block is lifted.**
`2740b0b..187d9ed`, three commits, 7 files: the base44 package bump (`skip`),
the `map_features.tga` rewrite (**Phase 31**, whose scope it halved rather than
grew) and the names merge (**Phase 41**). The settlement-position validation and
the coloured overlay exports he described are in neither commit, so those are
still unseen - ask for the files rather than scoping from the sentence. Two
things to pass back: his new orphan-white-source check is an `error` and vanilla
trips it at image (175,14), and the `map_features_checker.py` he ported from
cannot open either installed map because both ship RLE TGAs.
The sync is accepted and the manifest filed: `mapFeaturesChecks.js` to Phase 31,
`MergeNamesModal.jsx` to Phase 41.

## WHERE THINGS ARE - the tree moved on 2026-09-06
Only the two `.bat` files and `README.md` are at the top of the repository.
**Everything else is under `main/`, and `main/` is the code root** - what
`config.PROJECT_ROOT` resolves to, what a test's `parents[1]` is, and what every
path in this file and in the source is relative to. `main/dev/` never ships.

## THE TWO RELEASE LINES
Two lines off this one `master`, chosen by whether a change touches the campaign
map. **Not campaign-map** -> a **2.x subrelease with the map hidden**, uploaded
`--latest` (latest **v2.3.8**, 2026-09-23). **Campaign-map** -> the **beta
line**, uploaded as a **pre-release** (latest **beta 2026-09-23**). A
**subrelease means both**: one job, both zips, same tree.

The switch is **one flag**: `off:true` on the `campmap` entry in `MODES` in
`web/js/core.js`, which `menuModes()` and `modeOffered()` are the only readers
of. It is a **release-time edit, not a state of `master`**: set it, bump the 2.x
number, build, upload, then put it straight back off in the next commit.
`master` carries the map ON, and `__version__` says `beta-2026-09-23`
because the beta was the last thing cut.

Of the finished work, **21 and 29 belong to BOTH lines** (raw text is a menu
mode of its own, the faction audit also draws in the Factions mode, and 29's
`icons.png_bytes` is the unit editor's and the BMDB browser's route as well as
the viewer's) and **22a, 22b, 22c, 23a, 23b and 24 are map work**, beta only.
Both blocks are finished, and so is the 2026-09-13 pass (45 to 48, all
subreleases). M18 was the beta alone.

Betas are named by the **date** they were released, with a letter for a second
in one day. The GitHub title is `M2 GUI-Kit V<X.Y.Z>`: hyphenated **GUI-Kit**,
capital **V**; run `gh release list --limit 3` and copy the newest title's shape
rather than typing it from memory. The strict step-by-step is `RELEASE.md`.

**Nothing is written and held any more.** `RELEASE_2_2_4.md` and
`RELEASE_BETA_2026_09_11B.md` are kept as the record of what was drafted;
neither version was ever cut and both were folded into `RELEASE_2_3_0.md` and
`RELEASE_BETA_2026_09_12.md` on 2026-09-12.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 44 - the EDB's tree, checked | **done** | Closed 2026-09-20, committed, **cut** as v2.3.5 and beta 2026-09-20 (both lines - the EDB is not map work). Nine `@rule`-shaped rules in `buildings.py`, `mapcheck.py`'s shape down to the decorator and the `source` field, so M17 gets the EDB behind the same door without a translation layer. Five references that resolve or not (`tree.name_twice`, `no_levels`, `upgrade_unknown`, `convert_unknown`, `min_level_unknown`) all fatal and all finding **nothing** on either mod; three measured warnings (`free_level` 4, `instant_level` 1, `no_factions` 0 of 789 levels); one reshaped note (`second_entry`). **336 `building_present_min_level` references resolve both halves.** `tree_check(edb, line="")` rides in `/api/buildings/checks` rather than a route of its own. **Three refusals in `RULES_REFUSED`, and they are the phase**: two level-count ceilings a shipping mod is over, and his unreachable-level rule, which fires on 42 alternative-lines. Two collisions of my own found by the suite: `TREE_REFUSED` already existed (took `overview()` down) and `bldTreeToggle` already existed in `buildings.js`. `tests/test_buildings.py` +24 checks (12, 12b), `test_web_modules` 117/117. |
| M18 - the map in 3D | **done** | Closed 2026-09-20, committed, **not cut** (beta only - it is map work). Asked for outright, not rated. A **mode** on the campaign map (`⛰ 3D`, or `D`), not a second screen: `cm3Texture` composes the mesh's colour map in `cmapPaint`'s own order, so the 3D has no layer, opacity, season, gap or colouring controls of its own and cannot drift from the flat map. **One vertex per tile, no decimation** - his caps at 2048 steps because his heights are the raw `2W+1` TGA, ours arrive at `fit=tile` and `descr_terrain.txt` caps a map at 510x510 (248,370 vertices on DaC, 260,100 at the ceiling). **Sea is `mapvocab.is_sea_height` alone** where his rule is two, and the suite runs the JS against the Python on both installed maps: 74,365 tiles on DaC and 71,968 on ROCSS, agreeing tile for tile. Normals are a central difference over the height field, not accumulated over faces. **Two faults found by testing and both now guarded**: a bare `requestAnimationFrame` never resolves in a tab that is not being rendered, so the build hung forever with the message up (`cm3Yield` races it against a 120 ms timer); and `loseContext()` does not free a canvas to be drawn on again, so off-and-straight-back-on built a scene that never drew with a null-info-log shader failure (`cm3Stop` swaps the element for a `cloneNode(false)`). The mode is **not remembered between sessions** - it opens a WebGL context - but the height scale and the water plane are, and ride in `cmapLayerState`. Markers, labels and the tooltip stay on the flat map; all four are screen-space and have no place in a scene. New: `web/js/map3d.js`, the button and the `D` key, `cm3DropOrphan` beside `v3DropOrphan` in `applyMode`, the `.cm3card`/`.cm3msg` styles. `tests/test_map3d.py` 34/34, new; `tests/test_web_modules.py` 117/117. |
| the contributor's map editor | **merged** | `865c22f`, Demircan, 2026-09-20, 18 files and 870 insertions on the campaign map workspace. **Closes no open roadmap item** - it extends 17d, 17e, 20b, 20c, 22a/22b and 28a/28b/49/50, and adds character editing on the map, which was never tracked. Its region browser is **not** M10: that is an OSM backdrop and a region search together, three stars, and it is `Phase 25`. Branched from `4ca984e`, before both port commits, so those were rebased on top - clean, and nothing of ours was overwritten (it never touches `app.py`, `startup.py` or `build_release.py`). |
| 39 - the engine ceilings | **done** | Closed 2026-09-17, committed, **not cut** (both lines when a cut happens). `unittransfer/educeil.py`; `ceilings`/`roster_ceilings` on `edit.unit_detail`, a warning in `plan_edit` for a ceiling the edit crosses, `edCeilHtml`. **The scoped list was RTW's**; every checked number has an M2TW source, the RTW-only ones and the 20,000-face limit are not checked (DaC ships 30,252-face strat models). `too-many-units` in `modflags.CAP_FINDINGS`. `tests/test_educeil.py` 24/24. |
| 32c - six rules, one repair | **done** | Closed 2026-09-17, committed, **not cut** (beta only). `merc.unit_unknown`, `region_twice`, `region_unknown`, `religion_unknown` (factions too), `event_unknown` (through `event_sources`, or DaC's 61 script-set events would all be findings), `year_outside`; all warnings. Repair: `mcpKeepIn`, per pool, through `region_move`. Scoped counts did not hold (DaC 0 unknown units, not 2). `test_mercpools` 109/109, `test_mapcheck` 95/97 (timing bar, red before). |
| 32b - both directions, five gates | **done** | Closed 2026-09-17, committed, **not cut** (beta only). `mercpools.hire_view`/`gates`/`event_sources`/`faction_rows`/`campaign_years`; `GET /api/map/mercs`; `mapquery.info_merc_count`, `info_merc_any`, `merc:<unit>`; `web/js/mercs.js` as the Province tab's Mercenaries sub-tab, with edit/add/remove through 32a. Events traced to the script line that sets them (DaC `ND_BOH`, `campaign_script.txt` 10765). Fixed on the way: `faction egypt, spawned_on_event` lost its religion. `test_mercpools` 102/102, `test_web_modules` 112/112. |
| 32a - the pool as a record, one parser | **done** | Closed 2026-09-17, committed, **not cut** (beta only). `unittransfer/mercpools.py` owns `descr_mercenaries.txt`: `parse_unit` keeps all five fixed fields and six optionals with their character spans, `set_field` splices one value (a value set to itself is untouched, `0.10` included), six plan actions with a gate that refuses a save touching a record it did not name. `mapquery.parse_mercenaries` and `campfiles.parse_mercs`/`MercFile`/`set_regions`/`move_region` are calls into it. Found: `factions { }`, undocumented, on 41 of Fellowship's 51 lines - 32b has five gates. `GET /api/mercpools`, `POST /api/mercpools/plan\|apply`. `tests/test_mercpools.py` 73/73, new. |
| 38 - `descr_campaign_db.xml` | **done** | Closed 2026-09-17, committed, **not cut** (both lines when a cut happens). A Minor Files tab and a mode of its own, like Guilds. The form is typed off each tag's own attribute; `campdb.VOCAB` holds the fourteen tags the archive explains and nothing guessed, and the seven it prints whole are the only addable ones. Line scan and a splice between quotes, ElementTree as the gate on save. DaC 262 tags, Reforged 217, both round-trip with no findings; Reforged lacks the four piety tags; no vanilla copy on disk. `state.gu` now cleared on a mod switch. New: `unittransfer/campdb.py`, `GET /api/campdb`, `POST /api/campdb/plan\|apply`, `web/js/campdb.js`, `campdb` in `modfiles`. `tests/test_campdb.py` 50/50, new; `tests/test_web_modules.py` 105/105. |
| 50 - the defaults, and the stack off the column | **done** | Closed 2026-09-16, committed, **not cut** (beta only). Two requests about the state the screen opens in. The settlement names and the terrain textures now open ON (summer, gap **neutral**), each on `saved.x === undefined` so turning one off still sticks; the tooltip already did; a named view is untouched, because `mapviews.js` has its own fallbacks. `mapterrain.GAP_DEFAULT` deliberately stays `magenta` - the browser's opening habit and what an unasked request draws are two questions, and the browser sends `&gap=` on every fetch. The layer stack left the right column for **a button at the foot of the map and a panel over it** (`cmapLayPop`, `#cmLayPop`, count on the button): 20a's ruling standing, not repealed - the ten number keys still tick a layer with it shut, `s` opens it, Escape closes it after the pin and the selection, and it no longer costs the tab body 45% of the column or disappears when the column is collapsed. `tests/test_web_modules.py` 105/105 (was 92). |
| 29 + B4 - the strat model viewer | **done** | Closed 2026-09-12, committed, **released 2026-09-12** as v2.3.2 and beta 2026-09-12c. The scoping was wrong about the root and right about everything above it: the art is not in a `.pack`, it is loose beside the stub as `<name>.tga.dds`, and `cas.texture_path` took the zero-byte `.tga` because it existed. Fixed at all five levels. New: `cas._has_bytes`, `icons.ArtUnreadable`, `icons.fault`, `png_bytes(strict=)`, `/model_texture` 415, `factions.packs_beside`, `factions.no_file_note`, and in `viewer3d.js` `uCutout`, `v3Degenerate`, `v3AskWhy`, `v3TexFault`, `v3FaultRows`. `tests/test_stratart.py` (40). |
| 49 - two strips, the colours left, one place for models | **done** | Closed 2026-09-16, committed, **released 2026-09-16** as v2.3.3 and beta 2026-09-16 (both lines: the Models Editor half is outside the map). Asked for directly off a screenshot of Mylae's screen. **28a's strip was half the shape** - it grouped sixteen panels behind six tabs and then stacked each group down one scroll, and Province was seven panels deep. `CMAP_TABS` is two levels now and every panel is still in the DOM with its own state. **Choosing a sub-tab presses that panel's own toggle** (`open: {fn, at}`), once and only when it is shut; nothing is read until the tab is chosen, so load is unchanged and the validator does not run itself. The palette left the right column for **a dock on the left of the stage**, present only while the brush is armed, and the target layer left 28b's toolbar `<select>` for **eight buttons on top of the colours they change**. BMDB + Sprites is the **Models Editor**: the Strat map tab gained the BMDB browser's own 3D panel (**206 of DaC's 237 entries ship a mesh to point it at**) and 16k's model browser moved here off the map screen, which is the half that matters - a settlement is in no entry at all, and **DaC declares 237 entries and ships 926 model files**. **One shipped defect found on the way**: a docked viewer whose host the next screen wrote over was never stopped, true of the BMDB panel since it was built - `v3DropOrphan`, once from `applyMode`. New: `cmapSubs`, `cmapTabPanels`, `cmapSubId`, `cmapSubOf`, `cmapSubsHtml`, `cmapSub`, `cmapSubOpen` and `m.sub` in `cmapLayerState`; `cpaintChosenHtml`, `cpaintLayerTogHtml`, `cpaintDockHtml`, `cpaintDockPaint` and `#cmPalCol` (`cpaintTargetHtml` is gone); `stmPrev*` and `StratEntry.viewable` with `meshes` on every entry row; `v3DropOrphan`; `stratview.js` rewritten around `#cmodBrowse`. `tests/test_web_modules.py` 92/92 (was 86). |
| 37a - T7, the spawn export | **done** | Closed 2026-09-16, committed, **not cut** (beta only). A read-only scan of the campaign script, which 19b refuses to WRITE and this does not: the refusal is untouched. **DaC's imperial campaign scripts 1,324 spawns - 1,317 armies, 3,822 units - against the 305 characters `descr_strat.txt` places**, so four fifths of what it puts on the map was invisible here; Shattered Alliances is another 1,131, Reforged's Fellowship 98. The markers layer gains `spawn` as its eighth category and it is **the only one that opens OFF**, because it quadruples what is drawn. **Every one of the 2,510 `spawn_army` blocks carries a coordinate.** The reading is validated through `province_at`: 1,322 of 1,324 in a named province with both misses admirals, 1,127 of 1,131 on the other campaign, and **all 3,822 DaC unit names in its EDU**. That join found the parse bug: a `character` line is comma-separated and a `unit` line is not (4,253 lines, no commas), and six DaC lines carry `soldiers` as an attribute, so stopping at `exp` alone produced exactly the six dead references the join reported. Three unresolved states are modelled - at sea, on an undeclared colour (2 on Shattered Alliances), off the map - and **a spawn with no coordinate is not resolved at all**, which a test caught being counted as a spawn at sea at (0,0). Reforged's Fellowship is counted and not judged: 45 of 98 spawns on sea tiles with a land character, 247 of 431 unit names not in its own EDU. New: `unittransfer/spawns.py`, the `spawn` category in `marker_view`, `GET /api/map/spawns`, `POST /api/map/spawn_export` (a CSV to the cache folder, because 16g's TGA export is right for a picture and useless for 1,324 rows), and in `campmark.js` the category, the hollow ring and the tooltip that ends in the file line. `tests/test_spawns.py` 41/41, new. Seven suites green; `test_campmap` 108/112 and `test_campstrat` 96/100 are DaC-build numbers, identical on a stashed tree. |
| 36 - D1, change a region's colour | **done** | Closed 2026-09-16, committed, **not cut** (beta only). **The write-up's premise is withdrawn: a recolour does not renumber.** A region ID is the order a colour is first met in a row-major scan, so it is a fact about where the pixels are, and a recolour moves none - measured at **0 IDs moved** on both mods, recolouring the first region in the scan and a middle one, and 0 again off disk after a real save. The panel therefore says nothing renumbers rather than showing what does, because 16e and 24 both warn that they DO and a reader will assume this one does. **The merge is the case that renumbers and it is refused**: another province's colour moves 51 IDs on DaC and takes `Celebrant_Province` off the map. **Every tile of the colour, not a bucket** - 8 of DaC's 200 and 10 of Reforged's 199 regions are not one blob, and a bucket from Forodwaith's anchor would leave 13,912 of its 40,995 tiles behind in a colour no record declares. **One defect, found by the guard refusing its own save**: `_emptied` reads declared colours against painted ones, and mid-recolour those disagree by design; it now reads the pending record change for that one province and judges every other as before. **141 live numeric region references measured on DaC** (76 ancillaries, 62 traits, 3 campaign_script) and 3 on Reforged, which is what the create and delete warnings are about and had never been counted. New: `campaint.region_tiles`, `recolour_faults`, `recolour`, `cancel_recolour`, `_plan_recolour`, `_emptied(recolour=)`, `sess.recolour`, `_stroke_over` (lifted whole out of `paint`); the `rgb` slot on `campmap.render_block` (`plan_region` goes on refusing that edit); `POST /api/map/recolour|_cancel`; `web/js/recolour.js`, `#cmRecolour`, the Change colour button on the Colour row. `tests/test_recolour.py` 47/47, new. Eight suites green; `test_campmap` 108/112 pre-existing; `test_mapcheck`'s only red is the timing bar and a stashed tree fails it harder. |
| 35 - rebels right in place | **done** | Closed 2026-09-16, committed, **not cut** (beta only). New: `unittransfer/rebelpools.py` (`read_rebels`, `assignments`, `view`, `plan`, `apply`, `RebelPlan`, `REBELS_REL`, `BY_REGION`, `BY_CATEGORY`), `GET /api/map/rebels`, `POST /api/map/rebel_plan|_apply`, `web/js/rebels.js`, `#cmRebels` in the Province tab, the `.reblist` styles. **Three of the four things the scoping called missing already existed** - the unit list is the Minor Files rebel form's and is already joined to the EDU, the province end is `cmPick`'s `rebels` box, and the highlight is `info_rebels`' own group filter (38 groups on DaC). What landed is the reverse join and bulk assignment. **No `mapcheck` rule and no repair, deliberately**: nothing dangles on either mod and not one of the 248 `unit` lines names a unit the EDU lacks, so there is nothing for a validator to find and a wrong assignment is a valid one somebody did not mean. **The finding is `chance`** - Reforged sets `chance 0` on all 27 blocks its provinces name, so all 199 of its provinces point at a faction that never spawns, while DaC uses it for `No_Rebels` alone (9 provinces); a rule would be wrong 208 times, so the number goes on every row instead. **Three blocks no province names are not orphans** - one per non-`peasant_revolt` category, spawned by category - and after that exemption DaC has two real ones, `Ent_Rebels` and `Saralainn_Rebels`. **One defect in shipped work, led with**: `plan_region`/`apply_region` read and wrote the BASE `descr_regions.txt` whatever campaign was on screen, though `CampaignMap` reads the campaign's own copy and the delete beside it honours 22c; Reforged's Fellowship ships its own and **the two differ in eleven records**. Its other half: only `base/map.rwm` was deleted and Fellowship ships its own, 14 KB apart. New for that: `campmap.RWM_NAME`, `campmap.regions_rel`, `campmap.stale_rwm`, a `cm` argument on `plan_region`, and the campaign in `cmapSave`'s body. `tests/test_rebelpools.py` 68/68, new. Ten other suites green; `test_campmap` 108/112 with the same four DaC-number failures a stashed tree gives. |
| 41 - merge one faction's name pool | **done** | Closed 2026-09-15, committed, **not cut** (both lines when a cut happens). `merge_section` / `merge_names` / `merge_block` in `minorfiles.py`, with `merge` and `dedupe` as actions behind the module's own plan/apply. Three of Mylae's corrected, each a check: `present` is 0 whenever dedupe is off because nothing was skipped; merging nothing is refused and names the dedupe button; `settlements` is carried rather than dropped. **And the phase could not run its own suite**: `test_minorfiles` had been dying in the sweep on `Owaib Cyfeiliog`, invisible because stderr and buffered stdout interleave. `render_names` refused any name with a space and **2,513 of 34,923 names have one** (45% of all surnames, plus 90 characters and 10 women - `al Adid`, `Arigh Boke`, `Yax Kuk Mo`, `Hywel Dda`), so **58 factions across two mods could not be saved at all**. Replaced by the one real constraint in `name_fault`: a name may not BE a section keyword. The first draft relaxed it for `surnames` alone and was wrong the same way one size smaller. New: `name_fault`, `merge_section`, `merge_names`, `merge_block`, `_plan_merge`, `MinorPlan.merge`, `mfMergeOpen` and the two buttons in `minorfiles.js`, `.modal.mgwide`. `tests/test_minorfiles.py` 221/224 (was 153 green with a crash). **The three left were handed on and are done** (2026-09-15): `localised_name` is what fixes `resource_tag` for `camels`, `elephants` and `dogs`, which are keyed singular and had been showing no name at all in every mod; Kingdoms' three extra resources are dead in their own mod, which strengthens the edit-only refusal rather than disproving it. 225/225. |
| 30 - a missing texture without the pink | **done** | Closed 2026-09-15, committed, **not cut** (beta only). New: `mapterrain.GAP_FILLS`/`GAP_DEFAULT`, a `gap` argument on `composite` and `png`, `gap_fills`/`gap_default` on `view`, `&gap=` and `|gap|<name>` in the disk-cache token on `/api/map/terrain` plus an `X-Map-Gap` header, `CMAP_GAPS`/`CMAP_GAP_LABELS` and `cmapTerrainGap` in `campmap.js`, `terrain_gap` in `cmapLayerState` and in every named view. **The write-up's premise is withdrawn**: `vanilla_kingdoms_uncompromised` ships no texture folder at all, so 159,855 tiles - all its land, 57.6% of the map - are a gap, which is the report. The thirty rows that blamed the aerial file are one row that names the folder. `test_mapterrain` 84/84 (was 72/73, and the one red was that mod), `test_web_modules` 75/75 (was 66). |
| 34 - a climate is a slot, not a thirteenth name | **done** | Closed 2026-09-15, committed, **not cut** (beta only). New: `unittransfer/climatenew.py` (`lookup_names`, `lookup_state`, `geography`, `climate_tiles`, `slots`, `ground_keys`, `donors`, `climate_block`, `write_climates`, `aerial_block`, `write_aerial`, `write_lookup`, `ClimatePlan`, `plan`, `apply`, `view`, `VANILLA_ORDER`, `SPARE`, `GEOG_SETTINGS`), `GET /api/map/climates`, `POST /api/map/climate_plan|_apply`, `web/js/climates.js`, `#cmClim` in the Paint tab, the `.cclslots` grid. **The scoping was right about the files and wrong about the operation**: its tutorial's own thread withdraws the how-to eighteen posts later, and **all four installed mods declare exactly the twelve climates the engine ships, in the engine's order, and not one added a thirteenth**. Divide and Conquer has a custom 248,370-tile map and took `unused1` (18,970 tiles, "Harondor") and `unused2` (192, "Lorien") over instead; Reforged did the same at 5,466 and 182. `descr_geography_new.txt` is the ceiling and Vanilla Redux is the one mod shipping the readable copy: fifteen top-level blocks, three settings and **twelve climates**. So a take-over is offered first and a new name second, as a warning rather than a refusal. Four writes and **`map_climates.tga` is not one of them** - painting stays the brush's (28b). Three facts the write-up lacked: the lookup file is **already wrong in the wild and it is the tutorial's fault** (its step 4 prints `volcanic`, its step 3 does not; Reforged and Vanilla Redux ship exactly that), a take-over **strands** the tiles its old colour is on, and the ground types in a new block are the mod's own (16 on three mods, 17 on Vanilla Redux with `impassable_shrouded`). **One defect found on the way, in `mapvocab`**: its climate-block regex dropped any block whose header carried a trailing comment, so a declared climate read as undeclared - harmless until now because `climatenew`'s own finder skips the comment, which would have made the panel offer to add a climate that was already there and then overwrite it. All four mods read identically before and after. `tests/test_climatenew.py` 110/110, new. Every other suite touched is green and the two that are not - `test_campmap` 143/148, `test_mapcheck` 104/105 - carry their pre-existing failures and no others, confirmed against a stashed tree. |
| 33 - T10, G2 and G4 in one session | **done** | Closed 2026-09-15, committed, **not cut** (beta only). New: `cmapCopyText`/`cmapCopyTile` and the `c` key, `mapquery.set_music_region`/`music_view`, `campfiles._plan_music` and a fourth `what`, `namekeys.ROW_WHAT` and a legion row in `region_names`, `cmapMusicHtml`/`Set`/`Save` and `CMAP_NAME_ROWS` in `campmap.js`, `out["music"]` on the region route. Measured: the copy form is vanilla's own `x 109, y 147` and it is the game y; a music move changes exactly two lines; 58 provinces of `vanilla_kingdoms_uncompromised` are under two music types and 2 of Vanilla Redux are named twice inside one; DaC writes 199 legion lines of which only 80 name their own record, and 115 of its 116 distinct legion keys have a names line - the one that does not is `Thorenhad_Province` on `Suduri_Province`. `test_web_modules` 66/66, `test_campfiles` 101/101, `test_mapquery` 118/118. |
| 28b - the toolbar over the canvas, and a steady tooltip | **done** | Closed 2026-09-15, committed, **not cut** (beta only). `.cmbar` is two rows; `#cmPaintBar` carries the arm button, the five tools, the size and shape and the target layer, and the panel keeps the palette, the wizard, undo/redo and the save. New: `cpaintBarHtml`, `cpaintBarPaint`, `cpaintSizeHtml`, `cpaintWaterHtml`, `cpaintToolName`, `cpaintRowOpen`, `cpaintRowToggle`, `cpaintWireIn` (was `cpaintWire`), `CMAP_TIP_MARKS`, `paint_row` in `cmapLayerState`. The tooltip's frame is fixed on all five counts - the fifth, `.count` at 11px under `align-items:baseline`, was not in the write-up and was the last pixel. Six probes: same 320px width, same 246px height, same ten row positions. `tests/test_web_modules.py` 54/54 (was 34). |
| 28a - the strip, and the groups behind it | **done** | Closed 2026-09-15, committed, **not cut** (beta only). `CMAP_TABS` groups sixteen panels behind six tabs with Validate one of them; `#cmLayers` is in none and the suite says so. New in `campmap.js`: `CMAP_TABS`, `CMAP_SIDE_CLASS`, `CMAP_SIDE_KEY`, `cmapTabOf`, `cmapTabsHtml`, `cmapTabBadge`, `cmapRailHtml`, `cmapTab`, `cmapSurface`, `cmapSidePaint`, `cmapSideCollapse`, `cmapWireSplit`; `tab`, `side_hid` and `side_px` in `cmapLayerState`, so a named view carries them and `cmapResetView` puts them back. The drag is `splitInstall`'s, a third caller. **Three things the scoping did not have:** the layer stack has to be capped (794px on DaC would take the whole column), `.cmside.wide` and an inline drag width cannot both size it (`edPrevMin`'s problem again), and "switched to, once" means once per map rather than once per manual pick. `tests/test_web_modules.py` 34/34 (was 22). |
| 43 - playable, unlockable, not playable | **done** | Closed 2026-09-15, committed, **not cut** (beta only). **Nearly all of it was already built** - 16j shipped the roster writer (`what="rosters"`, `_roster_splice`, `roster_block`) and `cjRoster` has been the three-way radio per faction all along; the write-up's "missing four times over" was four correct guards in `stratcamp`, `stratchar`, `stratedit` and `regiondel`, and `_guard` already exempts `rosters`, `create` and `delete`. What landed is the refusal: `camp.no_playable` is fatal **when the save is what empties the list**, via a third `before` argument to `check_rosters`; passed nothing, which is the read path, it stays a warning, because a flat fatal would trap a campaign that already had no playable faction on the one screen that repairs it. Six campaigns measured, all with at least one playable. `tests/test_stratcamp.py` 114/115, the one failure being Vanilla Redux's unread `random_persona_weights` header word, red before this phase. |
| 42 - the art a clone does not get | **done** | Closed 2026-09-14, committed, **not cut** (both lines when a cut happens). The copier was never at fault and the re-measurement held; what was missing was a sentence. `ART_PLACES` is the nine places a faction's art lives, `art_gaps` names every one the clone came away from empty-handed with one of four reasons - the donor has none either, the destination already exists, a longer-named faction owns the name, the mod has no such folder. The old whole-scan warning fires only when the scan is completely empty, which on a real mod it never is. **121 donor slots swept over four mods: 253 empty places, 50 clean donors, and all 253 the same reason.** Not one of Reforged's 30 factions fills every place; `vanilla_kingdoms_uncompromised` is worst at 146. The scoping was wrong about one fact: Reforged's `fe_symbols_80` is **empty**, and the 17 vanilla-named files in it are DaC's. New: `ArtPlace`, `ART_PLACES`, `art_gaps`, `_asset_hits(skips=)`, `ClonePlan.art`, `payload()["art_gaps"]`, the `.fcgap` rows in `factions.js` and the places named in the apply confirm. `tests/test_factionclone.py` 74/74 (was 64), `tests/test_factionclone_apply.py` 39/39 (was 30). **Open:** the reporter's own mod is still unknown, so the end-to-end reproduction against the report itself was not done. |
| 31 - two river rules and a ford in the sea | **done** | Closed 2026-09-13, committed, **not cut** (beta only). Three rules and one repair: `river.fourway` (river on all four sides), `river.no_source` (a four-connected component with no white source), `feature.ford_in_sea` (own altitude sea **and** four neighbours sea - the second half the scoping did not have, and without it the message and the repair are not true). All three find **nothing on any of the five installed maps**, which is what they are for. `ford_none` is the one repair with a safe answer; the other two need the map author's intent or `map_heights.tga`, and both refusals are written into `FIXES`. New: `_r_river_fourway`, `_r_river_no_source`, `_r_ford_in_sea`, `_plan_fords`, `FIXES["ford_none"]`. The three existing river fixtures painted sourceless courses and now paint their source. No web change - the panel is data-driven off `RULES` and `rep.fixes`. `tests/test_mapcheck.py` 104/105. |
| 40 - the new province the engine cannot read | **done** | Closed 2026-09-13, committed, **not cut** (both lines when a cut happens). Four defects, one of them the scoped one. `campaint.new_record_lines` and `campmap.render_block` both produced the eight-line record, the second by dropping the line when the last resource was cleared; both write `none` now, which is what vanilla writes on 18 of 112, Vanilla Redux on 78 of 252 and `vanilla_kingdoms_uncompromised` on all 853. `none` read as a resource name was 931 false findings across two mods. And the indent reading lost DaC's ` Erebor_Province` to a stray leading space - **200 regions read as 199**, 517 painted tiles declared nowhere, and its settlement marker written into the source and a test as DaC's one orphan. New: `campmap.file_shape`, `campmap._resplit_runs`, `check_record(rec, vocab, shape)`, a `parse_block` retry for an indented name line. The inferred engine crash is **withdrawn**: DaC ships a short record and plays. `tests/test_campaint.py` 4c and 4d (185), `tests/test_campmap.py` 1 (+7), `tests/test_campedit.py` (139). |
| 28-43 - the rest of the 2026-09-12 review | **done** | Both blocks closed 2026-09-17: block one with 38, block two with 32a, 32b, 32c and 39. Each has its own row above and its write-up in `ROADMAP.md`. |
| 44-48 - the pass over Mylae's non-map screens | **scoped** | Six sessions, added 2026-09-13 at the user's request, in neither block and every one a subrelease on both lines. 44 the EDB's tree checked (his is the one validator he has and we do not), 45 the `hidden_resources` line, 46 cultures on a mode of its own with a four-tab form and the faction form on the same strip, 47a the six `export_descr_sounds_*` files on `sounds.py`'s own parser, 47b the 32 `descr_sounds_*` scripts on a grammar nothing here reads, 48 add and remove on the strings screen. Two of the seven things asked for produced no phase and a measurement instead: his traits and ancillaries have not moved since 2026-03-27, and his `.strings.bin` codec is wrong where ours is right. |
| 24 - Make and unmake | done | Closed 2026-09-12, committed, **released 2026-09-12**. Closes G1, M15 and the roadmap. Deleting a province, with its land going whole to a neighbour it borders and its name coming out of every file 19b measured - and the campaign script listed, never written, for the reason a rename gives. Making a campaign, as a copy of one that works minus the compiled map, with its own header and its own menu keys. New: `unittransfer/regiondel.py` (`heirs`, `campaigns_reading`, `standing_on`, `plan`, `apply`, `view`), `unittransfer/campnew.py` (`sources`, `plan`, `apply`, `view`), `mapquery.drop_music_region`, `renames.mentions`, `campfiles.write_descriptions`, `GET /api/map/region_delete`, `POST /api/map/region_delete_plan\|_apply`, `GET /api/campnew`, `POST /api/campnew/plan\|apply`, `web/js/regiondel.js`, `web/js/campnew.js`. `tests/test_regiondel.py` (62), `tests/test_campnew.py` (52). |
| B2-B3 - from the beta | scoped, unscheduled | Delete a settlement and move one between mods; one-file insert and export. B4 went out inside 29. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-21 | done | 16-20a published on the beta line; 20b onward committed and uncut. The 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |
| 16-23 | done | Every write-up is in `ROADMAP_ARCHIVE.md`. 16-20a published on the beta line; everything from 20b to 24 went out in the 2026-09-12 cut. |
## In-progress detail
**Clean.** Nothing is mid-flight.

**34's own re-run is worth keeping as a method note.** The first sweep put
`test_mapcheck` at 103/105 and the extra red was *the whole rule set runs in
1085 ms, under the one-second bar* - a timing check, failed because the dev
server and a browser were running beside the suite while the phase was being
verified in the preview. Stopped, it is 804 and 817 ms over two runs and the
suite is 104/105, which is the number this file already had. **A stashed tree
gave the same 104/105 and the same single failure by name**, so nothing
regressed. The lesson is the one 41 left about buffered output, one layer up:
a red that is a *measurement* has to be re-measured on a quiet machine before it
is read as a change.

**Phase 41's suite is 221/224 and the three left are the resources tab's, not
41's** - see its row below. It is worth knowing WHY they were invisible until
now: `test_minorfiles` crashed partway through the real-mod sweep, and because
stderr is unbuffered while stdout is not, the traceback landed in the middle of
the output instead of at the end. A suite that dies mid-sweep looks exactly like
a suite with one failing check. **When a suite's pass count is missing from its
last line, it did not finish** - that line is the only reliable sign.

**Phase 42's own suites are green and were measured both ways**:
`test_factionclone` 74/74 against 64 on the stashed tree,
`test_factionclone_apply` 39/39 against 30, `test_factionaudit` 56/56,
`test_renames`, `test_startup` and `test_parsers` all green. `test_factions` is
87/88 and its one failure is *not one of the 121 loading_logo files is
unpacked*, which is a fact about the installed mods: `loading_screen` is one of
the three roots `ART_ROOTS` deliberately excludes, so 42 cannot have touched it.

**The 103-suite sweep of 2026-09-14 got through 87 - 73 green, 14 failing - and
is not to be trusted as it stands.** The shape is at least not alarming: the
2026-09-13 baseline was 85 green and 18 failing of 103, and the fourteen here
are the same families, so nothing cascaded. It was run in the background while Phase 41 was being written, so
every suite it reached after that started - `test_minorfiles` above all - was
measured against a tree that was moving underneath it. It also *speculated*
that `test_edbvocab`, `test_mapquery`, `test_minorfiles` and `test_namekeys`
might be Phase 42's doing; none of the four so much as imports `factionclone`,
and 42 touched nothing outside `factionclone.py`, `factions.js` and
`index.html`. **Re-run the full set clean before believing any of it.**

**All 103 suites run one at a time on 2026-09-13 after the Vanilla Redux fixes:
85 fully green, 18 failing.** Every one of those 18 was captured against a
stashed tree in the same session and the failing check **names are identical**
before and after - the one textual difference anywhere is a millisecond count
inside `test_mapterrain`'s failure line. Nothing regressed.
`test_campmap` is 136/141 against 131/136 stashed: the same five DaC-number
failures, plus the five checks of the new section 6b.
`test_parsers` gained 18 and stays green.

**Two things worth knowing about that run.** `Vanilla_Redux` and
`vanilla_kingdoms_uncompromised` are both **marked M2EX** in `config/settings.json`
as of 12:15 on 2026-09-13, which changes how many checks run - a refused mod
skips its section - so the scores are not comparable with the 2026-09-12
numbers further down. And `test_images`, `test_startup` and `test_mapcheck`
each threw `PermissionError: [WinError 10013]` once, on binding a socket; all
three are green on a re-run. It is the machine, not the suite.

**The 2026-09-12 line below - "98 of 103 passed" - was already stale before the
M2EX fix, and the reason is worth keeping.** `vanilla_kingdoms_uncompromised`
is installed, and **six suites tracebacked the moment they reached it**:
`test_campedit`, `test_campaint`, `test_campview`, `test_mapquery`,
`test_regiondel`, `test_stratobj`. All six were confirmed against a stashed
tree, so none of it was the fix - the same `MapError` out of the same line, in
the old wording. The cause underneath was one mistake made six times: **the
skip guard was on `CampaignMap(mod)`, which is lazy and has never refused
anything.** Every refusal those guards were written for comes out of `.index`,
which is read much further down. The guard is now the read in all six, each
one placed where the section actually needs the index - `test_campedit` keeps
its text half running, because (a) and (b) need no index and are the checks
such a file is most worth running.

`test_campview` is the one that is not a guard: `campmap.view` **degrades
rather than raising**, so a map it cannot index comes back as a manifest with
an empty region table. The suite asserted that never happens. It now asserts
what the degraded manifest is for - that its findings say why - and skips the
rest of that mod.

**Three of those six also redirect `config.SETTINGS_PATH` to a temp config
partway through the file** (`test_mapquery`, `test_regiondel`,
`test_stratobj`), which means every mod reads as **unmarked** on that side of
the file whatever `settings.json` says. Each now says so in a comment beside
its guard. It is why marking a mod as M2EX does not make those three read its
map, and it is not a defect - the save test wants a clean config.

**The twelve map suites, run one at a time on 2026-09-13 after the fix, with
no mod marked beyond the one that already was:** no tracebacks anywhere.
`test_campaint` 152/152, `test_campaignmap` 31/31, `test_mapquery` 109/109,
`test_regiondel` 62/62, `test_maplayers` 46/46, `test_campnew` 55/55,
`test_stratobj` 65/65, `test_campfiles` 86/86 all pass. `test_campmap` 102/106
and `test_campview` 58/61 are the documented DaC numbers below. `test_mapcheck`
89/90 is `every finding carries a place to go and look`, which fails the same
way on a stashed tree and has nothing to do with this.

**`replace_record` was eating a blank line per save, and that is fixed**
(2026-09-13, the session after the one that found it). It popped every trailing
blank line off the replacement block while still replacing the record's **whole
span** - and a span runs to the line before the next record's header, so it
includes the blank separator. `vanilla_kingdoms_uncompromised`'s
`descr_regions.txt` puts a blank line after every record, so **all 853 of 853
lost a line when edited**, and a **no-op save reported a change and wrote a
shortened file**, because `plan_region` decides there is nothing to do by
comparing `replace_record`'s output against the file. DaC and Reforged write
their records back to back, which is why the pop never had anything to do.

**What the pop was really carrying is the delete.**
`regiondel` removes a record by handing in `""`, and `_split_lines("\n")` is one
empty line rather than none - so without the pop a delete left a blank line
where the record had been. That is the case, so that is the test now: a block
with nothing but blank space in it takes the whole span out, and anything else
is spliced verbatim. The span itself is untouched; `record_text` is documented
to hand out the comments and blank lines a record carries and that is still
true.

Checked over every record of all three installed maps, not just the two the
suite samples: 1,251 records re-render byte-exact, put back unchanged return the
file's own bytes, and change exactly one line when one field is edited; a delete
still drops the whole span. On the mod itself a no-op save on
`Riba_Raudones_province` now answers **"nothing to change"** and writes nothing.
`tests/test_campedit.py` section 3 has the regression, on a three-record file
written there rather than on an installed mod - it fails on the old code with no
mod present at all.

**All 103 suites were run one at a time after 29 and 98 passed** (2026-09-12).
The five that did not are the four documented DaC suites below, each on its
documented number, plus `test_mapcheck`'s timing bar, which failed at 1,505 and
1,491 ms inside the batch and passes idle at 821, 666 and 165 - exactly the
behaviour that section describes. `test_campstrat` was also re-run against a
stashed tree to confirm its three failures are the mod and not this phase; they
are. `tests/test_stratart.py` is new (40) and covers all five levels of 29 plus
B4.

**The one-second bar in `test_mapcheck` has less headroom than it did.** 23a's
rule put it at about 630 ms on DaC and 23b's second season at about 740. Idle on
2026-09-12 it measures **659 ms on DaC and 329 on Reforged**; in the middle of a
102-suite batch with a graph rebuild running it measured **1,484 and 1,215** and
failed both checks. It is the load that moves it, not the rule - re-run it alone
and idle before believing a failure, and expect it to fail inside a full run.

**Four suites fail the same way on a clean `master`** - hard-coded Divide and
Conquer numbers (77 port pixels, 13,153 newlines, 305 characters, 73,904 sea
tiles) against an installed DaC that is a different build: `test_campmap`,
`test_campstrat`, `test_campview`, `test_stratchar`. Stash and re-run before
believing one of them.

**And a suite that walks the installed mods meets a third map now**, which is
neither DaC nor Reforged and is inside neither's assumptions: 823x337, 856
region colours, blank lines between the records of its `descr_regions.txt`, 7
port pixels the dock rule cannot decide, and religion totals of 95 and 99. A
check written as "every installed mod does X" is a claim about the installed
set, so read a new failure as the mod before reading it as the tool - and a map
this one cannot read is a **skip with its reason printed**, never a traceback.

**Three suites need node**: `tests/test_maplayers.py` (20a),
`tests/test_mapgo.py` (20b) and `tests/test_maplabels.py` (20c). Without node on
PATH each prints a skip line and its Python half still runs.

**Two suites bind a socket and can collide inside a back-to-back run**
(`test_buildings_http`, `test_viewer3d_http`, `WinError 10013`), and **two
one-second timing bars are load-sensitive** (`test_mapcheck`'s rule-set bar,
`test_mapquery`'s warm fact-table bar). Re-run any of the four alone and idle
before believing it.

The other standing trap: the suite leaks `ut_*` temp directories into `%TEMP%`.
And **never `git stash` while a suite is running in the background** - it pulls
the edits out from under it (21 did it once; see the archive).

## Read first
- `ROADMAP.md` - the backlog, the locked decisions, and the campaign map
  reference. Read all of it.
- **`git fetch origin` before anything else.** There is a second person on this
  repo since 2026-09-20 and his work arrives on `origin/master` without notice.
  Check what is new, pull it, and rebase local commits onto it rather than
  merging over them.
- `web/js/map3d.js` - **before drawing anything in 3D on this page, and before
  giving a WebGL context up anywhere.** Two things in it are not obvious and
  both cost a bug: a bare `requestAnimationFrame` never resolves in a tab the
  browser is not rendering, so anything that awaits one can hang forever; and
  `WEBGL_lose_context.loseContext()` does not free a canvas to be drawn on
  again - the element keeps that context and hands the same LOST one to the
  next `getContext`, so a canvas that is reused has to be replaced. The model
  viewer never hit either because it tears its host down with it.
- `web/js/mappin.js` - **before adding a coordinate field anywhere** (20c).
  `cpinButton(what, fn, args)` is the whole of it; 22a's and 22b's forms and
  their three Place buttons use it.
- `campaint.map_campaigns` - **before writing anything to the base map** (B1).
  A write to `world/maps/base` reaches only the campaigns that do not ship
  their own copy.
- `unittransfer/factionaudit.py` - **before adding any check about a faction.**
  `Census` already counts every slot in every file; gap or note is measured on
  the installed mods, never copied from a reference.
- `Registry.map_for` and `campmap.layer_map` - **before a module draws a
  layer.** The engine reads a campaign's own copy of a map file where it ships
  one, and so does the screen; a texture built from the base map's ground layer
  is not Fellowship's.
- `unittransfer/spawns.py` - **before reading a campaign script for anything.**
  Reading one is allowed and writing one is not, which is 19b's refusal and the
  reason this module exists. Two traps are banked in it: a `character` line
  inside a spawn is comma-separated and the `unit` line beside it is not (the
  name runs to the first of `soldiers`, `exp`, `armour`, `weapon_lvl`), and a
  coordinate is the game's y, so `CampaignMap.image_xy` is what indexes a pixel
  with it. A spawn that resolves to no province has exactly three possible
  reasons and all three are real on the installed mods; a spawn with no
  coordinate has none of them and is not resolved at all.
- `campaint.recolour` and `campaint.region_tiles` - **before assuming a change
  to the map renumbers anything.** A region ID is the order a colour is FIRST
  MET in a row-major scan, so it says where a province's pixels are and not what
  colour they carry: creating and deleting a province move pixels between
  colours and do renumber, and a recolour does not, measured at zero on both
  mods. The one recolour that renumbers is a merge into a colour already in use,
  and it is refused rather than warned about. A province is not always one
  connected blob - 8 of DaC's 200 and 10 of Reforged's 199 are not - so the
  whole colour is replaced and never bucket-filled. `_emptied` reads the pending
  record change because the two halves of this save disagree by design until
  both are written.
- `campmap.regions_rel` and `campmap.stale_rwm` - **before writing a region
  record, and before deleting a compiled map.** Which `descr_regions.txt` an
  edit belongs in is the CAMPAIGN's question, not the mod's: a campaign that
  ships its own copy is drawn and judged on it, so a write to the base file is a
  write to a file that campaign never reads. `plan_region` takes the map for
  exactly this reason and passing it nothing still means the base map, so no
  caller had to change. The compiled map beside the file that changed is always
  stale and is listed first, because the campaign list is built from the folders
  carrying a `descr_strat.txt` and a folder holding only map files is not in it.
  Reforged's Fellowship is the installed proof of both halves: its
  `descr_regions.txt` differs from the base in eleven records and its `map.rwm`
  is a different file 14 KB apart.
- `unittransfer/rebelpools.py` - **before adding anything that reads a province
  through a second file.** The reverse join is the whole module and it needs no
  layer, which is why the route asks for a map and never requires one.
  `BY_CATEGORY` is the rule that keeps three correct blocks off the orphan list
  on every mod, and `chance` is the number that decides whether an assignment
  does anything at all - it is in `descr_rebel_factions.txt` and the assignment
  is in `descr_regions.txt`, which is why the panel shows both at once. It is
  also where the ruling lives that a *wrong* assignment is not a findable one:
  nothing dangles on either installed mod, so there is no rule to write.
- `campmap.record_text` and `campmap.replace_record` - **before splicing a
  record back into a file.** A record's span runs to the line before the next
  record's header, so it owns the comments and the blank separator after it;
  hand those back or the file loses a line every save, and `plan_region`'s
  "nothing to change" - which is `replace_record`'s output against the file -
  starts lying. An all-blank block is the delete and takes the span with it.
- `campmap.RegionIndex.labels` and `CampaignMap.uncapped` - **before touching
  the label image, and before writing any check against an engine number on a
  map.** The labels are `bytes` at or under 256 colours and a 16-bit
  `array("H")` over it, so subscript them and never hand the buffer to Pillow -
  `mapquery._paint` and `regiondel._mask` are the two that map through a table
  instead, and they are the pattern. The 510-a-side cap and the 200-colour cap
  are both in the vanilla executable, so both are off on a mod marked M2EX;
  `uncapped` is the one place to ask, and `modflags.CAP_FINDINGS` is the record
  half of the same rule.
- `unittransfer/mapterrain.py` - **before anything needs a layer's colours as
  one byte a tile.** `Vocabulary.texture` is the one place the engine's four
  texture rules are applied; `_index` is the exact colour-to-index pass, in
  Pillow's C and 16x quicker than a dictionary pass, with the slow one kept
  beside it as the reference.
- `Colouring.payload`'s `bands` - **before working out anything per group.**
  Which group each province is in, `-1` for none, absent for anything that is
  not a province. The colour cannot answer it and reading it off the colour was
  a real bug: a presence map's "none" group is painted the same grey a province
  in no group is.
- `tests/test_mapquery.py` section 3b - **the pattern for anything the browser
  draws and Python exports.** Both passes, over one map, in node. It found two
  faults that had been in the tree since 16g, neither of which reading the code
  had found.
- `unittransfer/renames.py`'s `REGION_SITES` and `mentions` - **before anything
  has to follow a province name anywhere.** The site list is the measured set of
  files a province is named in and `regiondel` walks it rather than keeping a
  second one; `mentions` is the whole-mod scan that separates the scripts (which
  are listed and never written) from everything else. Both are the reason a
  delete and a rename cannot disagree about where a name lives.
- `unittransfer/campnew.py` - **before anything writes a folder the engine
  reads.** What a copy of a campaign gets wrong on its own is three things and
  they are all in one place: the compiled `map.rwm`, the `campaign <name>`
  header, and 18a's menu keys being built from the folder name.
- `unittransfer/climatenew.py` - **before adding anything to a file the engine
  indexes by position, and before believing a modding tutorial.** The twelve
  climates are a ceiling `descr_geography_new.txt` enforces by name, so a
  climate is a slot taken over and not a thirteenth entry; `VANILLA_ORDER` and
  `SPARE` are the measured list, and `GEOG_SETTINGS` is the three blocks in that
  file which are not climates. It is also where the rule lives that a declared
  list is never reordered, because the order IS the index.
- `unittransfer/mapsnap.py` - before writing any rule about where something may
  stand. The search is there; hand it the rule and put `near` on the finding.
- `unittransfer/stratobj.py` - one writer for every one-line thing on the map.
- `unittransfer/rawtext.py` - `rtOpen(rel, line)` is how any screen offers
  "open this file as text"; a parser that meets a line it does not model points
  there rather than growing a special case.
- `unittransfer/icons.py`'s `fault` and `png_bytes(strict=)` - **before any
  screen shows a picture that might not be there.** Absent and unreadable are
  two answers now and collapsing them is what Phase 29 undid; absent stays
  blank and stays quiet, unreadable is a fault and only a caller that can say
  so asks for it.
- `cas.texture_path` - **before resolving any art path by name.** A mod's
  packer leaves the named `.tga` at zero bytes and the real DDS beside it as
  `<name>.tga.dds`, so "the file exists" is not "the file has a picture in
  it". 1,171 of the 1,174 zero-byte files on the installed mods are that.

## Upstream
Reference tool reviewed SHA **439aa9b** (2026-09-17), accepted after the diff
was read: **34 commits, 49 files**, against three at the last review. The
manifest is **342 files, none untriaged** - 30 new records were classified by
hand in this pass, including five he pushed while it was being written.

**Two halves, opposite directions.** The asset half is our own `cas.py` and
`mesh.py` transliterated into `m2CasCodec.js` and `m2MeshCodec.js` - same
constant names, same values, `# over the two RGB triples` on the same line -
so those four files are `skip` and there is nothing left to take from his model
code. The map half is his: a spray brush, custom climates he calls M2EX,
a Koppen seeder, and a 3D preview he has just fixed and textured.

**Four gaps filed, none rated**: M18 the map in 3D, M19 climates past the
twelfth, M20 the scatter brush, M21 `texture_density`, plus M16 split so its
playback half can be taken without its editor half. `ROADMAP.md`'s
*2026-09-17 pass* holds the evidence and the three things to send back to him.

**M18 is built (2026-09-20), asked for rather than rated, and the entry
under-read it in one direction and over-read it in the other.** It was filed
as an L; it came in well under, because the two things the entry itself said we
would not have to solve - the textures and the water types - are most of what
makes his file 612 lines. And his sea rule is not one rule but two, where
`mapvocab.is_sea_height` is one and is the measured one. **A fourth thing to
send back to him**, beside the three above: the 2048-step cap he needs because
his heights are the raw `2W+1` TGA is unnecessary on the `fit=tile` view, which
is one pixel a tile at the block centre the engine samples. M19, M20 and M21
are still unrated and still the user's call.

**M21 is the one that may be a defect rather than a feature.** `mapterrain.parse`
drops a root-level `texture_density` line, and if any installed mod declares one
the terrain picture has been tiling at a rate the game does not since 23a.
Measure before building.

## Decisions
- 2026-09-17: **The reference tool is a mirror in both directions now.** His new
  `.cas` and `.mesh` readers are our two modules transliterated, comments
  included, two days after ours were published. Nothing is owed either way and
  the credit in the README stands, but the manifest has to say so: reading his
  model code for format knowledge is reading our own back, and a `port-concept`
  that has become `skip` is a real change to what the mirror is for.
- 2026-09-16: **A default is what somebody does first, every time, before they
  can start.** The settlement names and the terrain textures opened off and were
  turned on at the start of every session on every mod. A switch in that state
  is not a default, it is a chore. The test of one is the first thirty seconds
  of a screen, not what is cheapest to draw.
- 2026-09-16: **What the browser opens on and what an unasked request draws are
  two questions.** Moving `GAP_DEFAULT` with the screen's habit broke six checks
  that are about the drawing rather than the UI, and rightly. The browser sends
  `&gap=` every time, so the two can differ and one of them can stay loud.
- 2026-09-16: **A panel that is always up is a panel paid for on every errand.**
  20a's ruling put the layer stack outside the tabs, which was right, and under
  the tab body, which cost 45% of the column whatever you were doing and lost the
  stack entirely when the column was collapsed. Outside the tabs does not have to
  mean inside the column - the map has a foot.
- 2026-09-15: **Measure the premise, not only the feature.** Phase 30 was
  scoped around "15 pink tiles on DaC, so this is the paint tool"; the installed
  set has changed and one mod now draws 159,855 of them because it has no
  texture folder at all. The feature was right either way, but what it is FOR
  was not. Re-measure a write-up's numbers before building on them - third time
  in six phases.
- 2026-09-15: **A missing folder is one sentence, not one per file in it.**
  Thirty gap rows naming thirty textures all said the same thing and each blamed
  the wrong file. Check the container before the contents, and report at the
  level the fault is at.
- 2026-09-15: **A key on a record is not always that record's own key.** The
  `legion:` line points at another province's name key on 119 of DaC's 199, and
  the first draft of the panel labelled it as this province's third name. A row
  that shows a key has to say whose it is. The same question is worth asking of
  every other line this tool reads as a name.
- 2026-09-15: **Report the file's odd states, do not tidy them.** 58 provinces
  in two music types and 2 named twice in one are what the installed mods
  actually ship; the engine plays one of them either way. The panel says which
  it is and the plan says what saving would resolve, rather than a writer
  silently making the file neat under somebody.
- 2026-09-15: **A control built for a 336px column does not move to a strip
  unchanged.** The five tools were a grid with the glyph over the word and the
  layer picker was `flex:1 1 100%`, both of them right in a panel and both of
  them wrong on a toolbar - the first cost 107px of covered map, the second a
  whole second line. Moving a control means re-deciding its shape, not just its
  parent.
- 2026-09-15: **A habit rides in `cmapLayerState`; a thing somebody is doing
  right now does not.** `paint_row` is in every named view and `p.on` is in
  none, because a preset that arms the brush is a preset that starts editing a
  map. The line is worth stating: the next switch added to this screen has to be
  put on one side of it.
- 2026-09-15: **A control that sizes itself and a width somebody dragged cannot
  both own the same element.** `.cmside.wide` is a class and `splitInstall`
  writes an inline flex, so the inline one wins and the Code View stopped
  widening. `cmapWireSplit` takes the inline width off while a self-sizing state
  is up and puts it back after, which is exactly what `edPrevMin` does in
  `editor.js`. Three callers of `splitInstall` now, one rule.
- 2026-09-15: **"Surface it once" means once per screen, not once per manual
  pick.** Re-arming the automatic tab switch every time somebody chose a tab by
  hand reads as the considerate version and is the annoying one: a person on the
  Paint tab clicking province after province is painting. One switch teaches
  where a click lands; a dot says it every time after.
- 2026-09-15: **A pinned panel has to be capped or it is not pinned, it is the
  column.** The layer stack at its natural height is 794px of an 842px column,
  so "it stays visible whichever tab is up" cost a `max-height` and a second
  scroller. Worth saying out loud because the next pinned thing will be the
  same.
- 2026-09-15: **Checks that read a table do not see the layout.**
  `test_web_modules` was 34/34 green while all six tab groups were showing at
  once, because `.cmgroup{display:flex}` beats the UA sheet's `[hidden]` and no
  check looks at CSS. The browser found it in one screenshot. Run the screen.
- 2026-09-15: **A phase is scoped against the tree, not against the write-up.**
  43 said the toolkit would not write the three rosters; 16j had written them,
  with the radio control and the byte-exact tests, and the four sentences it
  read as missing writers were four guards doing their job. The first move in a
  phase is to run the thing the write-up says does not exist. Second time in
  three phases - 40 withdrew an inferred crash the same way.
- 2026-09-15: **Fatal when the save creates the state, a warning when it only
  reports it.** `camp.no_playable` refuses a roster save that empties the
  playable list and says nothing more than before when the file already arrived
  that way, because the screen that would refuse is the screen that repairs it.
  `check_rosters` gets the before-state as an argument rather than a severity
  flag, so the read path did not have to change at all.

- 2026-09-12: **A file that will not decode is not a file that is missing** -
  now true rather than scoped. `png_bytes` answered both with a 1x1
  transparent PNG, and that conflation is what let the strat model bug through
  four layers. Absent stays blank and stays quiet; present and unreadable is a
  fault, `strict=True` is how a caller asks to be told, and the blank served
  for one is no longer cached so replacing the file is enough to fix it.
- 2026-09-12: **The scoping said the art was packed and it is loose beside the
  stub.** Phase 29's own write-up blamed a `.pack`; the measurement says a
  mod's packer converts each `.tga` to `<name>.tga.dds` and truncates the
  original, and 1,171 of the 1,174 zero-byte files on the two installed mods
  are exactly that pair. `cas.texture_path` took the stub because it *existed*.
  A candidate list ordered by name alone cannot tell a file from a placeholder
  - it has to prefer one with bytes in it. **Reproduce before scoping**: four
  correct diagnoses above a wrong one still leave the bug in place.
- 2026-09-12: **Say what was measured, not what it is blamed on.** The
  temptation was to have the panel announce "this mod keeps its strat textures
  in a `.pack`", which is the sentence the scoping asked for and is not true.
  Nothing here reads a `.pack` index, so nothing here may claim what is inside
  one: `icons.fault` reports the size and the partner file it can see, and
  `factions.no_file_note` counts the archives it can list and says the file is
  not loose. An empty `packs` folder is not an archive - Third Age Reforged
  has one.
- 2026-09-12: **A cut-out rule belongs to the format it was measured on.**
  `if(base.a < 0.35) discard;` is what makes a plume a plume on a unit's
  `.mesh`. Applied to a `.cas` whose sheet came back degenerate it deletes the
  model, and the survivor is whichever mesh had no material at all. A shader
  constant shared between two decoders is a decision about both.
- 2026-09-12: **A delete is a rename to nothing.** 19b measured where a province
  is named - fifteen files in Divide and Conquer, twelve in Third Age Reforged -
  and G1 walks that list rather than one of its own, removing the name where a
  rename would substitute it. The two agree about the campaign script for the
  same reason: it is a grammar nothing here parses, so it is listed line by line
  and never written. A second list of "where a province is named" would have
  been a second list to keep right.
- 2026-09-12: **Land goes whole to one neighbour it touches, and the reason is
  16e's own rule.** Geomod says "usually an adjacent one" and does not say
  which. A tile-by-tile share-out between several neighbours is the obvious
  generalisation and cannot be proved to leave anybody in one piece; one
  adjacent heir can, because two contiguous areas that share an edge make one.
  Offering every neighbour ordered by shared border is the part that is better
  than the arbiter, not the splitting.
- 2026-09-12: **Placed by tile means not orphaned.** Geomod's manual warns that
  "resources, forts and characters will remain" when a region goes, and that
  warning is half wrong: all three carry coordinates, the coordinates do not
  move, and what changes is whose province they stand in. The panel counts them
  and names the heir. The one thing genuinely filed under a province NAME is
  `descr_strat.txt`'s `region <name>` section, and that is the one thing moved.
  `mapsnap.nearest` was expected here by the brief and was not needed - a delete
  moves no coordinate, so no placement rule can be broken by one.
- 2026-09-12: **A new campaign is a copy of one that runs.** The engine reads
  more than a dozen files out of a campaign folder and a missing one is a load
  failure with nothing on screen to explain it, so a template or a skeleton
  would be a way of shipping that failure. What a copy alone gets wrong is three
  things, all of them in `campnew.py`: the compiled `map.rwm` must not travel,
  the `campaign <name>` header must name the copy, and 18a's menu keys are built
  from the folder name so a copy inherits none of them.

Older decisions are pruned into `STATE_ARCHIVE.md` at the ten this file's
contract allows.
