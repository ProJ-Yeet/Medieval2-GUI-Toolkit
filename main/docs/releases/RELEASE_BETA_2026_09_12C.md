# beta 2026-09-12c

**Everything in v2.3.2 with the campaign map switched on**, and the reason this
build exists: the strat model viewer drew settlements as a bare white cube, or
as nothing at all. It draws them now.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in
rather than the moment you load it. Everything it writes is backed up and one
Undo away. Read the plan before you press Apply.

## Fixed

* **Strat models: the whole settlement, not one white box.** Open Campaign Map
  → Strat models on Divide and Conquer, pick `anduin_city_4`, and you got a
  flicker of something correct and then a plain cube. On models built
  differently you got an empty canvas. Wireframe always worked, which is the
  clue nobody could act on.

  The model was fine. Its **textures** were the problem, and it took four
  wrong answers stacked on one wrong answer to get there.

  A mod's packer converts each `.tga` to a DDS file named `<name>.tga.dds`,
  and **truncates the original `.tga` to zero bytes rather than deleting it**.
  Divide and Conquer has 1,172 of those stubs under `data/models_strat` and
  Third Age Reforged has two - and 1,171 of the 1,174 have their real art
  sitting right beside them under exactly that name. The toolkit looked for the
  file the model named, found it, and never looked at the one next to it. An
  empty file is still a file.

  From there: an unreadable file came back as a blank picture rather than as an
  error, so the viewer believed it had a texture, uploaded it, and the shader's
  cut-out rule - the one that makes a plume a plume on a soldier - deleted
  every part of the model that named a texture. The cube was the one mesh in
  the scene with **no material at all**, which is why it survived. The flicker
  was the model drawn correctly, for the frames before the blank arrived.

  All five are fixed. Across all 926 of Divide and Conquer's strat models there
  is now no material at all that the viewer cannot paint with.

* **And when a texture really is broken, the panel says so.** A grey model with
  no explanation was half the original complaint. The facts panel now names the
  file and says what is wrong with it - that it is empty, or that its art is
  beside it under another name, or that it will not decode - and the mesh row
  that uses it reads *will not load* rather than *not in this mod*. Those two
  were the same label and they are not the same thing.

* **The alpha cut-out no longer applies to campaign-map models.** It is a rule
  measured on battle models, where it is what gives a plume its shape, and it
  was being applied to strat models exported by a different tool. Unit models
  are unchanged.

* **"There is no faction slot called england in this mod" - when there is.**
  Carried up from v2.3.2: on a mod that keeps `descr_sm_factions.txt` inside a
  `.pack`, the Factions screen refused outright and Rename slot refused every
  faction by name. It now says the file is not loose, how many archives it can
  see, and what unpacking it would get you.

* **A picture that would not load stayed broken until you cleared the cache.**
  Also from v2.3.2. The blank drawn for a file that could not be read was being
  cached alongside real pictures, so fixing the file changed nothing. Replace
  the file and it appears now.

## Not in this build

The toolkit still cannot read inside a `.pack`. Where it says a file is not
loose, that is exactly what it measured - the archives it can see and the file
it cannot find - and it does not claim to know what is inside them.

## What has not changed

No campaign file is written by any of this. The strat model viewer is the one
screen in the toolkit that only looks.
