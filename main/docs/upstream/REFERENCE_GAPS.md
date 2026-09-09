# What the four reference tools still do that we do not

Written 2026-09-05, after Phase 16 finished and V3.0.0 became feature-complete.
This is the answer to one question: **with the campaign map editor built, what
is left to take from Demir's tool, Mylae's tool, Bare Geomod and TWMapReader?**

**Nothing here is scheduled.** The user classifies it by priority, and the
classified items become numbered phases in `ROADMAP.md`. Items already scheduled
elsewhere are marked and cross-referenced rather than repeated.

## How this was measured

- **Demir** - `Reference/Map/Demir.html`, "StratMap Forge v0.4", 350 KB in one
  `<script>`. Every top-level `function` name was enumerated and each one
  matched against a module of ours.
- **Mylae** - the upstream mirror at `refs/upstream/editor/main`, SHA `ac503ac`,
  310 files, all triaged in `docs/upstream/PORT_MANIFEST.json` (128 port-concept, 90
  skip, 71 out-of-scope, 21 audit). The port-concept set was walked file by
  file.
- **Geomod** - `The Geomod Manual - 6.18_2012.09.12.pdf`, 35 pages, read in
  full. Its contents list is a feature list.
- **TWMapReader** - the TWCenter thread saved beside the source, which carries
  the author's own feature description and a full change log back to v1.4, plus
  the 304 Java sources.

Then each candidate was checked against this repo rather than assumed: a `grep`
for the file it edits and for the function that would write it. Where an item
says "we do not", that was verified, and the verification is quoted.

## The count

| Source | Items | Already scheduled | Already done, or a duplicate |
|---|---|---|---|
| Demir's StratMap Forge | 14 | 0 | **D4, D5 done 19a** |
| Mylae's M2TW Editor | 17 | 4 (M1, M2, M10, M11) | 2 (M9 we do better, M14 = D11) · **M5, M6, M13 done 18a; M3, M4 done 18b** |
| Bare Geomod | 8 | 1 (G6) | 3 (G7, G8 done; G5 = D9) · **G3 done 18a** |
| TWMapReader | 12 | 1 (T5, folded into 17d) | 0 |
| **Total** | **51** | **6** | **5** |

So **40 genuinely open items**, of which 17d and 17e (M1 and M2) are the two
already written into Phase 17.

Sizes are S (part of a session), M (a session), L (more than one). They are the
cost of doing it *our* way - one engine, byte-exact round trip, a test suite -
not the cost of copying the reference.

---

# 1. Demir's StratMap Forge

The deepest campaign-database editor of the four and the source of most of
Phase 16's validation rules. Fourteen things it does that we do not.

### D1. Change a region's colour · M

`changeRegionRgb`, `randomizeSelectedRgb`, `makeRandomSafeRgb`. Picks a new RGB
for a province, repaints every pixel that carried the old one, and rewrites the
record. **We refuse this outright**: 16d's region form declines the colour field
"because the colour is the map's own pixels", and the paint tool can only reach
those pixels one brush stroke at a time.

Doing it properly is more than a fill. The new colour must not collide with
another region, with the two marker colours, or with whatever the mod uses for
sea; region IDs are the order of first appearance in a row-major scan, so a
recolour that moves a province earlier or later **renumbers every region after
it**, which 16e already warns about when a province is created. `campaint`'s
undo is a pixel-delta stack and would hold the whole change, so the machinery is
there.

### D2. Rename a region or a settlement everywhere · M

`renameRegionReferencesEverywhere`, `regionReferenceRepairTarget`. **We refuse
this too**, and say why in three places at once: the name is a key that
`descr_strat.txt`, the win conditions, the campaign script and every `legion:`
line point at.

The refusal is honest but it is not the same as being unable to do it. The
follow-every-reference work is already written elsewhere in this toolkit -
`unitrefs.py` and `factionclone.py` both walk a name across a dozen files - and
`winconds.py` and `campstrat.py` own two of the four files a rename has to
touch. What is missing is the campaign script, which is a scripting grammar
nothing here parses, so a rename would have to report that file rather than edit
it. Say so, and the feature is still worth having.

### D3. Rename a faction everywhere · M

