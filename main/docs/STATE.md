# STATE - Medieval 2 GUI Toolkit
_Updated: 2026-09-14 - **v2.3.2** is the latest 2.x and **beta 2026-09-12c**
the latest beta - after the M2EX map-ceiling fix, the `replace_record` blank
line it turned up, the two bugs a second report brought in, and **Phases 40, 31
and 42**, all committed and **not cut**. **Releasing is on-request only**:
commit to master and stop_

## Next up
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
blocks are done. Twenty sessions in all; **29, 40, 31 and 42 are done**, so
sixteen are left and three of those are subreleases.

**Block one, the campaign map** - ~~29~~, ~~40~~, ~~31~~, ~~42~~, **41, 43**,
28a, 28b, 33, 30, 34, 35, 36, 37a, 37b, 38.

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

**Start with 41, then 43.** 41 is Mylae's names merge. 43 is the playable / unlockable /
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
`--latest` (latest **v2.3.2**, 2026-09-12). **Campaign-map** -> the **beta
line**, uploaded as a **pre-release** (latest **beta 2026-09-12c**). A
**subrelease means both**: one job, both zips, same tree.

The switch is **one flag**: `off:true` on the `campmap` entry in `MODES` in
`web/js/core.js`, which `menuModes()` and `modeOffered()` are the only readers
of. It is a **release-time edit, not a state of `master`**: set it, bump the 2.x
number, build, upload, then put it straight back off in the next commit.
`master` carries the map ON, and `__version__` says `beta-2026-09-12c`
because the beta was the last thing cut.

