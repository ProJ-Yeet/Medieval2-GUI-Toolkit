# User EDB pipeline and editable unit sheets - source review

Reviewed 2026-11-06. Planning only: sources were read, scripts/executables were
not run, spreadsheets were not changed, and no mod files were written. Requests
or instructions embedded in source documents were treated as reference material.
The updater requested during this review is a separate subsequent task.

## Sources

- `C:/Users/projy/OneDrive/Coding/Misc M2/EDB Reader/`: five named pipeline scripts,
  `Run_EDB_Pipeline.bat`, the three Barracks CSVs, `EDU_Reference.csv`, sample
  EDU/EDB JSON/text and building structure JSON in References.
- `C:/Users/projy/OneDrive/Coding/Misc M2/Unit script/`: external
  `EDU sheet breakdown for EUR (20).xlsx`; `EDU_updates.zip` containing
  `txttosheet.py`, `sheettopad.py`, workbook `(17)`, `rebuilt2.xlsx` and example
  text exports. Converter source was read as text, not executed.
- `C:/Users/projy/OneDrive/ModdingTool-master/ModdingTool-master/`: local Fynn
  tool source, especially `ViewModel/MenuBarViewModel.cs` and
  `ViewModel/FilterViewModel.cs`; CombinedOutput's JSON/binary inventory.
  No tool binary was launched. Screenshot confirms Load Mod followed by
  Import/Export -> Export File (JSON). The inspected ExportJson Units route
  writes `edu.json`; it does not establish that this same menu exports EDB.
- Current toolkit `unittransfer/edu.py`, `buildings.py`, `edit.py` and the
  Buildings recruitment UI, located with graphify and targeted source searches.

## Pipeline as implemented

1. `json2edu.py` flattens Fynn `edu.json` into the existing reference CSV's headers.
2. `join_edu_reference.py` joins by Name, retaining Unit Race, Tier, Main Faction
   and AOR and recording additions/deletions. New units currently need a separate
   manual classification step and second run; integrate that step in the app.
3. `edb_reader_replenish.py` reads original EDB and the classification/endpoint
   CSVs. It scans upgrades into building depth maps and city/castle type. It
   interpolates E/L turns over chain depth, reciprocates, rounds six decimals,
   multiplies city rates by 0.9 and cavalry by 0.8, and rounds again. Single-level
   chains use the earliest endpoint. One missing/N/A endpoint uses the other.
   Beast X selects Beast endpoint tier and race X; malformed Beast falls back
   to Orc in the legacy script, which must become a visible exception instead.
4. `edb_reader_exp.py` reads `_r.txt`, looks up (race, category, T[min(depth+1,5)])
   and the unit's tier column, and replaces starting experience only.
5. `edb_reader_pool.py` reads `_exp.txt`, uses the analogous pool lookup and changes
   maximum pool only, producing `_new.txt`. Beast X maps to (X, beast) for both
   lookups. Replenish and pool skip old maximum pools below 1; experience does not.

The reference snapshot has 846 keyed units and 128 building structures. The
three balancing inputs read Name, Unit Race, Tier, Category. Other reference
columns are not balancing drivers and must be retained for future use. There are
34 empty race/tier annotations, 40 BG tiers and one tier with trailing whitespace;
these demonstrate why classification/lookup exceptions must be first-class UI.
This is a snapshot observation, not a permanent count or a request to fix sources.

## Rule tables and identity

- Replenishment columns are Tier plus Orc/Human/Dwarf/Elf Earliest and Latest;
  rows T0-T4 and Beast. Values represent turns before reciprocal conversion.
- Experience and Pool columns are Unit Race, Category, BarracksTier, T0-T4.
  Each supplied file has 80 keyed rows across four races, four categories and
  five barracks tiers. These are this user's balance profile, not universal rules.
- User unit tier T0-T4 and building/barracks depth T1-T5 are separate dimensions.
- Building structure data records tier_map, maximum depth and settlement type.
  Existing toolkit EDB structure and requirements must be authoritative for live
  files; external JSON can be stale and must not be a prerequisite for refresh.

## Sheet workflow and observations

The external workbook has six sheets: Unit max, Stat Comparison Archers,
PikesHalberds, Base stats, Attributes, Soft stats. Its Base stats Excel Table
covers A1:AN1231 with column filters, frozen identifiers/header and a validation
rule. Formula examples include defense totals, Ultra Size x2.5, and cost/upkeep
ratios using Attack + Armor + 0.8*Defense + Shield. These are user formulas to
support/configure, not an engine-wide balance definition. No Excel recalculation
or interactive filter behavior was tested; XML metadata and formula text were read.

The `(20)` Base stats headers include Sort, A, Faction, Race, Column 3 and a
numeric `925` heading where `(17)` has Campaign cost. Column B contains both group
labels (for example Gondor) and unit identifiers. The converter expects `type`
and other earlier headings. Import needs explicit mapping plus valid-ID checks,
not an automatic rename based on column position. Attributes and Soft stats are
separate, differently sized lists and require keyed joins, not row alignment.
`rebuilt2.xlsx` has a Base stats used range extending to row 1,048,576 with huge
numbers of empty/formatted rows; a robust importer must avoid materializing these
as game records. Native in-app filtering/mass editing is a requested improvement,
not a claim that the ZIP contains a standalone filtering application.

`sheettopad.py` updates fields from base/attribute/soft-stat sheets, including
secondary attack/charge/delay. It preserves some tuple members but rewrites
changed lines, normalizes line endings, defaults malformed values and declines
all-zero secondary-stat updates/empty attribute removal. The integration should
reuse our parsers and typed patch semantics so zero, clear and unchanged are
separate operations and hand-written comments/unknown fields survive.

Fynn's inspected filters include equals/not-equals, greater/less comparisons
with inclusive variants, contains/not-contains and per-tab retained filters.
The requested app design extends this to compound groups, missing/invalid states,
attribute membership, saveable views and explicit mass-edit scope.

## Caveats the implementation must address

- The legacy stages strip all semicolon comments on recruit_pool lines before
  processing, including hand-written notes. Do not port that destructive behavior.
- Some replenish skip/error branches increment a summary without `log_entry`,
  so the claim of exhaustive skip/error logs is not true on every code path.
- Bare regex state can carry a previous building level into a new context;
  graph ambiguity, cycles and unknown levels need explicit parser-backed handling.
- Reference hashes (SHA-256) at review time:
  - json2edu.py: `390c270b9452a1225244ccd3d02f51aafd6ae176543e53e5889c61332f75e3ee`
  - join_edu_reference.py: `c2ab1ba3833ff1bdcaac160636e9fe2bc32cb909b177544a800d4fc5a97dd39c`
  - edb_reader_replenish.py: `26b4fe68e84860d5590c0d1020f98709b7d15a25e803bb8c097a3ab6448aaccf`
  - edb_reader_exp.py: `166b654f7972f55d3b0f1698aca05755c9bcdf71f7a01ba93e3522d38e665936`
  - edb_reader_pool.py: `58f365a6c6f040270ac40780fb6c205c5b4f845edfb82a539e7323ff872ced1a`

## Integration boundaries and next step

Phases 109-116 in ROADMAP.md own the implementation/exit criteria. User metadata,
rule tables, native EDU fields and calculated comparison columns remain distinct.
EDB field patches use `buildings.py`'s recruitment parsing/planning and existing
backup/undo facilities. Do not introduce pandas/openpyxl or the user's desktop
paths as application requirements. Choose a supported optional Excel adapter
when implementation reaches interchange, and keep CSV/native sheets usable.