`renameFactionEverywhere`. Same shape as D2 over a wider file set. 15g's
`factionclone.py` already knows all twelve files that name a faction slot, plus
the three that name it as a judgement and are reported rather than edited, so
this is that module's list read in a different direction.

### D4. Write the localisation key when a region or settlement is created · **done**

`stageRegionLocalization`, `setLocalizationValue`, `localizationTargetPath`,
`hasLocalizationKey`, `rebuildLocalizationIndex`. A new province needs an entry
in `text/imperial_campaign_regions_and_settlement_names.txt` or the game shows
its code name.

**We read that file and never write it.** `campmap.shown_names` parses it for
the panel, 16f reports a missing key as a finding, and 16e's new-province wizard
creates a province that will have one. Geomod writes it too, and the toolkit
already owns a UTF-16 writer with a BOM (`strings.py`, `stringsbin.py`) and the
`.strings.bin` recompile beside it. This is the smallest genuinely missing piece
in the whole audit and it closes a finding the validator currently reports
against our own output.

**Done 19a**, in `unittransfer/namekeys.py`, and the wizard now writes it in the
same backup set as the record it creates. Measured: 400 keys in Divide and
Conquer and 398 in Third Age Reforged, covering every region and settlement in
both, so a missing one is a record something built.

### D5. Name pools for a new character · **done**

`parseDescrNamePools`, `populateCharacterNameSelectors`,
`resolveCharacterNameParts`, `ensureCharacterNameInFaction`,
`stageNamePoolLocalization`, `syncCharacterNameSelectors`. When you add a
character, the first and last name are chosen from the faction's own pool in
`descr_names.txt`, and a name that is not in the pool is added to it.

16i writes characters and takes the name as free text. `descr_names.txt` is
already read and edited by `minorfiles.py` and already cloned per faction by
`factionclone.py`, and 16j-2 deliberately did not add a third copy of it - so
this is `stratchar.js` calling the module that already owns the file. It also
removes a class of fault: a character whose name is in no pool has no localised
name in game.

**Done 19a**, and it turned out to be two files rather than one: 3,583 of Divide
and Conquer's 3,583 pool names and 2,572 of Third Age Reforged's 2,573 have a
key in `text/names.txt`, and a pool entry without one shows the raw token in
game. The one exception is the word `surnames`, which is `descr_names.txt`'s
fourth section heading and which `minorfiles.NAME_SECTIONS` was reading as a
name - corrected in the same phase, on Demir's and TWMapReader's word.

### D6. Faction dependency audit · M

`factionDependencyAudit`, `factionAuditHtml`, `factionRepairCandidates`,
`stageDependencyText`, `showFactionAudit`. One screen answering "is this faction
complete?" across every file that should mention it, with a repair offered per
gap.

We have the pieces and not the screen: `factionclone.py` knows the twelve files,
`mapcheck` and `factions.py` both report per-file faults, and Home reports
per-mod readiness. What is missing is the per-faction view.

### D7. Textured terrain render · L

`buildTerrainCanvas`, `buildProceduralTerrainCanvas`,
`loadGroundTexturesInBackground`, `parseAerialGroundTypes`. Draws the map with
the game's own aerial-map ground textures instead of flat legend colours, so it
looks like the campaign map rather than a data layer. **TWMapReader does the
same thing and does it better** (see T1), so treat them as one feature with two
implementations to compare.

We know where the textures are - `mapvocab.py` already cites
`descr_aerial_map_ground_types.txt` - and `cleaner.py` walks `aerial_map`. What
is missing is the compositing: one texture per (climate, ground type) pair,
tiled, blended at the seams. It is the most expensive item in this document and
the most visible.

### D8. River overlay · S

`buildRiverOverlayCanvases`, `updateRiverOverlayControl`. Rivers lifted out of
`map_features.tga` and drawn as their own toggleable overlay with their own
colour, instead of being three colours inside a features layer that is 97.7%
black.

16d already punches the blank colour out of `map_features.tga` and makes it an
overlay, and 16f already builds the four-connected river graph to find rejoins.
This is those two facts joined into a control.

### D9. Place, move and delete strat objects on the map · L

`insertStratObject`, `deleteStratObject`, `openObjectDialog`,
`saveSelectedObject`, `locateObject`, `nearestStratObject`, `populateObjectLists`,
`insertRegionObject`, `removeSelectedObject`. Click the map to add a fort, a
watchtower or a trade resource; drag one to move it; delete one.

