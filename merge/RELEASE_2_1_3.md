# Medieval 2 GUI Toolkit v2.1.3

This one is about disk and about gaps nothing else can see.

A big overhaul ships art the game can never reach — strat-map models replaced
two versions ago, unit cards for units that no longer exist, the same info card
copied byte for byte into thirty faction folders — and none of it is visible
anywhere, because nothing in any file says it is unused. Divide and Conquer
carries **700 MB** of it. So BMDB mode grows from two tabs to four: the two new
ones find that art and move it out, backed up and undoable, the way 🧹 Clean up
BMDB already did for `battle_models.modeldb`.

The same release fixes the other kind of invisible gap — a model entry with no
texture record for a faction that fields a unit drawn with it — and makes the 3D
viewer a panel you can actually size.

A subrelease: real features, same standing as 14j and 2.1.2, not folded into
Phase 16 because Phase 16 (the Campaign Map Editor) is a different program.

---

## The short list

- **Strat map**, a new tab: `descr_model_strat.txt` and `data/models_strat`
  audited and cleaned the way the modeldb already was. 4 MB of dead models and
  **54 MB of unnamed files** in Divide and Conquer.
- **Unit cards**, a new tab: every unit and info card hashed, then the art for
  units that are gone removed and the identical copies folded into the merc
  folder the game already falls back to. **645 MB of Divide and Conquer's 1.2 GB**
  of card art. Where a mod genuinely ships a *different* card per faction, it
  shows them side by side and takes no view — you pick, or you leave them.
- **🛡 Fix ownership** and **🌐 All factions**, beside 🧹 Clean up BMDB: give a
  model entry a texture record for every faction that fields a unit drawn with
  it — or for every faction in the mod. 212 gaps in Divide and Conquer, 264 in
  Third Age Reforged.
- **The 3D viewer's divider is draggable**, on both docks, with the width
  remembered per screen. In BMDB mode the panel now opens at **half the window
  and already showing**.
- **A mount is drawn from one texture, not two glued together.** Half the texture
  memory and one less decode, for a picture identical to the one before.

---

## Everything in this release

### Strat map — the campaign map's models

`unittransfer/stratmap.py` + `web/js/stratmap.js`. The third tab of BMDB mode.

The strat map is where unused art hides. A battle model nobody recruits is at
least visible in the unit list; a general model that was replaced two versions
ago is visible nowhere at all, and its 5 MB texture goes on shipping.

The tab lists every `type` block in `descr_model_strat.txt` with what references
it, and 🧹 Clean up strat map offers two lists: the models nothing names, and the
files under `data/models_strat` nothing points at. References are read from
`descr_character.txt`, another block's `model_sprite`, `descr_sm_factions.txt`,
`descr_sm_resources.txt`, `descr_cultures.txt`, every campaign's
`descr_strat.txt` and `campaign_script.txt`, and every `.lua` in the mod — the
same over-cautious net the modeldb cleanup uses, and for the same reason: a false
"still used" costs nothing and a false "unused" silently breaks a mod.

**Two rules make this safe rather than catastrophic, and both came out of running
the scan against a real mod before any of the UI existed:**

- **`models_strat/residences` is skipped entirely.** The settlement models live
  there, and the game picks a faction's variant of one out of that tree *by
  folder* — nothing names the file anywhere, so "nothing names it" would be wrong
  about all 2,443 of them. It also cannot hold anything unused worth finding: a
  settlement nobody can see is the first thing a player notices.
- **`x.tga`, `x.tga.dds` and `x.dds` are ONE texture.** M2TW prefers the DDS and
  loads it for a line that says `.tga`, which is what every texture optimiser in
  the scene leaves behind. A reference to any spelling protects all three, and
  removing a model takes all three with it. Without that rule the first run
  reported **387 MB of Divide and Conquer's live art** as named by nothing. With
  it, the honest answer is 54 MB.

The rewrite of `descr_model_strat.txt` is a splice: every other byte of the file,
its CRLF endings and its tab alignment included, comes out exactly as it went in.

### Unit cards — one picture instead of thirty

`unittransfer/cards.py` + `web/js/cards.js`. The fourth tab.

The game finds a unit's card under the **player's** faction folder, so a unit
thirty factions can field needs its card in thirty folders — and mods do exactly
that, byte for byte. Divide and Conquer ships 4,289 info cards for 916 units:
1.2 GB, of which 244 MB is art for units that no longer exist and 397 MB is the
same picture copied out.

The way out is the folder the engine already falls back to. `ui/units/mercs` and
`ui/unit_info/merc` are searched for any unit whose own faction folder has
nothing, which is why DaC already keeps 1,181 of its 1,554 unit cards there and
nowhere else. One copy does the job of thirty.

