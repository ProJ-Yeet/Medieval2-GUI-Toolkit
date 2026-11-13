# The guided unit designer

A beta feature: it is offered only with *Opt into beta features* ticked at the
top of Settings. It works out a unit's stats from a few choices (who the men
are, how good, what they carry and wear, what they ride) and hands the numbers
you pick to the toolkit's own editors. It never writes a file by itself.

The rules and the project format come from Lupinemaverick's
[Stainless Steel: Reforged Unit Builder](https://github.com/lupinemaverick/stainless-steel-reforged-unit-builder),
used with the author's permission, itself built on the MUG Unit Builder v1.5
and the MUG Unit Creation Guide, with the Combat Reforged work for King
Siegfried. The toolkit reads that builder's revision
`d4ed9368d0db3da2000bc895e96f52a83b93cb67` as data; none of its scripts run.

## Where it opens

* **Unit Editor**, the *Guided designer* tab: a design for the unit being edited.
* **New unit**, the *Guided designer* button: a design with no unit yet.
* **Unit sheets**, *Design selected unit*, with exactly one unit row selected.

A design is kept per unit in the mod's sheet project (Save draft), and one
design without a unit per mod. Undo and Redo work inside the window.

## The two profiles

* **Native values** starts from the unit as the mod has it and changes nothing
  by itself. You pin the final numbers you want under *Final stat overrides*.
* **Combat Reforged** works every number out from the choices: archetype,
  quality, class, equipment grade, subtypes, weapons, armour and its layers,
  shield, horse and barding, terrain and formation. It is a balance choice you
  make, never picked for you from a mod's folder name.

Upgrade bonuses follow each mod's engine: the base game +3 attack and +2 armour
per level, an EOP mod what its `luaPluginScript.lua` sets, an M2EX mod what its
`descr_caps_ex.txt` sets. *Calculation contributions* under the results lists every term
that went into each number, so a value is never a mystery.

## What it never writes

These are kept in the design as notes, because nothing shows the game runs
them: the custom weapon and unit effects (`hook_drag`, `hook`, `rend`,
`stagger`, `duelist`, `pikebreaker`, `batter`, `crush`, `hemorrhage`,
`hamstring`, `cleave`, `linebreaker`, `stalwart`), `sp`, campaign automation
for the Mounted, Bloc, Raider, Engineer and Garrison subtypes, mount movement
and geometry, and the M2EX armour and weapon levels of a mercenary pool line.

A unit's own attributes that the designer has no word for (an EOP mod's
`area_effect_25_2`, say) stay on the unit when you take the design's attribute
list, where they stood among its other attributes.

## Using a design

Tick the fields to take under *Apply to a unit*, then *Show the changes*. A
missing battle model, projectile or mount is listed first, and nothing goes on
until it is fixed.

* From the Unit Editor, the fields go into the unit's own edits. The editor's
  Save previews, backs up and logs them; the Log undoes them.
* From New unit, pick the unit to copy; New unit's composer opens on it with the
  fields on top, where the name, models, factions and cards are chosen as usual.
* From Unit sheets, the fields go back to the sheets as edits for that unit,
  through the sheets' own review. Their Apply backs up and logs.
* **Mercenary pools**: with the Mercenary subtype ticked, set the pool numbers,
  tick the campaign's pools and *Preview pools*. A pool that already has one
  line for the unit gets the new numbers and keeps its religions, events and
  years; a pool without one gets a new line. Apply backs up
  `descr_mercenaries.txt`; the Log undoes it. A unit the mod does not have yet
  cannot go in a pool: make it first.

## Examples

`docs/examples/designer/` holds three projects to open with *Portable projects
and exports* > *Import project or presets JSON*: mounted knights, militia pikemen and
mercenary crossbowmen (with pool numbers set, pools left for you to tick).
`tests/test_builder_examples.py` keeps them valid.

## What was tested, and what was not

| Check | Base game (EOP installed) | Divide and Conquer EUR (EOP) |
| --- | --- | --- |
| Open, preview and stage on cavalry and infantry | done | done |
| A native design equal to the unit stages no change | done | done, custom attribute kept |
| Upgrade bonuses read from the engine | +3 / +2 defaults | +1 / +1 from its Lua |
| Mercenary pools listed | 30 pools | 57 pools |
| Pools previewed in the app | | done, nothing applied |
| Sheets to designer and back, review cancelled | | done |
| Phone width (375 px), failed requests | | done |

Stainless Steel: Reforged and an M2EX mod are not installed here, so neither
was tried. Pool and stat writes were applied on throwaway copies in the test
suites, never on an installed mod. Nothing here claims a design plays the way
its numbers suggest in battle: that needs the game.