**This is the largest single hole in our campaign editor.** 16b reads forts,
watchtowers and resources - 105 forts, 295 watchtowers and 1,131 resources on
DaC, each with its line span - and nothing writes them. `stratchar.py`'s
`UNTOUCHED` tuple names all three as things a character save may not touch,
which is the guard working correctly around a feature that does not exist.
Geomod (G5) and TWMapReader (T4) both have this too, so it is the one gap all
three of the map tools fill and we do not.

### D10. Snap to a legal position · M

`nearestValidSettlementPixel`, `nearestFreeCharacterPosition`, `nearestMapTarget`,
`nearestRegionForMarker`, `settlementTileProblemAtImage`. When a placement is
illegal, offer the nearest tile that is not.

We have the predicate and not the search: `mapcheck.marker_faults` is the single
copy of the four marker rules and `campaint` calls it for the new-province
wizard. Turning "no" into "no, but here" is a spiral search over that predicate.
Pairs naturally with D9 and with 17d's drag-to-move.

### D11. A raw text editor for the campaign files · S

`loadRawFile`, `saveRawFile`, `populateRawFileSelect`, `refreshKnownText`,
`rawKnownText`. Pick any file the tool knows about and edit its text directly,
with the tool's own backup and undo around it.

Our Code View is per record, not per file, and deliberately so. A whole-file
editor is a different thing and is the escape hatch for the case every editor in
this toolkit eventually meets: the mod does something the parser does not model.
Mylae has the same feature as a page (`TextEditor.jsx`, M14).

### D12. Export the project as a zip, and load one back · M

`exportProject`, `loadProject`, `saveProjectToMod`, `zipStore`, `crc32`,
`downloadBytes`. Everything the tool has touched, packaged, shareable, and
importable into another copy.

`pack.py` already does exactly this shape for units, including the import side
and the conflict report. A campaign or map package is the same machinery over a
different file list.

### D13. Generate a horde start for a new faction · M

`hordeStartPositions`, `hordeCharacterNames`, `factionHordeConfig`,
`buildStartingFactionStrat`, `populateNewFactionHordeOptions`,
`syncNewFactionHordeMode`, `uniqueTemplateLeaderName`. A new faction that
appears as a horde needs no settlement, but it does need spawn positions,
characters and the horde keys.

16j-2 creates a faction with the donor's AI, label, purse and diplomacy and
**nothing else** - no settlement, no character, no coordinate - and says so,
because that is the shape vanilla's Mongols and Timurids already are. The horde
keys themselves are already editable in Phase 11's faction editor. This is the
missing half: the tool filling in the start rather than the modder.

### D14. A campaign browser · S

`renderCampaignBrowser`, `renderCampaignChooser`, `renderCampaignDetail`. A
screen listing every campaign in the mod with what is in each one, before you
pick one.

We have the picker (`campstrat.campaigns` lists every folder that really has a
`descr_strat.txt`, and every map route takes `&campaign=`) and not the browser.
Cosmetic, and cheap, and the kind of thing that makes a mod with six campaigns
navigable.

---

# 2. Mylae's M2TW Editor

The tracked upstream. Seventeen items; five are already scheduled.

### M1. Strat overlay: markers for everything with a coordinate · **scheduled**

`StratOverlay.jsx`. **Phase 17d.** See `ROADMAP.md`.

### M2. Pixel tooltip on hover · **scheduled**

`MapPixelTooltip.jsx`. **Phase 17e.** See `ROADMAP.md`.

### M3. `descr_events.txt` editor · **done**

`CampaignEventsTab.jsx` (419 lines) + `campaignEventsParser.jsx`. The historical
events a campaign fires: their dates, their text keys and their conditions.

**Nothing in this repo touched that file** - verified by grep across
`unittransfer/` and `web/js/`. It was explicitly kept in scope during triage
(`docs/upstream/SYNC_LOG.md`: the thing ruled out was the *script* editor, which is a
different feature) and then never built. Geomod writes this file too.