Of the finished work, **21 and 29 belong to BOTH lines** (raw text is a menu
mode of its own, the faction audit also draws in the Factions mode, and 29's
`icons.png_bytes` is the unit editor's and the BMDB browser's route as well as
the viewer's) and **22a, 22b, 22c, 23a, 23b and 24 are map work**, beta only.
Of the fourteen sessions left, **two are subreleases**: 38, because
`descr_campaign_db.xml` is a data file and gets a mode of its own; and 39,
because the EDU half of the ceilings is the unit editor's. The other twelve are
the beta alone.

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
| 29 + B4 - the strat model viewer | **done** | Closed 2026-09-12, committed, **released 2026-09-12** as v2.3.2 and beta 2026-09-12c. The scoping was wrong about the root and right about everything above it: the art is not in a `.pack`, it is loose beside the stub as `<name>.tga.dds`, and `cas.texture_path` took the zero-byte `.tga` because it existed. Fixed at all five levels. New: `cas._has_bytes`, `icons.ArtUnreadable`, `icons.fault`, `png_bytes(strict=)`, `/model_texture` 415, `factions.packs_beside`, `factions.no_file_note`, and in `viewer3d.js` `uCutout`, `v3Degenerate`, `v3AskWhy`, `v3TexFault`, `v3FaultRows`. `tests/test_stratart.py` (40). |
| 42 - the art a clone does not get | **done** | Closed 2026-09-14, committed, **not cut** (both lines when a cut happens). The copier was never at fault and the re-measurement held; what was missing was a sentence. `ART_PLACES` is the nine places a faction's art lives, `art_gaps` names every one the clone came away from empty-handed with one of four reasons - the donor has none either, the destination already exists, a longer-named faction owns the name, the mod has no such folder. The old whole-scan warning fires only when the scan is completely empty, which on a real mod it never is. **121 donor slots swept over four mods: 253 empty places, 50 clean donors, and all 253 the same reason.** Not one of Reforged's 30 factions fills every place; `vanilla_kingdoms_uncompromised` is worst at 146. The scoping was wrong about one fact: Reforged's `fe_symbols_80` is **empty**, and the 17 vanilla-named files in it are DaC's. New: `ArtPlace`, `ART_PLACES`, `art_gaps`, `_asset_hits(skips=)`, `ClonePlan.art`, `payload()["art_gaps"]`, the `.fcgap` rows in `factions.js` and the places named in the apply confirm. `tests/test_factionclone.py` 74/74 (was 64), `tests/test_factionclone_apply.py` 39/39 (was 30). **Open:** the reporter's own mod is still unknown, so the end-to-end reproduction against the report itself was not done. |
| 31 - two river rules and a ford in the sea | **done** | Closed 2026-09-13, committed, **not cut** (beta only). Three rules and one repair: `river.fourway` (river on all four sides), `river.no_source` (a four-connected component with no white source), `feature.ford_in_sea` (own altitude sea **and** four neighbours sea - the second half the scoping did not have, and without it the message and the repair are not true). All three find **nothing on any of the five installed maps**, which is what they are for. `ford_none` is the one repair with a safe answer; the other two need the map author's intent or `map_heights.tga`, and both refusals are written into `FIXES`. New: `_r_river_fourway`, `_r_river_no_source`, `_r_ford_in_sea`, `_plan_fords`, `FIXES["ford_none"]`. The three existing river fixtures painted sourceless courses and now paint their source. No web change - the panel is data-driven off `RULES` and `rep.fixes`. `tests/test_mapcheck.py` 104/105. |
| 40 - the new province the engine cannot read | **done** | Closed 2026-09-13, committed, **not cut** (both lines when a cut happens). Four defects, one of them the scoped one. `campaint.new_record_lines` and `campmap.render_block` both produced the eight-line record, the second by dropping the line when the last resource was cleared; both write `none` now, which is what vanilla writes on 18 of 112, Vanilla Redux on 78 of 252 and `vanilla_kingdoms_uncompromised` on all 853. `none` read as a resource name was 931 false findings across two mods. And the indent reading lost DaC's ` Erebor_Province` to a stray leading space - **200 regions read as 199**, 517 painted tiles declared nowhere, and its settlement marker written into the source and a test as DaC's one orphan. New: `campmap.file_shape`, `campmap._resplit_runs`, `check_record(rec, vocab, shape)`, a `parse_block` retry for an indented name line. The inferred engine crash is **withdrawn**: DaC ships a short record and plays. `tests/test_campaint.py` 4c and 4d (185), `tests/test_campmap.py` 1 (+7), `tests/test_campedit.py` (139). |
| 28-43 - the rest of the 2026-09-12 review | **scoped** | Sixteen sessions in two blocks, 40, 31 and 42 having closed. **Block one, the campaign map:** 41 merge one faction's name pool, 43 playable/unlockable/nonplayable, 28a the right menu as a tab strip with Validate one of them, 28b the paint controls over the canvas and a tooltip that holds still, 33 T10 + G2 + G4 in one session, 30 the pink as a choice, 34 add a climate zone, 35 rebels right in place, 36 D1 region colour, 37a T7 spawn export, 37b T3 FE zoom, 38 `descr_campaign_db.xml`. **Block two, the mercenaries:** 32a `mercpools.py` takes the format over from `mapquery.parse_mercenaries`, 32b the two directions with the four gates resolved, 32c five rules and one repair, 39 the engine ceilings. Write-ups and the order table in `ROADMAP.md`. |
| 44-48 - the pass over Mylae's non-map screens | **scoped** | Six sessions, added 2026-09-13 at the user's request, in neither block and every one a subrelease on both lines. 44 the EDB's tree checked (his is the one validator he has and we do not), 45 the `hidden_resources` line, 46 cultures on a mode of its own with a four-tab form and the faction form on the same strip, 47a the six `export_descr_sounds_*` files on `sounds.py`'s own parser, 47b the 32 `descr_sounds_*` scripts on a grammar nothing here reads, 48 add and remove on the strings screen. Two of the seven things asked for produced no phase and a measurement instead: his traits and ancillaries have not moved since 2026-03-27, and his `.strings.bin` codec is wrong where ours is right. |
| 24 - Make and unmake | done | Closed 2026-09-12, committed, **released 2026-09-12**. Closes G1, M15 and the roadmap. Deleting a province, with its land going whole to a neighbour it borders and its name coming out of every file 19b measured - and the campaign script listed, never written, for the reason a rename gives. Making a campaign, as a copy of one that works minus the compiled map, with its own header and its own menu keys. New: `unittransfer/regiondel.py` (`heirs`, `campaigns_reading`, `standing_on`, `plan`, `apply`, `view`), `unittransfer/campnew.py` (`sources`, `plan`, `apply`, `view`), `mapquery.drop_music_region`, `renames.mentions`, `campfiles.write_descriptions`, `GET /api/map/region_delete`, `POST /api/map/region_delete_plan\|_apply`, `GET /api/campnew`, `POST /api/campnew/plan\|apply`, `web/js/regiondel.js`, `web/js/campnew.js`. `tests/test_regiondel.py` (62), `tests/test_campnew.py` (52). |
| B2-B3 - from the beta | scoped, unscheduled | Delete a settlement and move one between mods; one-file insert and export. B4 went out inside 29. |
| 25-27 | scoped, unscheduled | OSM backdrop, map resize, layer generators. |
| 16-21 | done | 16-20a published on the beta line; 20b onward committed and uncut. The 3.0.0 and 3.1.0 numbers are still unassigned to a cut. |
| 16-23 | done | Every write-up is in `ROADMAP_ARCHIVE.md`. 16-20a published on the beta line; everything from 20b to 24 went out in the 2026-09-12 cut. |
## In-progress detail
**Clean.** Nothing is mid-flight.

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
Reference tool reviewed SHA **187d9ed** (2026-09-12), accepted after the diff
was read: three commits, 7 files, the base44 bump plus the two that became
Phase 31 and Phase 41. Earlier that day `sync` had been run four times against
`2740b0b` - at the start of 23a, 23b, 24 and the review - and was up to date
every time; he pushed after the last of them.

**`triage` was broken by the tree move and is fixed.** `git ls-tree` takes the
working directory as an implicit path prefix, `ROOT` is `main/`, and his
repository has no `main/`, so `upstream_files()` returned **nothing** from
2026-09-06 onward. `triage` read that as "all 310 files deleted upstream",
stamped every record `status: gone` and filed no new file ever again;
`git diff --name-status` has no such prefix, which is why `sync` kept working
and hid it for six days. `--full-tree` is the fix, and re-running `triage`
restored all 310 and filed the 2 new ones.

`docs/upstream/PORT_MANIFEST.json` is authoritative again: **312 files triaged,
none untriaged**; `src/pages/TextEditor.jsx` notes it done in 21.
`REFERENCE_GAPS.md` marks D6, D11 and M14 done and G2 half done; **D7, T1 and
T12 were Phase 23's and G1 and M15 were 24's, and all five are now done.**
Nothing in the audit is scheduled any more. Run `sync` before touching anything
that ports from a directory he has been working in.

## Decisions
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
