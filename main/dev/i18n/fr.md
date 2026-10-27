# French (fr)

Phase 88e completed 2026-10-26. The 9,605-ID catalogue is in
web/i18n/fr.json and offered in Settings as Français (French) - brouillon.
Its status remains draft pending review by a French-speaking Medieval II modder.
See fr-review.md for terminology, exact glossary exceptions and UI review scope.
Use polite plural vous, infinitive button labels, sentence case, French
accents and curly apostrophes. Preserve filenames, keywords, placeholders,
HTML and code content. Follow the French termbase. No em dashes.
Use one/many/other for every plural object (CLDR French).

Merge only through i18n_todo.py; fix refusals. Exemptions require exact ID
and genuine alternate sense or literal-token evidence. Keep unknown noun
placeholders isolated when agreement cannot be known. Draft until native
review. The completed catalogue passed validation and the Phase 88e UI walk
before promotion. The checkpoints below are historical.

Initial batch: boot/common80 strings. Continue missing common then i18n,
app/home/settings/core. Run i18n_todo.py fr for authoritative counts.

App67 and remaining common/i18n14 completed. app.shared_cards_title
exempts tile: UI cards, not map tiles. Module label Transférer des unités
uses the verb to match the termbase. Native review should assess époque
labels Ancienne/Haute/Tardive. Use i18n_todo.py fr for current counts.

# French common and i18n

Read main/dev/i18n/fr.md and exported fresh missing strings. Completed14: common12, i18n2. Checked merge accepted14 with zero refusals; fresh export0 missing. Answer .cache/fr-common-answer.json. No plurals in batch; no exemptions needed. Preserved lowercase/uppercase status distinction, ellipses and {name}. Trigger=déclencheur. No Russian/shared-doc/termbase edits or promotion. Stopped after assignment; usage at start77% used /23% remaining.

## Checkpoint

2026-10-25:243/9,605 done,9,362 missing,0 stale/extra. Completed boot,
common, i18n, app and home. Next settings/core. French remains isolated
in dev/i18n. Home mounted_pack exempts mount (archive attachment rather
than riding animal). Existing termbase transfér stem does not accept noun
transfert; use natural verb constructions where possible, review globally
if noun labels become necessary. All batches passed merge checks.
Russian translation complete, full UI QA pending.

## Checkpoint 2026-10-26

607/9,605 done, 8,998 missing, 0 stale/extra. Completed settings (169)
and core (195), including core.things_to_look_at with one/many/other.
All 607 translated entries pass the catalogue checker (markup, placeholders,
literal tokens, plurals and terminology); termbase completeness and
git diff --check pass. No UI or native-speaker review performed; no promotion.
Next: transfer, then editor and edrecruit. Russian remains 9,605/9,605,
with UI QA still pending.

French termbase now accepts transfert alongside transfér, as its existing
note already specified, and généraux alongside général. Prefer natural
transfer noun labels; the earlier checkpoint's workaround is obsolete.
Review earlier app labels for consistency before promotion. Settings and
core use Fichiers secondaires, Cartes d’unités and Carte de campagne.

Exact alternate-sense exemptions added:
- settings.and_more_characters_in_the_diagnostic: character means a text
  character (caractère), not a person.
- settings.start_the_soldier_row_on_base: building means creating a unit,
  not a settlement building.
- core.every_model_a_mod_ships_the: ships means includes/distributes,
  not a naval vessel.
- core.the_tool_did_not_finish_loading: turn it off means disable,
  not a campaign turn.
- core.the_two_pictures_per_unit_deduplicated: merc is the literal folder
  name, preserved unchanged, not a prose reference to a mercenary.

Batch sources and answers: .cache/fr-settings.json,
.cache/fr-settings-answer.json, .cache/fr-core.json,
.cache/fr-core-answer.json. Merged only through i18n_todo.py.
Five-hour account usage at checkpoint: 81% remaining.

## Checkpoint 2026-10-26, Transfer and Unit Editor