**Landed in 18b** (2026-09-07), as a panel on the campaign map screen, because
the `position` lines are the half of it that needs a map. It is **not**
`flatrecord`-shaped and the claim above that it is was wrong: `flatrecord` reads
a run of `<head> <name>` records with `keyword value` lines and this file's
keywords repeat - one event may carry four `date` lines and thirty-seven
`position` lines. Two things measuring corrected in the reference: their parser
holds a single `date`, so the three extra ones are lost, and their category list
is the *disaster* list, missing `counter` and `emergent_faction` - which the
game's own file header names, and the second of which is how a faction enters a
campaign.

### M4. `descr_disasters.txt` editor · **done**

`DisastersTab.jsx` (222 lines) + `disastersParser.jsx`. Eight event types
(earthquake, volcano, flood, storm, dustbowl, locusts, plague, horde), each with
a frequency, a season pair, a warning flag, repeatable climate / region /
position lines, and a min and max scale.

Not touched here either. The `position x, y` lines make it a map-editor feature
rather than a minor-files one: a disaster has coordinates, so it belongs with
D9's placeable objects.

**Landed in 18b** (2026-09-07), in the same panel. The file is under
`world/maps/base` with the layers rather than in the campaign folder - one map
has one set of disasters however many campaigns are painted on it. Both
installed mods ship it **empty**, so the format arbiter is the game's own
unpacked copy, which documents itself in its own header. Two more corrections
there: their serialiser writes every key, and vanilla's `plague` block has no
`warning` line, so the first save of any block in the file would add one; and
vanilla's `storm` and `horde` both write `region the sea`, which is not a region
in `descr_regions.txt` and never will be, so a region rule that did not know
that would report the shipping game as broken.

### M5. Campaign description strings · **done**

`CampaignDescriptionsStrings.jsx` (312 lines) + `CampaignDescriptionsEditor.jsx`.
The title, blurb and victory text a campaign shows on the menu.

`modfiles.py` knows the `campaign_descriptions` file exists; nothing edits it.
Small, self-contained, and the last unedited file in the campaign folder now
that 16j-2 took `descr_win_conditions.txt`.

**Landed in 18a** (2026-09-07), on the faction screen. The keys are built from
the campaign folder's name and the faction's rather than listed, so a faction the
file has never mentioned still gets a form. There is no "victory text" in this
file in either installed mod - that claim above was wrong, and a campaign's
victory terms are `descr_win_conditions.txt`, which 16j-2 already writes.

### M6. Faction movies · **done**

`factionMoviesParser.jsx` (55 lines). The intro and victory movies per faction.
Not read here. Tiny; belongs with the combined faction screen in 17f.

**Landed in 18a** (2026-09-07), on that screen. It is `descr_faction_movies.xml`
and it is in the campaign folder, not a `.txt` under `data/` - and neither
installed mod's copy ends with a newline, which is why it is a line splice and
not the reference tool's serialiser.

### M7. Import a campaign from another mod · L

`campaignImporter.jsx` (224 lines). Take a whole campaign folder out of one mod
and bring it into another, resolving what the destination does not have.

This is Unit Transfer's problem at campaign scale, and `transfer.py` is the
model: a plan that names every missing faction, region, unit and building before
anything is written. Large, but the discipline already exists.

### M8. Pick an X,Y off the map into any form field · S

`PositionPickerButton.jsx` (49 lines). A pin button beside a coordinate pair that
puts the map into pick mode and writes the clicked tile back into the field.

Every coordinate in `stratedit`, `stratchar` and D9's object dialogs is typed by
hand today. This is one shared control that makes all of them clickable, and it
is small. Good value.

### M9. Region colour detector · S

`RegionColorDetector.jsx` (210 lines). Reads the colours actually present in
`map_regions.tga` and reconciles them with what `descr_regions.txt` declares.

**We already do this better** and this entry is here to record that. 16c's sea
heuristic and 16d's legend census both do the census, and 16f reports the four
undeclared classes by name with a measurement behind each. Listed as an audit
item, not a port: read his file once for anything the rule set misses, then
close it.

### M10. OSM backdrop and region search · **scheduled**

`OsmBackground.jsx`, `OsmRegionSearch.jsx`, `CoastlineTracer.jsx`. **V3.1**,
opt-in and off by default.

### M11. Overlay and layer generators · **scheduled**

