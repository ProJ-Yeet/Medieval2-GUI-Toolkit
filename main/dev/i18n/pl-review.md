# Polish repair review, 2026-10-30

## Result and availability

The repair pass and direct semantic review are complete for all 9,739 catalogue
IDs and their forms, including 382 plural objects. Coverage, source hashes,
terminology and syntax checks are clean. No unresolved catalogue repair finding
remains from this pass. Polish stays an unoffered draft in `dev/i18n/pl.json` under
the user's earlier no-shipping instruction; no release or promotion was made.
Native-speaker certification has not been obtained.

The earlier coverage-only completion claim was wrong: the parked draft contained
lost instructions, reversed meanings and broken code. This pass read the text
against English and repaired meaning, grammar and literal syntax. 4,875 IDs differ
from the parked HEAD, including 106 newer entries. That count includes mechanical
format repairs and is not a count of entirely new translations.

## Review coverage

Three authorized parallel reviewers read disjoint assignments of 3,044, 3,070 and
2,603 IDs, including every plural form. The primary editor reviewed the other 937
original IDs and 79 Home readiness messages; an independent reviewer then read
those 1,016 current entries and supplied nine further repairs. Six final UI gaps
were authored separately (card status/counts, cache labels, missing-model suffix
and error). The union of the saved reviewed-ID manifests and final additions was
checked against English: 9,739 reviewed, zero omitted.

Local batch maps and exact manifests are in `.cache/pl-review3-*`. They are working
records; this document records the durable result. The catalogue and its explicit
`_exempt` map remain authoritative. Exemptions cover contextual meanings and
literal identifiers, for example ship as a distribution verb, turn as model
rotation, or soldier/dictionary used as field names. They do not disable literal
syntax or placeholder checks.

## Functional localization repairs

Translated edit keys and HTML attributes could break controls. `ttCode` now fills
source templates for internal keys, selectors, bindings and event handlers, even
under pseudo-localization. `ttTitle` retains the source disabled flag/action code
and translates only the tooltip value, escaping quotes. Native title/accessibility
prose inside HTML may be translated; unrelated attributes must remain exact.

Home's file/readiness labels and notes were outside the catalogue; 79 messages now
use the normal annotated engine-message path. Card status/counts and cache labels
were also extracted. Display names for cache targets are kept separate from file
path tokens, so Polish cannot change export_units/export_buildings paths. Empty
states and map label counts use translated messages. The 3D viewer now translates
its missing-file suffix and annotated geometry error, including the manual-fetch
error path that previously skipped `i18nFromServer`.

## Verification

- `tests.test_i18n`: 45/45, covering source extraction, parameter agreement,
  real settlement controls reading/writing actual engine keys, pseudo-locale
  invariance, action/tooltip syntax, Home readiness annotations and cache paths.
- `tests.test_i18n_integrity`: 14/14, including placeholder occurrences,
  literals, native file filters, internal keys, handlers and native tooltip text.
- `tests.test_termbase`: 31/31, including Polish inflections and both pseudo-locales.
- `tests.test_web_modules`: 124/124; all 101 modules parse together.
- Full parked-catalogue glossary check: zero problems.
- Integrity and strict path/markup audit: zero problems.
- Real-catalogue Polish plural runtime probes: 3,820 passed (382 entries × ten
  count samples, including zero, teens, twenties and fractions).

The isolated browser preview used synthetic mods only. Home readiness, Settings,
Unit Editor, Transfer and Campaign Map were inspected at desktop width. At 375 px,
the map's document width was 365 px without page overflow; the earlier Guided
check also confirmed a field edit updated the raw EDU working copy and Ctrl+Z
restored it. Final UI repairs addressed interpolated grammatical cases, native
tooltips, card status, map counts and missing-model errors. Preview evidence is
under `.cache/pl-uiqa-final/` and `.cache/pl-uiqa-2026-10-30/`. No Apply/Save was
used to modify a mod. Saved user preferences were not changed.

## Limits

Direct semantic review by coding agents is not native-speaker sign-off. Engine
keywords, enum values, mod-authored unit descriptions and paths remain literal.
Raw transfer-plan diagnostics and server logs still display English; this pass
does not certify those uncatalogued diagnostic reports as localized. Browser
checks used small synthetic fixtures, not an exhaustive playthrough of every
mod or edit mode. Keep these limits visible when deciding whether to offer or
ship the draft; clean structural checks alone are insufficient evidence.

Catalogue SHA-256: `b703dad75efa70cf322a99176f83b31b5467dbf62afc1e13e8a044cfb75bd414`.
