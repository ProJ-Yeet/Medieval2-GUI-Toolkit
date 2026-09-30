# v2.4.1

**Transfer does more of the job, M2EX mods are read the way M2EX reads them,
and the screens fit the window.** Everything since v2.4.0: a transferred unit
can arrive recruitable, carrying only the skins its new owners wear, with a
banner the destination did not have; an M2EX mod that reads its battle models
as text is read and written through that text; a cloned faction arrives with
its victory conditions and campaign descriptions; and the layout holds at
every interface size, down to a phone.

Measured on the mods the reports came from: Tsardoms 3.0 (the recruitment lag)
and M2EX's own files (the text battle models).

## New

* **Let the faction recruit them.** A tick on the transfer page adds the unit's
  recruit pools in the same job as the unit, through the Recruitment tab's own
  writer. A renamed copy of a unit the destination has gets the original's
  pools, held to its owners; a new unit goes into the building levels that
  recruited it in the source, where the destination has a level of that name.
  Each pool is listed before you apply, one Undo takes them back with the
  unit, and a unit left with none says so.

* **Copy only the skins the new owners wear.** An option on the transfer: the
  copied models keep the texture records of the factions that will own the
  unit, and the files only the others named are not copied. The plan says how
  many files and MB that saved.

* **A banner the destination has not got.** A unit whose `banner` line names a
  banner missing from the destination is caught in the plan: bring the banner
  across (cut to the destination's factions, with a row for each owner) or use
  `main_cavalry` / `main_infantry` instead. Neither leaves a Health finding.

* **M2EX mods that read their battle models as text.** A mod whose
  `descr_caps_ex.txt` says `model_battle_source text` has its models read from
  and written to `descr_model_battle.txt`, so a transfer into or out of one
  lands in the file the game reads, converting between the two. The Home card
  says which file a mod reads, and Health warns when the one the game does not
  read has been changed since.

* **A cloned faction's campaign files.** *Add a faction* now writes the donor's
  victory conditions under the new name in every campaign (its `hold_regions`
  left empty, since those provinces are the donor's) and a title and
  description on the faction picker, and says what is left for you to fill.

* **New resources on M2EX.** On a mod marked as running on M2EX, Minor Files >
  Resources no longer flags a 29th resource as ignored, and offers *New
  resource* and *Clone*: the record, its name and tooltip, and its icon.

* **Open any screen in a new tab.** The Home card's screen buttons and the side
  menu are links now: a middle click, Ctrl+click or *Open in new tab* opens that
  screen for that mod beside the one you are in.

* **The turns beside a pool's rate** on the Unit Editor's Recruitment tab, as
  the Buildings editor shows them: "= 8.9 turns" under 0.112.

## Fixed

* **The Buildings editor no longer freezes on a big level.** On Tsardoms'
  militia barracks (1,131 recruit pools) a ▲ on a pool's rate froze the page,
  and every open tab of the toolkit with it, for a third of a second a click.
  Ten fast clicks now take a fifth of a second in all.

* **The layout fits the window at every interface size.** The Minor Files tab
  strip is one row that scrolls instead of tabs three lines tall pushing the
  page sideways, *+ New* and *Port from another mod* are the size of their
  labels, and the breakpoints now follow Settings' interface size, not only the
  window's. Nothing scrolls sideways at 1280, 1600 or 1920 px at 60-125%, or on
  a phone.

* **Restart now to apply it keeps its console.** With *Keep the console window
  open* ticked, a restart came back with no console; it now starts on the
  console interpreter.

* **A faction clone's shield.** A cloned faction pointed at shield names the
  interface sheets did not have and showed the wrong button; it gets shields of
  its own, and the Factions editor, Health and the faction audit find and
  repair the ones made before.

* **A sprite at the far LOD.** A transferred model whose sprite path the
  destination already used for a different sprite showed the destination's;
  it now arrives under a name of its own.

* **A models file with a hand edit.** A `battle_models.modeldb` with a stray
  letter after a `0` is named as the hand edit it is, with the line, and a
  `blank` entry holding a name reads.