`OverlayMapGenerator.jsx`, `BboxLayerGenerator.jsx`, `FeaturesLayerGenerator.jsx`,
`autoGroundTypes.js`, the Köppen and land-cover fetchers. **V3.3.**

### M12. Bulk faction duplicate, and faction zip export · M

`factionBulkDuplicate.js`, `DuplicateFactionModal.jsx`, `FactionZipExport.jsx`.
Clone several factions in one pass, and export one faction's whole file set as a
zip.

15g's `factionclone.py` does one faction across twelve files with one transfer
id. The bulk half is a loop over it with one plan; the zip half is `pack.py`'s
machinery over the faction's files. Both are extensions of things that exist.

### M13. Guild editor · **done**

`GuildEditor.jsx`, `GuildsParser.jsx`. `export_descr_guilds.txt`.

We **validate against** that file - `buildings.py` refuses a `guild_` requirement
the file does not declare, and says so with the count - and cannot edit it. A
small `flatrecord`-shaped file, and the asymmetry (we know it well enough to
refuse, not well enough to fix) is the argument for closing it.

**Landed in 18a** (2026-09-07) as its own sub mode beside Traits and
Ancillaries. Only the definition half is flat-record shaped; the file could not
be read through `flatrecord` at all, because `Guild` opens a definition AND
names an effect inside a trigger. That collision was also a live bug in
`triggers.py` - every guild trigger ended at its own first effect - and the fix
is `triggers.DEFINITION_WORDS`. Running the check it exists to run found that
Divide and Conquer awards guild points to two guilds it never declares.

### M14. A raw text editor · S

`TextEditor.jsx`. Same feature as D11; count it once.

### M15. Campaign manager: create a new campaign · M

`CampaignManager.jsx`, `CampaignForm.jsx`, `CampaignCard.jsx`. Make a new
campaign folder from an existing one.

Every file in that folder now has a writer here (16h, 16i, 16j-1, 16j-2 and
`winconds.py`), so what is missing is the folder-level operation and the plan
that says what a new campaign inherits.

### M16. Animation editor and asset converter · L, unscoped

`AnimationEditor.jsx`, `CasAnimParser.jsx`, `SkeletonViewer.jsx`, `PoseEditor.jsx`,
`skeletonPoser.js`, `slerpUtils.js`, `AssetsConverter.jsx`, `ms3dCodec.js`,
`textureCodec.js`.

Currently `out-of-scope` in the manifest, and worth re-examining now rather than
before: 15a decoded `.mesh` down to the bone table and 16k decoded `.cas`
including its skeleton, its parent table and its five chunk kinds. The two
formats these pages need are both read here now. This is not a recommendation to
build it, only a note that the reason it was excluded has changed.

### M17. Export and validation dashboard · M, unscoped

`ModValidator.jsx`, `ValidationDashboard.jsx`, `TriggerValidationPanel.jsx`,
`Export.jsx`, `CampaignPackagePicker.jsx`. One screen running every check over
the whole mod at once.

Out of scope in the manifest. We have more validators than he does and they are
scattered across eight modules with no single door. Home's readiness report is
the nearest thing.

---

# 3. Bare Geomod

The format arbiter, and the tool most of Phase 16's rules were checked against.
Eight items; two are already scheduled.

### G1. Delete a region · M

The manual: "click the name of the region, then click Delete, and all work on
that region including itself will be gone. The area of the former region will
automatically be allocated to an existing region, usually an adjacent one."

**We create regions and cannot delete one** - verified: nothing in `campaint.py`
or `campmap.py` deletes a record or reallocates its tiles. 16e's wizard is the
whole other half of this and its rules apply unchanged, including the one that
refuses to leave any region with no tiles. Note the manual's own caveat, which
is a validation opportunity rather than a limitation to copy: "resources, forts
and characters will remain" - ours should say what is about to be orphaned, and
16f already has every rule needed to find them.

### G2. Region music · S

`descr_sounds_music_types.txt`: which music plays when you fight in this
province. `mapquery.py` reads the file (`MUSIC_REL`) to answer a query and to
skip a filter when it is absent; the region form does not offer it. One more
field on a form that already writes seven, spliced into the line it came from,
exactly as 16d does the rest.

### G3. Region mercenary pool · **done**

