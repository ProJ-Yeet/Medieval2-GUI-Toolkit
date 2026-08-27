# Medieval 2 GUI Toolkit v2.1.5

All of this release is about one thing: the modeldb cleanup deciding what is
dead, and being wrong about it.

It came out of a mod that stopped launching after a clean-up. Chasing that turned
up three separate places where a battle model the game genuinely needs was
invisible to the scan — a whole *kind* of campaign file nobody was opening, a
script command whose model sits where no pattern was looking, and every campaign
folder one level deeper than the walk reached. Any one of them deletes a model
the campaign uses, and you only find out in game.

So the cleanup's nets are wider, and there is now a way to ask the question
after the fact: **Recheck past cleanups** re-reads the cleanup log, re-tests
everything a past run removed against today's nets, and tells you what should not
have gone and whether a copy of it still exists to put back.

A subrelease: same standing as 14j, 2.1.2, 2.1.3 and 2.1.4 — real features, not
folded into Phase 16 because Phase 16 (the Campaign Map Editor) is a different
program.

---

## The short list

- **`change_battle_model` is read.** The script command that swaps a character's
  model mid-campaign put its model where nothing was looking, so a model named
  only that way looked like textbook dead weight.
- **Custom battle maps are read** — `world/maps/battle/custom/*/descr_battle.txt`
  was a file kind the cleanup never opened at all.
- **Every campaign folder is read, however deep** — a custom campaign sits one
  level below where the walk used to stop.
- **An installer's alternate trees are read** (`Activate/`, `extra/`): a copy
  today, the live mod the moment you run the mod's own switcher.
- **🧹 Clean up BMDB → Recheck past cleanups** — what an older, narrower clean-up
  took out that this build would have refused to touch, with a one-click revert
  from the backup or the export folder.
- **A cleanup writes down which entries it removed**, so that question stays
  answerable after the backups are gone.
- **The mod's other `battle_models.modeldb` files are still ignored, on purpose**
  — and the tool now says so out loud.
- **The text scan streams**, so a mod with a two-gigabyte file in it no longer
  runs the server out of memory.

---

## Everything in this release

### `change_battle_model` — the model is the LAST word

`unittransfer/bmdb.py`, `script_models` / `_BATTLE_MODEL_KEYWORD_RE`.

A campaign script names a battle model two ways, and only one of them was being
read:

```
character  Gandalf, named character, age 22, battle_model gandalf_white, label g2
change_battle_model turks leader aragorn_arnor
```

The second is a script command that swaps a character's model mid-campaign — how
a mod turns its faction leader into the crowned king at the climax of its own
story. It broke both existing patterns at once. The bare-word pattern never
fired, because the character before `battle_model` is `_` rather than a space or
a comma; and had it been loosened to fire, it would have captured `turks` — the
faction, not the model, since this form puts the model on the *end*.

An entry named only this way is invisible to every other net in the module: no
unit fields it, no mount or `descr_character.txt` names it. It reads as dead
weight and the cleanup offers it up.

So the keyword is now matched with whatever prefix it carries, and the prefix
decides where the model sits: `battle_model` is followed by its model,
`anything_else_battle_model` is a command whose last argument is the model.
Taking the last argument rather than the third also keeps a two-argument variant
working, and an unknown `*_battle_model` command written in some future patch is
read as a command rather than silently ignored.

On one overhaul this was 17 occurrences naming three models, one of which existed
nowhere else in the mod.

### Where campaign files actually live

`unittransfer/bmdb.py`, `campaign_files`; `unittransfer/luascan.py`, `mod_files`.

The old walk listed the immediate children of `data/world/maps/campaign/` and
read `descr_strat.txt` / `campaign_script.txt` in each. That misses, in ascending
order of how badly:

- **a custom campaign**, which ships as `campaign/custom/<name>/` — one folder
  deeper than the walk ever looked;
- **a custom battle**, `world/maps/battle/custom/<name>/descr_battle.txt`, which
  names its characters' battle models exactly the way a `descr_strat.txt` does,
  on a tree that was never opened;
- **an installer's alternate trees** — `Activate/NORMAL/…`, `extra/kdSkip/…` and
  friends. Those are copies right now and they are the live mod the second
  somebody runs the mod's own configuration switcher, so a model only they name
  is not dead weight, it is the model the next configuration needs.

The whole mod root is walked for them instead, the same way `luascan` already
walked it for `.lua`. On the overhaul this was found on, the cleanup went from
reading 2 campaign files to 15.

Each is now labelled by its **path inside the mod** rather than its parent
folder, because `imperial_campaign/campaign_script.txt` stopped identifying a
file the moment those two filenames turned up in six different trees.

### One tree walk, not four

`unittransfer/luascan.py`, `mod_files`; `unittransfer/mod.py`, `Mod.scanned_files`.

Finding all of that means walking a hundred thousand files. `lua_files` already
did one such walk and threw away everything that was not a `.lua`; it now keeps
the campaign scripts and the text files too, and the three callers take three
slices of one cached answer. `Mod.lua_files` is now a view onto it, so nothing
that used it had to change.

### 🧹 Clean up BMDB → Recheck past cleanups

`unittransfer/bmdb.py`, `recheck` / `revert_recheck`;
`GET /api/bmdb/recheck`, `POST /api/bmdb/recheck_revert`; `web/js/packs.js`.

