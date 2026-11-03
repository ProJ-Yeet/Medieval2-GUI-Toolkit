# Translation refresh, 2026-11-03

All seven existing non-English catalogues match the current 10,098 English
entries: zero missing, stale or extra IDs. French, Simplified Chinese and
Turkish remain offered drafts. Russian and Polish remain in dev/i18n and are
not offered or promoted. No release was built.

## Catalogue changes

Compared with the working revision at the start of this refresh:

| Language | Entries added | Existing translations changed |
|---|---:|---:|
| German | 0 | 1 |
| Spanish | 0 | 0 |
| French | 444 | 4 |
| Simplified Chinese | 444 | 5 |
| Turkish | 465 | 218 |
| Russian, unoffered | 444 | 5 |
| Polish, unoffered | 359 | 4 |

The new text covers model imports, the image browser, menu sheets, reports
and answers, faction recolouring and culture changes, campaign-map controls,
garrisons and bulk towns, scripts, appearance, new-unit presets, temple
creation, base-game browsing, file labels, voice transfer, projectile effects
and transfer rollback. Turkish also catches up with text-model and vegetation
conversion. Four changed source templates are refreshed in each affected
catalogue: folder import, report contents and the two 3D-map help messages.

Exact repeated labels reuse the language's existing current translation.
Already-current Polish entries retain their prior reviewed wording.
New and repaired text was written directly and merged through i18n_todo.py,
which validates each answer and records its current English fingerprint.
No translation service was used for this refresh. These remain model-authored
drafts; no native-speaker certification or desktop/narrow-screen visual review
is claimed for this pass.

## Literal syntax repairs

The Turkish audit found 218 integrity flags across 214 existing entries.
Those 214 entries were rewritten, restoring filenames, inline code, engine
keywords, paths, braces, HTML attributes, action handlers and disabled title
syntax. The strict integrity checker now reports zero Turkish problems.
German, Simplified Chinese and Russian also restore the exact source for
modelpicker.data_gfme_data_i_data_part: that entry is internal attribute syntax,
and the runtime deliberately uses the source through ttCode.

The integrity scanner no longer mistakes punctuation such as `<, >` or `<、>`
for HTML. It still detects altered dynamic XML tags, code and attributes.
The text scanner excludes CSS font-family lists and canvas font assignments;
the map's font descriptors had produced false untranslated-prose failures.
Regression checks cover both exclusions and readable font instructions.

## Exact terminology exceptions

The glossary itself is unchanged. New per-entry exceptions have specific
reasons:

- campcreate entries describing a port exempt port_verb: these are harbours,
  not the verb for moving content between mods.
- report.state_open exempts open: a report status, not a command. Spanish's
  existing abierto is retained, with this exception recorded.
- eng.server.model_file_missing exempts ship: supplying a file, not a vessel.
- Russian bmdb.imp_button_title and eng.modfiles.battle_models_bmdb exempt
  standalone battle: the established compound is боевая модель.
- Chinese editor.engine_with_title and eng.modfiles.siege_engines exempt
  standalone siege: the compound is 攻城器械.

Other refusals were resolved with the established glossary wording, not
exemptions. Existing justified exemptions are preserved.

## Verification

- Full coverage/source-fingerprint checks: 10,098/10,098 current in every
  catalogue, no extra IDs.
- Full structural and terminology checks: zero problems in all seven.
- tests.test_i18n: 45/45.
- tests.test_termbase: 31/31.
- tests.test_i18n_community: 11/11.
- tests.test_i18n_integrity: 18/18.
- Actual browser translation runtime in Node: all 395 plural entries in
  each language rendered at 0, 1, 2, 5, 21, 1.5 and 1,000,000 without unfilled
  placeholders, 19,355 successful renderings.
- git diff --check: passed.

The raw strict integrity report retains nine placeholder-multiplicity flags
that have been read and are valid grammatical differences. They are not
suppressed in the checker:

- German minorfiles.pick_a_noun_on_the_left/other uses plural nouns in both
  clauses. The call supplies both noun and nouns.
- Spanish minorfiles.pick_a_noun_on_the_left/many and /other do the same.
- Spanish eng.edit.other_model_entries_also_use_these/one says otra entrada
  rather than printing the number 1; the standard plural validator permits it.
- Spanish guided.steps_of repeats the step naturally: de {step} en {step}.
- French minorfiles.pick_a_noun_on_the_left uses an element-neutral opening
  instruction in all three forms, with the noun retained in the count label.
- Chinese campbrowse.no_files_of_its_own has one CLDR form. It retains why from
  English's singular template; the call always supplies why, even for a list.

Russian and Polish also have zero strict integrity flags. No mod files were
changed during translation or testing. Unrelated Reference deletions and
other pre-existing workspace files were left alone.