Which pool from `descr_mercenaries.txt` this province draws on. The roadmap has
carried this as "data layer lands in 16b, UI deferred" since the phase was
scoped, and the data layer did land. One picker.

**Landed in 18a** (2026-09-07), on the region panel, reading 16b's parser and
adding the write. No province is in two pools in either installed mod, which is
what lets it be a single choice.

### G4. Legion label, with its name dialog · S

`descr_regions.txt`'s `legion:` line, and the small editor Geomod puts behind it
for creating the label and its display name together.

16a made the `legion:` form a first-class case (197 of DaC's 198 records use it)
and 16d edits the field. What is missing is the paired display name, which is
D4's localisation write in miniature - do them together.

### G5. Place resources, forts and towers · **see D9**

Geomod's Resources and Towers-and-Forts sub tabs, including "Localize", which
draws a shrinking circle onto the item so you can find it on a large map. Same
feature as D9; the Localize animation is worth taking on its own, because
`mapcheck` and `mapquery` both already centre the map on a tile and neither
tells you where your eye should land.

### G6. Map resize · **scheduled**

"Add surface area and automatically write the new coordinates into
`descr_strat.txt`." **V3.2**, with the manual's own warning that shrinking needs
the area emptied by hand first.

### G7. Information maps · **done**

Nine fixed maps plus one per hidden resource, religion and trade resource.
Landed in 16g at 93 colourings on Third Age Reforged.

### G8. Debugger, and BinEditor · **done**

The three debugger actions are 16f, including the ambiguous-altitude fix that
finds the Ragusa port bug in the stock game. The BinEditor is `stringsbin.py`
and the Strings module.

---

# 4. TWMapReader

The reverse-engineered engine behaviour, and by some distance the best *viewer*
of the four. Twelve items; one is scheduled.

### T1. Textured map view, summer and winter · L

"The textures (summer/winter) map options display the map using the appropriate
texture TGAs for the tiles' climates and ground types." Read from
`data/terrain/aerial_map/ground_types`, with a missing texture reported in the
Errors tab and drawn pink rather than skipped silently.

Same feature as D7, and this is the better specification of the two, because the
pink-for-missing rule is exactly the toolkit's own "a rule with no evidence
reports nothing" applied to a picture. The winter set doubles it for free.

### T2. Heights, drawn as transparency · S

"A variation of the Heights map, such that darker = more transparent." Meant to
be laid over the textured view, and the author's own note is that the
combination is what makes it readable.

Cheap once T1 exists, and cheap even without it: our heights layer is already
served at one pixel per tile with its own opacity control.

### T3. An FE zoom, for authoring `map_FE.tga` · M

The faction-selection map is a different size from every other layer. His "FE"
zoom keeps it at its native size and scales everything else down to meet it, so
a faction-selection map can be traced and saved with no resampling at all: "no
loss of quality due to scaling up and then scaling down again."

We serve `map_FE` and say `aligned: false` rather than pretending it lines up,
which is correct and is where we stop. This turns that honest refusal into the
one workflow the layer exists for, and it pairs with 16g's per-faction TGA
export, which already writes one file per faction.

### T4. Settlement names on the map, placed to avoid overlap · M

Names beside the markers, shifted around each other so they do not collide, with
font size and marker size held constant across zooms. His own assessment: "its
intelligence is fairly limited but the results are better than none at all."

17d is the markers; this is the labels, and it is the harder half. Worth
separating so 17d is not blocked on it.

### T5. Trade resources drawn with the game's own icons · **part of 17d**

Reads the TGA icons from `data/ui/resources`, falls back to the parent game for
a mod that ships none, and shows nothing rather than an error when neither has
it. Plus a "show only" list to filter to one resource at a time.

Folded into 17d, which already carries the icon rule. The "show only" list is
the part to remember: on DaC that is 1,131 markers, and one resource at a time
is the only usable view.

### T6. Export every tile as text · M

The Export tab: tab-delimited rows, one per tile, with coordinates in both
systems, region, settlement, ground type, feature (which overrides ground type
when present), climate, height, and an extended mode adding RGB values and the
sea flag.

**We export pictures and never numbers.** 16g writes TGA information maps into
the cache; there is no tabular export anywhere in the map editor. `mapquery`'s
fact table is exactly the join this needs and answers a 199-province query in
0 ms, so the work is a serialiser and a route, not a new read. His own warning is
worth keeping in the UI: a big map will pass a spreadsheet's row limit.

### T7. Spawn export, including from the campaign script · M

The Spawns sub-tab "lists all spawn location information, including starting
characters (`descr_strat.txt`) **and spawned ones (`campaign_script.txt`)**."

The second half is the interesting one. Nothing here parses the campaign script,
and it is named in three places as the file a rename or a region delete cannot
follow (D2, G1). A read-only scan for spawn coordinates is a much smaller job
than a script parser and it closes part of that hole.

### T8. Find a region, settlement or region ID · S

The Find tab: type a name or an ID, and the result is shown on the map.

`mapquery` has 24 filters and can already answer "which province is this", and
`mapcheck` and `mapquery` both centre the map on a tile. What is missing is the
one-box search, which is a different thing from a filter panel: it is what you
reach for when you know the name.

### T9. Named view presets · S

The `.mps` state files: any number of saved view configurations - which layers,
which opacities, which colours, which highlight - each named, listed and
loadable, and portable between installs by copying the file.

16d remembers **one** layer stack in `map_layers` on `/api/settings`, per user
rather than per mod, with a reconcile against the manifest so a saved order is
never trusted blindly. That reconcile is the hard part and it is done. This is
the same store keyed by a name, plus a picker. The nine `.mps` files shipped
beside the tool in `Reference/Map/TWMapReader_source/TWMapReaderApp/` are the
author's own working set and are worth reading as a list of what people actually
want to look at.

### T10. Copy the view, or what is under the cursor · S

Copy to clipboard: the current map display, the coordinates under the cursor,
and the region and settlement names under the cursor. Save the display as PNG
(keeping transparency) or TGA (flattening it to an alpha channel). Plus
`SHIFT+X` for coordinates in `x 23, y 284` form, which is the form
`descr_strat.txt` wants them in.

Nothing in the map editor reaches the clipboard; `sprites.js` is the only module
in the toolkit that does. The shift-X detail is the one to take: it is the
difference between a coordinate you read and a coordinate you paste.

### T11. Toggle layers with the number keys · S

"The maps can be toggled on/off by using the number keys 1..0. This can be
useful when you wish to switch to another map without losing your mouse position
and the info being displayed for that tile."

The reason is the feature. `campmap.js` has one `keydown` handler already, and
ten layers is exactly ten keys.

### T12. Region highlight: tint, and border styles · M

Three things his highlight does that 16g's themes do not: an **HSB tint** that
colours a region without painting over it, so the layer underneath still reads;
a **border render type** with an "inside" option; and **borders on all regions**
rather than only the highlighted ones.

16g draws political borders by comparing the group each region is in, which is
the right rule and gives clean frontiers. The tint is the one to take: our
colourings replace the region layer, and his does not, and on a textured
backdrop (T1) replacing it is exactly wrong.

---

# What this adds up to

Four clusters, if the 51 items are grouped by what they are really about:

1. **Placing things on the map** (D9, D10, G5, M4, M8, and 17d) - the largest
   hole, present in all three map tools, and the one where our data layer is
   already complete and simply has no writer. Forts, watchtowers, resources and
   disasters all have coordinates and none of them can be moved.
2. **Making the map look like the campaign map** (D7, D8, T1, T2, T12) - texture
   rendering, the river overlay, the heights wash, the tint that does not
   overwrite. Expensive, entirely visual, and the difference between a data
   layer and a map.
3. **Names and references** (D1, D2, D3, D4, D5, G4) - renaming a thing across
   every file that points at it, and writing the localisation key when a thing
   is created. We refuse most of this today, honestly and with a reason, and the
   machinery to stop refusing is mostly written.
4. **Getting data back out** (T6, T7, T9, T10, T11, D12, D14) - tabular export,
   the clipboard, saved views, keyboard toggles. Individually small, and
   together they are most of what makes TWMapReader pleasant to use eleven years
   after it was written.

The five files nothing in this repo reads at all: `descr_events.txt`,
`descr_disasters.txt`, `descr_faction_movies.txt`, `export_descr_guilds.txt`
(validated against, never edited) and `campaign_script.txt` (named as an
obstacle three times, never parsed).