Every card in the mod is hashed, so "the same picture" is a fact rather than a
guess, and the tab asks three questions per kind of card:

1. **for units that are gone** — a dictionary no unit claims, in
   `export_descr_unit.txt` or in an M2TWEOP unit file. Ticked, because it is a
   fact
2. **the same picture in several folders** — every copy byte for byte identical.
   One goes to the merc folder, the rest move out. Nothing written at all when
   one of them is already the merc copy. Ticked, because there is nothing to
   decide
3. **different pictures per faction** — shown side by side, each with the folders
   that hold it, and **nothing ticked**. Some mods really do give a unit a
   different card per faction, and collapsing that on its own would be the tool
   choosing which art a mod ships

Three refusals, said out loud on the page: a file that is not shaped like a card
(the agent pictures — `spy.tga`, `diplomat.tga` — and whatever else has been
dropped in there), a unit that pins `card_pic_dir` / `info_pic_dir`, and a
dictionary no unit claims but a `.lua` script names.

### 🛡 Fix ownership · 🌐 All factions

`bmdb.ownership_audit` / `bmdb.ownership_edits`, and two buttons beside the
cleanup.

A modeldb entry carries one texture record per faction and the game reads the
one belonging to the faction whose army is on the field. An entry with no record
for a faction that fields a unit drawn with it is a unit that does not show up
right for that faction — and nothing in either file says the two lists have to
agree, which is exactly why nobody notices.

**Fix ownership** takes the answer from the units: every faction that owns a unit
whose `soldier`, `officer` or `armour_ug_models` names this entry. All three
slots count, because all three are drawn on the field; `slave` counts too, being
the generic rebel skin. **All factions** takes it from the roster instead — every
faction in the mod, on every entry.

A new record is a clone of one the entry already has, so it points at the same
texture until you give it its own, and records are only ever **added**. The
dialog says how much bigger `battle_models.modeldb` gets before you press
anything — Fix ownership is +0.1 MB on DaC; All factions is +9.4 MB on Third Age
Reforged's 1.4 MB file, **7.8×**, and the row goes amber with a pointer back at
🧹 Clean up BMDB. Ownership tokens the faction roster does not define (an
`ownership` line may name a *culture*) are reported with the units that name
them and never written.

The write goes through `edit.plan_bmdb` — the same planner the model card's own
faction checklist uses — so it inherits that path's backup and undo rather than
getting its own.

### A viewer you can size

`splitInstall` in `core.js` puts a grab bar between the list and the docked 3D
panel, in both the Unit Editor and BMDB mode. Full screen used to be the only way
to see a model bigger, and full screen takes the thing you were reading with it.
Double-click resets; the width is saved per screen. In BMDB mode the panel opens
at half the window and already showing, seeded with the first entry — going down
two thousand entries deciding which of them is the horse is what that screen is
for.

### One sheet is one texture

The viewer painted every model from two sheets glued side by side, and when an
entry named no attachment sheet it glued the main one to a copy of itself. That
is a canvas, a second decode and a 2048-wide atlas for a result identical to
wrapping the single sheet — because the pair tiles anyway.

It now binds the one sheet and scales u by 1.0 instead of 0.5 (`uUScale` on the
fragment shader). **Every ordinary mount is that case** — a horse, a wolf, a
camel has one texture and an empty attachment slot — and so is any unit entry
whose attachment slot repeats the main file. Entries that really do carry a
second sheet (the Balrog, hero models with their own weapon sheet) are still
glued and look exactly as they did.

---

## Under the hood

**Tests:** `tests/test_stratmap.py` (43 checks), `tests/test_cards.py` (39) and
`tests/test_ownership.py` (41) are new, and all three build their whole mod from
scratch — a `descr_model_strat.txt` with CRLF endings and tab alignment, a
`models_strat` tree with a `residences` folder and a `.tga.dds` beside a `.tga`,
card folders holding identical copies and differing copies and the agent
pictures, a `battle_models.modeldb` written by hand down to its length prefixes.
That is the only way to pin the cases these three live or die on. All three end
by undoing the run and requiring every file back byte for byte.
`tests/test_bmdb_http.py` gained 13 checks driving the two ownership buttons over
a real server.

**65 test modules**, run individually (`python -m tests.test_X`).

**Nothing is deleted, anywhere in this release.** Every file the three cleaners
take out is copied to a folder outside the mod in the mod's own layout first,
backed up second, and restored byte for byte by 🕑 Log → Undo — including the
merc-folder copies the card consolidation *creates*, which undo removes again.

---

**Next:** Phase 16, the Campaign Map Editor — 3.0.0.
