# v2.3.7

**A Health screen, change sets, and the files nobody could open.** Everything
since v2.3.6: one door to every check the toolkit has, your edits recorded and
carried onto a mod's next version, five files that had no screen (the hidden
resources line, cultures, the sound banks, the sound scripts, new text
entries), a tester's pass over the Buildings screen, and the first half of
battle-model animation.

## New

* **🩺 Health: every check, over one mod, in one list.** Ten sources: the
  faction audit, the building tree and recruitment checks, the unit ceilings,
  traits, ancillaries, factions, guilds, campaign constants, the Minor Files
  tabs, and five checks the two crash guides name that nothing ran before.
  Fatal first, grouped by **when it bites** - starting the game, loading a
  campaign, opening a panel, in battle, during play - because that is how a
  crash arrives. Every row opens the screen that owns it, on the record.

  The five new checks were measured on both installed mods before they were
  written: an `ai_label` the AI file does not declare, a `historic_event` with
  no text, a trait and its antitrait excluded for different cultures, an
  absolute path in the banner, projectile or standard files, and a run of
  spaces in the modeldb. Two things the guides claim are **not** checks,
  because the mods disprove them, and Health says so: event names are not
  matched case-sensitively (631 of Divide and Conquer's 633 differ from their
  key only by case, and it plays), and a building level naming a faction the
  level below it does not is not a crash (DaC has 24, ROCSS 6).

  The four cleanup audits (unused models, duplicates, strat models, cards)
  take from 7 seconds to over a minute and never stop a mod starting, so
  Health lists them as doors to their own screens instead of running them.

* **My changes: your edits, recorded and carried onto the next version.** Every
  save the toolkit makes to a mod is recorded as it happens - the file as it
  was, and as you left it - outside the mod folder, so an update that
  overwrites the mod cannot touch them. When it does, **port** the changes
  back: record by record (a unit, a building, a region, a text key), each
  marked clean, merged, conflict or gone, side by side, with one Undo. Export
  and import a set as one file, keep **several versions** of a mod and switch
  between them in place, and **Export changed files** gives just the files you
  changed, in their `data/` folders, ready to unzip onto a mod.

* **The hidden resources line.** A panel on the Buildings screen adds to and
  takes from the EDB's `hidden_resources` line. A removal first lists every
  province that carries the name and every clause that gates on it, and waits
  to be told.

* **Cultures gets a screen of its own**, on four tabs, with the port ladder
  editable value by value and **Duplicate** writing a new culture from one that
  works, naming the text keys, factions and art it still needs.

* **Sound banks and sound scripts.** The six export sound banks (soldier and
  strat map voices, battle events, pre-battle speech, advice, narration) and
  the 31 `descr_sounds_*.txt` scripts open beside Unit Sounds. Every file on
  both installed mods reads and writes back byte for byte.

* **The strings screen adds and removes entries**, several at once, in the
  same save as its edits.

* **Traits and ancillaries given from Lua.** An M2TWEOP mod can give a trait
  from a script and never from a trigger - AGO's `OldAge` is
  `addTraitPoints("OldAge", 1)` in `world.lua`. The traits screen now reads the
  scripts in `eopData` and says **given by a script**, with the file and line,
  instead of "no trigger gives it". On Divide and Conquer, 25 traits it used to
  list that way are given by a script.

* **Interface size**, in Settings: 60% to 125%, remembered. Below 100% fits the
  building editor and its code view side by side on a 1080p screen.

## Changed

* **The building editor's lists fold.** Recruitment, the other capabilities,
  the checks and Probe fold to their headings and start folded, so the dialog
  scrolls to the bottom without the wheel getting caught in a list on the
  way. The ones you open stay open.
* **The recruitment faction filter is a checklist**, open until you click away,
  and a building opens already filtered to the factions ticked in the browser.
* **Picking a faction in the building browser switches the culture to match**,
  so the art and names on screen are that faction's.
* **Code name or in-game name**: the building browser's faction list has the
  Unit Editor's switch, and the two share one setting.
* **The resource picker in a `requires` clause is a suggestion list.** The old
  browser list matched the region names in every label, and hid the resource
  that matched exactly: typing `Harad` showed everything but Harad.

## Fixed

* **Hiding the code view lost your edits to recruit pools and capabilities.**
  Their rows count lines from the code view's text, and without it Probe and
  Save read those numbers against the whole file: every row came back
  "capability line 8 is no longer there - skipped". The code view is now only
  put away, and comes back as it was.
* **Resource names were matched by their spelling.** An EDB that declares
  `Resl` found no region carrying `ResL`; the game matches either.
* **The delete button was cut off** on a recruitment card in grid view.
* **A ticked faction came un-ticked** in the building browser when the culture
  changed.
* **My changes showed the Unit Editor's filters** down the side of the screen.

## Under the hood

* **Battle-model animation, first half.** The toolkit reads animation `.cas`
  files now - all 10 of ROCSS's loose ones and 1 741 of Divide and Conquer's
  1 753 (the twelve it refuses are one siege engine's files, every one cut
  short). Nothing plays yet: the viewer is the second half.