1,334/9,605 done, 8,271 missing, 0 stale/extra. Added 727 strings:
transfer (371), editor (313) and edrecruit (43), all complete. All translated
entries pass check_catalogue with the live termbase; termbase completeness
and git diff --check pass. Native and visual UI review remain pending.
French stays in dev/i18n; no promotion. Next: edusort, compare and undo,
then changes and bmdb. Continue through i18n_todo.py only.

All new plural objects include one/many/other. Literal HTML/code fragments,
event handlers, filenames, file-picker filters and placeholders are retained.
Unknown noun placeholders use labels rather than appended French endings.
The split transfer.change_what_comes_across_with_the and
transfer.buttons_and_the_card_boxes_below retain their join around the B badge.
Prendre depuis, Sonder and Utiliser ceux de la base are the corresponding
Transfer labels. Skin means texture in these model-specific strings;
attachment is élément attaché and tier is palier.

Three exact alternate-sense exemptions added (merc is the literal fallback
folder name, not a prose reference to a hired unit):
- transfer.merc_icons_off: mercenary
- transfer.merc_icons_on: mercenary
- transfer.put_the_unit_card_and_info: mercenary

French open term now accepts ouvert (including ouverture) alongside ouvr,
matching the existing note about its different participle stem. This fixes
natural Ouverture… and unité ouverte without changing the preferred verb ouvrir.

Source/answer batches are .cache/fr-transfer-{1,2,3}[-answer].json,
.cache/fr-editor-{1,2,3}[-answer].json and .cache/fr-edrecruit[-answer].json.
Refusals from earlier batches were corrected by later batches; fresh Transfer
export was empty and all 313 editor IDs are present. Check the catalogue state
for authoritative progress rather than re-merging an earlier answer file.
Files changed this continuation: dev/i18n/fr.json, dev/i18n/fr.source.json,
dev/i18n/fr.md and web/i18n/termbase.json. No application code changed.
Five-hour account usage at checkpoint: 72% remaining.

## Completion run, 2026-10-26 (finished)

User requested completion and explicitly authorized going past the usage guard
for this run. The French catalogue is now complete and promoted as a draft:
web/i18n/fr.json, 9,605/9,605 IDs, zero missing, stale or extra. Source hashes
remain in dev/i18n/fr.source.json. No native-speaker review is claimed.

Validation: full catalogue zero problems; termbase 189 terms / 16 languages /
zero problems; tests.test_i18n 37/37; tests.test_web_modules 120/120;
git diff --check clean. Source-hash stale detection also passed with an
in-memory English change, without touching en.json on disk.

Home, Settings, Transfer and the campaign map were walked at desktop and
375 px. The broader module review and its limits are recorded in fr-review.md.
The picker was verified against the promoted catalogue and offers French once,
as Français (French) - brouillon. Temporary preview forcing was confined to
.cache/fr-preview.py; no user language preference was changed for this QA.

Narrow-layout repairs in web/index.html: Home cards and setup steps wrap;
Armory's transform controls wrap without page overflow; My Changes' comparison
selectors stack with readable widths. Corrected static count labels to avoid
1 unités / 1 inconnus, and translated the builder's WHEN / IF / DO headings.

French termbase stems now accept transfert, généraux, ouvert/ouverture,
tours de guet and suppression. The preferred terms themselves are unchanged.
Exact exception evidence and native-review terminology are in fr-review.md.
Existing source-side English diagnostics/layer names remain documented there.

All translations were checked merges through i18n_todo.py. Reuse of 206 exact
English/French pairs is recorded in .cache/fr-reuse-provenance-206.json.
Batch source/answer files remain in .cache/fr-*.json; old answer files can
contain subsequently corrected refusals, so do not re-merge them blindly.

No release was cut and no commit was created. Russian draft files, its prior
termbase changes and unrelated user files were left in place. Remaining work
for this language is native-speaker review, not additional catalogue entries.
