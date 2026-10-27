# Simplified Chinese (zh-Hans)

Phase 88o started 2026-10-26 on the user's request to start Chinese
translation. Simplified Chinese comes first in the roadmap; Traditional
Chinese is the separate Phase 88p catalogue.

## Workflow

The draft stays in `dev/i18n/zh-Hans.json`, outside the language picker.
Merge through the checked workflow only; source hashes are maintained by it.
Run from the repository root:

```text
python main/dev/checks/i18n_todo.py zh-Hans
python main/dev/checks/i18n_todo.py zh-Hans --batch core --max 200 --out .cache/zh-Hans-core.json
python main/dev/checks/i18n_todo.py zh-Hans --merge .cache/zh-Hans-core-answer.json
```

Fix every refusal before proceeding. Do not promote until the catalogue is
complete, no source hashes are stale, the full checker passes, and the CJK
groundwork and screen review required by Phase 88o are done.

## Style

- Plain Simplified Chinese for people editing Medieval II mods. Use concise
  verb labels and direct instructions, with 你 where a pronoun is needed.
- Follow the Chinese termbase: 模组, 部队, 派系, 定居点, 战役, 战斗模型,
  战略模型, 骨架, 贴图, 随从, 特质, 槽位, 日志 and 撤消.
- Use Chinese punctuation in prose and preserve symbols and ellipses.
  Keep filenames, folder names, literal keywords, product names, code,
  placeholders, HTML tags and attributes unchanged. No em dashes.
- Keep a space between Chinese prose and embedded Latin names or numbers
  where appropriate. Avoid adding spaces between Chinese words.
- Chinese plural objects have only `other`; preserve `{count}` and use
  a suitable classifier, for example `{count} 个模组` and `{count} 项`.
- Do not attach grammatical assumptions to unknown placeholders. Preserve
  sentence fragments used by existing joins, including the boot error.
- The catalogue remains a draft until reviewed by a Chinese-speaking modder.

## Checkpoint, 2026-10-26

412/9,605 IDs done, 9,193 missing, zero stale or extra. Complete namespaces:
app (67), boot (7), common (85), home (82), i18n (2), settings (169).
Next: core, then transfer, editor and edrecruit.

All 412 entries pass `check_catalogue` against their English source with
the live termbase: placeholders, markup, protected tokens, terminology and
plural categories. Termbase completeness also reports zero problems.
Both translated plural objects have `other` only. The seven boot fragments
were checked against their concatenation order in `web/js/boot.js`.

Exact glossary exceptions, based on alternate senses or literal tokens:

- `app.shared_cards_title`: tile is a UI card, not a campaign-map square.
- `home.mounted_pack`: mount means attaching an archive, not a riding animal.
- `home.pick_your_medieval_ii_folder_it`: mods is the literal folder name.
- `settings.and_more_characters_in_the_diagnostic`: characters are text
  characters, not people.
- `settings.start_the_soldier_row_on_base`: building means creating a unit,
  not constructing a settlement building.

Source and answer batches: `.cache/zh-Hans-foundation[-answer].json` and
`.cache/zh-Hans-settings[-answer].json`. Final versions merge with zero
refusals. `dev/i18n/zh-Hans.source.json` records the English hashes.

CJK system-font stacks, line breaking, suppression of synthetic italics and
letter spacing, desktop/narrow screen inspection and native review are still
pending. No UI review or completion of Phase 88o is claimed. No application
code or termbase changes were needed for these batches. No release was cut.
Five-hour usage at the validation checkpoint: 96% remaining.


## Continuation checkpoint, 2026-10-26

9,605/9,605 done; 0 missing, zero stale/extra.
All translated entries pass the full structural and terminology checks.
Complete namespaces: ancillaries, app, areaeffects, armory, battleflags, bmdb, boot, buildings, campaint, campbrowse, campcreate, campdb, campevents, campforts, campimport, campmap, campmark, campnew, cards, changes, characters, climates, codeview, common, compare, core, dupes, edbimport, editor, edrecruit, edusort, eng.ancillaries, eng.animedit, eng.animloose, eng.animpack, eng.animslot, eng.animview, eng.areaeffects, eng.armbake, eng.armlib, eng.armory, eng.armunit, eng.artrecolour, eng.bannermaker, eng.banners, eng.bmdb, eng.buildings, eng.campaint, eng.campdb, eng.campevents, eng.campfiles, eng.campimport, eng.campmap, eng.campnew, eng.campstrat, eng.cards, eng.cas, eng.casanim, eng.changesets, eng.characters, eng.cleaner, eng.climatenew, eng.codeview, eng.crashrules, eng.dupes, eng.edbimport, eng.edit, eng.educeil, eng.edusort, eng.emblem, eng.factionaudit, eng.factionbring, eng.factionclone, eng.factions, eng.factionsites, eng.fileswap, eng.flatrecord, eng.gamelog, eng.gamepack, eng.guilds, eng.health, eng.heroabilities, eng.hordestart, eng.images, eng.keyblock, eng.launchcheck, eng.leafxml, eng.mapbundle, eng.mapcheck, eng.mapfe, eng.mapgen, eng.mapnew, eng.mapnewreal, eng.mapquery, eng.mapreal, eng.mapresize, eng.mapterrain, eng.maptga, eng.mercpools, eng.mesh, eng.meshfolder, eng.meshwrite, eng.minorfiles, eng.mod, eng.modeldb, eng.modelexport, eng.modfork, eng.modreport, eng.namekeys, eng.osmmap, eng.osmsites, eng.pack, eng.packhouse, eng.portrecords, eng.projectzip, eng.rawtext, eng.rebelpools, eng.regiondel, eng.rehearse, eng.renames, eng.scriptaddons, eng.scriptbuilder, eng.scriptcompat, eng.scriptfiles, eng.scripts, eng.scriptwords, eng.server, eng.settlemech, eng.settlemodel, eng.sidefiles, eng.soundbanks, eng.sounds, eng.soundscripts, eng.sprites, eng.spritesheet, eng.stratcamp, eng.stratchar, eng.stratedit, eng.stratfamily, eng.stratmap, eng.stratobj, eng.strings, eng.stringsbin, eng.traits, eng.transfer, eng.triggers, eng.voices, eng.walls, eng.winconds, facaudit, factions, factionsites, family, guided, guilds, health, healthx, heroabilities, home, hordestart, i18n, images, map3d, mapcheck, mapfe, mapfind, mapgen, maplabels, mappin, mapquery, mapsize, mapviews, mercs, minorfiles, modelpicker, osmmap, osmworld, packs, portui, projectzip, rawtext, rebels, recolour, regiondel, renameui, scripts, settings, settlemech, settlemodel, sidefiles, soundbanks, sounds, sprites, stratcamp, stratchar, stratedit, stratmap, stratview, strings, traits, transfer, triggerui, undo, v3anim, viewer3d, voices, walls.
User explicitly authorized continuing past the 50% usage guard for this run.
No promotion or release. Source/answer batches are in .cache/zh-Hans-*.json.
Authoritative next work comes from i18n_todo.py zh-Hans.