Every other net in the module answers "may this go?" *before* anything moves.
This answers the question that only ever comes up afterwards, usually with the
game already refusing to launch: **the last cleanup ran with a narrower idea of
what counts as a reference than this build has — did it take something out that
today it would refuse to touch?**

It cannot be part of the ordinary scan, and that is the whole point. The audit
describes the mod as it is; a file that is gone is not in the mod to be
described, and the only surviving record that it ever existed is the cleanup's
own log entry. So the recheck reads the log, re-derives what each run removed,
re-tests every one of those against the current nets, and answers the practical
question: can it be put back, and from where.

Each row carries the three facts a decision needs — what was removed, why this
build now thinks it was needed, and whether a copy survives. Ticked rows are
copied back: files from the backup or the export folder, entries read out of the
modeldb they were saved into and appended to the live one. The revert goes
through the same backup-and-log machinery as every other write here, so a revert
that turns out to be wrong is itself undoable from 🕑 Log.

Anything already back on disk is dropped from the report, however it got fixed.

**A run whose copies are both gone is still reported** — the log remembers what
it removed even when the backup folder and the export folder have both been
deleted — but the row says plainly that it cannot be put back, and offers no
button that would fail. That is the honest answer, and it is one the tool used to
have no way of giving at all.

### A cleanup writes down what it removed

`unittransfer/bmdb.py`, `apply_cleanup` / `removed_entries`.

The log record now carries the removed entry names. Months later the export
folder and the backups can both be gone, and that record is then the only
surviving answer to "what did that run actually take out". For runs from older
builds the names are recovered from the export folder's
`removed_battle_models.modeldb`, or failing that by diffing the backed-up modeldb
against the live one.

### The other modeldb files stay ignored — and the tool says so

`unittransfer/luascan.py`, `mod_files`; `unittransfer/bmdb.py`.

A mature mod carries several: `battle_models.modeldb.bak`, `battle_models_og.modeldb`,
a working copy some other tool wrote under `from_modeldb/`. They look like a
second opinion about which meshes are alive and they are not one — every one of
them is a snapshot of an *older* state of the same file, so honouring them would
hold alive every file the mod has ever used at any point in its history, and no
cleanup could free anything again.

They are therefore not read, by anything, and never token-scanned as text either
— a modeldb names thousands of files, so reading one as text would make every
file in the mod "mentioned somewhere". That was always the behaviour; what is new
is that the reasoning is written down at the skip, the Recheck dialog states it
where you can see it, and a test now pins it: a file only the backup copies name
is still offered as an orphan.

### The text scan streams

`unittransfer/bmdb.py`, `unit_model_refs`; `unittransfer/luascan.py`,
`TEXT_SUFFIXES`.

Reading every text file in a mod to see whether any of them names a file under
`unit_models` meant holding a whole file *and* a lower-cased copy of it. On a mod
with `data/sounds/Music.dat` in it — two gigabytes — that is a `MemoryError`, and
the server returned a 500 with the scan half done.

`.dat` was the mistake and is gone from the list: in M2TW that suffix belongs to
the engine's binary containers, not to anything readable. But the fix is the
scan itself, which now reads a line at a time, so no single file can double
itself in memory whatever its suffix says. Anything else binary that slips in is
caught by a NUL-byte sniff of the first block and skipped, with a count in the
log.

Line numbers come out of the streaming for free, which was the other half of the
old cost. The scan went from 292 seconds to 22 on the mod it was found on, and
the whole recheck from 356 seconds to 26.

---

## What this does not claim

The recheck is only as good as the nets behind it. A clean result means nothing a
past cleanup removed is named by anything **this build reads** — the EDU and
M2TWEOP units, `descr_mount.txt`, `descr_character.txt`, every campaign and
battle script, every `.lua`, every `data/descr_*.txt`, and every text file in the
mod that could name a mesh by filename. The dialog lists exactly what it read and
how much of it, so a clean verdict can be checked rather than taken on faith.

---

## Tests

`tests/test_bmdb.py` — 143 checks, up from 104:

- both `battle_model` forms parse, the command form yields its **last** argument,
  the faction on that line is never mistaken for the model, and an unknown
  `*_battle_model` command is read as a command rather than ignored
- a model named only by a nested custom campaign, a custom battle map, an
  `Activate/` tree or an `extra/` tree is not called unused, and each is
  attributed to its own full path inside the mod
- a file only the mod's backup modeldbs name **is** still offered as an orphan; no
  `.modeldb` is ever offered for removal, collected as a text file, or able to
  resurrect a file through the text scan
- the recheck round trip: a script that turns up *after* a cleanup flags exactly
  the file it names and not the one nothing names, says why, reverts byte-exact,
  reports clean on a second run, and the revert is itself undoable
- an entry removed by a cleanup is recovered by name from the log, put back into
  the live modeldb, and what is left still parses
- a run whose backup and export folder are both gone is still reported, is marked
  unrecoverable, and fails with a reason rather than pretending if reverted anyway

---

## Also

**`app.py --no-browser`** — serve without opening a tab in the system default
browser. For anything driving the UI itself: a test, a script, an agent with a
browser of its own, where a tab thrown at your default browser is an interruption
rather than a convenience. The "no browser ever loaded the page" warning is
suppressed under the flag, because there it is the expected outcome rather than
the failure that check exists to shout about.
