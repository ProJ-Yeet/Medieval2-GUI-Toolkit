# v2.3.3

**BMDB + Sprites is the Models Editor**, and the rename is the smallest part of
it. That screen has had four tabs for a long time - model entries, sprites,
strat map, unit cards - and only one of them was in the name. The two things
that made the old name nearly true have been fixed instead.

## New

* **Every campaign-map model in 3D, and you no longer need the campaign map to
  get at them.** Models Editor → Strat map now has the same 3D panel the model
  entries have had: it opens beside the list, it keeps the width you drag it
  to, and it does not rebuild itself every time you type in the search box.

  Every entry that ships a `.CAS` gets its own 🧊. On Divide and Conquer that
  is 206 of its 237 entries; an entry whose meshes are all inside a `.pack`, or
  simply missing, gets no button rather than a button that fails.

* **And the panel browses the model files themselves, which is where the
  settlements are.** `descr_model_strat.txt` declares the generals, the agents,
  the heroes and the faction symbols - and **not one settlement**. The game
  picks those by level and culture out of the `data/models_strat` folder tree
  with nothing naming the file, which is why Amon Hen and Minas Tirith are on
  the campaign map and in no entry at all.

  So the panel has a second way in: a filter box and every `.cas` the mod
  ships, grouped the way its folders group them. Divide and Conquer declares
  237 entries and ships **926 model files**.

  This browser existed before, inside the campaign map editor - which is not in
  this build, and has never been. It has moved to the Models Editor, where the
  rest of a mod's models are, and it is on the menu here for the first time.

* **A strat model's card opens its meshes too.** Click any entry for the
  read-only card - the block as the file stores it, and every file it names -
  and a mesh the mod actually ships now has a 🧊 beside it. That card is what
  you read to decide whether a block can go, and what it draws was the part of
  that decision nothing could show you.

## Where the rest of it went

This build is the same tree as **beta 2026-09-16** with the campaign map editor
switched off. That editor's panel has been rebuilt in the same work - two
strips instead of one, and the brush's colours moved to a column beside the map
- and the beta's notes cover it.
