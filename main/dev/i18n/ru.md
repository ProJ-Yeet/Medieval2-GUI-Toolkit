# Russian (`ru`) - how the catalogue is written

Phase 88m. Work in progress stays in `dev/i18n/ru.json` until the whole
catalogue passes the Phase 88d promotion checks. It is not offered in Settings.

## Workflow

Run from the repository root:

```text
python main/dev/checks/i18n_todo.py ru
python main/dev/checks/i18n_todo.py ru --batch NS --max 200 --out .cache/ru-batch.json
python main/dev/checks/i18n_todo.py ru --merge .cache/ru-answer.json
```

Translate complete namespaces where possible. Fix every refused string and
merge it again. Never bypass the checker. Source hashes are maintained by
the merge command. Only promote once nothing is missing or stale, the full
checker passes, and Home, Settings, Transfer and the map have been inspected.

## Voice and typography

- Plain Russian for a person editing a mod. Instructions use polite plural
  imperatives: «Выберите мод», «Закройте игру». Use lowercase «вы».
- Buttons use infinitives: «Сохранить», «Добавить», «Перенести»; preserve
  established platform labels such as «Отмена», «Обзор», «Параметры».
- Sentence case, full sentences for explanations, concise status messages.
- Use «…» for prose quotes and the single-character ellipsis. Preserve
  symbols, keyboard shortcuts, arrows and HTML attributes. No em dashes.
- Follow the termbase's е spellings, including «наемник», «приближенный».
- Do not inflect an unknown placeholder. Prefer a label followed by its
  value, or a construction that does not depend on the value's gender.
- Product names, file names, code names, keywords, placeholders and the
  contents of `<code>` stay unchanged. Translate module names by function.

## Terms

Use `web/i18n/termbase.json`'s Russian column, included in each exported
batch. In particular: unit = отряд; faction = фракция; settlement = поселение;
trait = черта; ancillary = приближенный; trigger = триггер; entry = элемент;
record = запись; log = журнал; transfer = перенос; tile = тайл.

Do not add an exemption simply to pass a check. If the English matches a
term in a different sense, record the specific ID and reason below.

## Plurals

Every plural has `one`, `few`, `many`, `other`. For example: «{count} отряд»,
«{count} отряда», «{count} отрядов», «{count} отряда». The `other` form is
also used for fractional numbers. Check 0, 1, 2, 5, 11, 21, 22, 25 and 1.5.
An explicit `zero` may be retained when English has one. Preserve every
placeholder and the source's HTML structure.

## Review notes

This is a model-written draft. A Russian-speaking Medieval II modder must
review terminology and phrasing before it is marked reviewed.

- The boot error is split across seven strings in the source. Read the
  fragments together; the Russian clauses follow the same DOM order.
- `app.shared_cards_title`: English "tiles" means unit-card tiles, not
  squares of the campaign map. Russian uses «карточки» (tile exemption).
- `home.mounted_pack`: "mounted" means an attached archive, not a riding
  animal. Use «подключенный» (mount exemption).
- `settings.and_more_characters_in_the_diagnostic`: "characters" means
  text characters, not people. Use «символов» (character exemption).
- `settings.use_the_base_units_soldier_line`: `soldier` is the EDU keyword
  naming the line, preserved literally (soldier exemption).
- `core.every_model_a_mod_ships_the`: "ships" means includes, not vessels
  (ship exemption).
- `core.the_tool_did_not_finish_loading`: "turn it off" means disable an
  extension, not a campaign turn (turn exemption).
- `core.the_two_pictures_per_unit_deduplicated`: `merc` is a literal folder
  name, not the label for a mercenary (mercenary exemption).
- Russian termbase stems: `general` now uses «полковод», matching both
  «полководец» and «полководцы»; `port_verb` uses «портир», matching
  «портировать» and «портируйте». These are inflections of the same terms.
- Health (the module) is «Проверка мода», not a person's health.
- `codeview.every_string_here_is_stored_as`: characters are text symbols,
  not people (character exemption).
- `changes.turn_off`, `changes.turn_off_putting_the_original_records`,
  `changes.turn_on`: enable/disable a version, not campaign turns (turn).
- `rawtext.pick_a_file_on_the_left`: "models" means represents a file
  format, not 3D models (model exemption).
- `maplabels.character`, `maplabels.port`: literal internal key prefixes
  `character:{line}` and `port:{region}` (character / port_verb exemptions).
- `maplabels.port_2`: harbor noun «Порт», not porting data (port_verb).
- `voices.no_name_call`: "general" means shared, not commander (general).
- `voices.own_compiled`, `voices.own_note`: events.dat/events.idx are literal
  sound-cache file names, not campaign events (event).
- «Представление» for a unit's "name call" needs native-speaker review.
- `changes.count_of_what` keeps the supplied noun separate from the count;
  the code can supply an English noun, which cannot be inflected here.
- `ancillaries.not_found_in_data_ui_ancillaries`: the term is inside a literal
  folder path, `data/ui/ancillaries` (ancillary exemption).
- `factions.bring_art`, `factions.bring_frame_units`: frame is a base faction,
  not an animation frame (frame exemptions); use «основа».
- `family.on_map`: preserve the `character` file keyword (character).
- `facaudit.world_maps_campaign`: preserve the literal path (campaign).
- `editor.soldier_replace`, `transfer.not_a_crash_the_engine_animates`:
  preserve the `soldier` file keyword (soldier).
- `transfer.merc_icons_off`, `transfer.merc_icons_on`,
  `transfer.put_the_unit_card_and_info`: `merc` is a literal folder name
  (mercenary).
- `transfer.mounted_engine` and
  `eng.transfer.engine_skeleton_the_mounted_engines_class`: mounted engine
  means an engine carried or drawn by animals, not a standalone mount
  (mount exemption); rendered «машина с упряжью» for native review.
- `eng.transfer.projectile_model_cas_files_were_copied`: missile means the
  projectile itself here, not ranged weapons in general (missile).
- `eng.stringsbin.a_single_string_cannot_exceed_65535` and
  `eng.stringsbin.a_string_says_it_is_characters`: text symbols (character).
- Unit/editor terms: skin = «облик», tier = «ступень», building line =
  «цепочка зданий», attachment = «крепление»; trait epithet = «прозвище».
- Native review: faction-audit gap = «пробел»; head modifier = «Модификатор
  главы»; triumph value = «Значение триумфа».

## Checkpoint

2026-10-25: Russian translation complete9,605/9,605, zero missing/stale/
extra, zero checker errors. Added824 final strings. All helpers stopped.
Catalogue remains in dev/i18n/ru.json pending full UI QA; not in Settings.
French started next:80 initial boot/common strings in dev/i18n/fr.json.

Final checks: test_i18n37/37, test_termbase27/27, all378 plurals valid for
nine representative counts; source hashes current, no extra IDs/em dashes,
draft isolation confirmed. Read ru-review.md for exemptions and terminology.
Home/Settings/Transfer/map preview inspected at605px; complete screen-by-
screen desktop and375px review still pending. Native review also pending.
Map layer names arrive as English backend labels; recorded in review notes.

Next Russian step: complete UI QA, then i18n_todo.py ru --promote to offer
as draft, retaining source hashes and review status. French workflow and
voice in fr.md; continue common/i18n then core UI. No commit/release.
