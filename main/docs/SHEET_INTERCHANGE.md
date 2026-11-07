# Sheet interchange

Open Unit sheets, then Import/export. CSV, XLSX and keyed Fynn EDU JSON imports
use the same explicit mapping and preview flow. Choose a view and header row for
each worksheet to use, map the columns, click Preview mapped IDs and fields,
review the IDs, before/after values, ignored rows and formula issues, then Stage.
Other worksheets can be skipped. Nothing is staged by selecting a file or making
a preview. Staging saves one undoable project change. Native changes still require
the existing EDU review and Apply; their backup and Log Undo path is unchanged.

The sheets window also has a collapsible Sheet help and examples section. For
example, filter Tier equals T1, select matching rows and preview an attack
increase of 1. Review the target count before confirming. Arrow keys and a
tab-separated rectangular paste use the selected cell as the anchor. Sheet
undo/redo restores project edits; Log Undo restores applied game files.

The preview token covers the file, mappings, project revision and native source.
Changing any of them requires a fresh preview. A refused import preserves the
previous project, including staged edits. Imports merge by exact live EDU type ID
or a complete rule key, never by row order. Duplicate unit IDs, duplicate rule
keys, duplicate field targets across sheets and invalid typed edits are refused.
No ID is inferred from a translated name, sort number, position or group title.
Unmatched IDs, separator rows and incomplete presentation keys are reported and
ignored; they do not create units or rules.

## Mappings and workbook versions

The mapper shows each source column with its one-based position, so identically
named headers remain distinguishable. Nothing automatically renames a header.
In the API, `mapping` maps a target field to a zero-based source column index;
an exact unique source header string also works. Duplicate header strings are
refused unless selected by index. An array of indices explicitly combines split
columns into one list field, in that order. Selecting the same list target in
several UI column menus creates this array. Scalars cannot consume several
columns. Rows are joined by ID even when worksheets have different lengths,
orders and group separators.

These examples describe choices, not automatically selected defaults:

| Source shape | Source header | Target |
| --- | --- | --- |
| Base stats `(20)` | `A` (column B) | `id` |
| Base stats `(20)` | `Race`, `Column 3`, `925` | `Unit Race`, `Tier`, `recruit_cost` |
| Base stats `(17)` | `A` (column B), `Tier`, `Campaign cost` | `id`, `Tier`, `recruit_cost` |
| Converter/native shape | `type`, `Tier`, `Campaign cost` | `id`, `Tier`, `recruit_cost` |
| Either Base stats shape | `Faction`, `attack`, `Attack Delay` | `Main Faction`, `attack`, `attack_delay` |
| Either Base stats shape | `Armour`, `Defence`, `Shield` | `armor`, `defense`, `shield` |
| Either Base stats shape | `Upkeep`, `Recruitment` | `upkeep`, `recruit_turns` |
| Attributes | `type` | `id` |
| Attributes | `attributes_1` through `_11` | `attributes`: columns 3 through 13 |
| Attributes | `stat_pri_attr_1` through `_5` | `pri_attributes`: columns 14 through 18 |
| Attributes | `stat_sec_attr_1` through `_4` | `sec_attributes`: columns 19 through 22 |
| Soft stats | `type`, `fmt_close_side`, `fmt_close_front` | `id`, `close_side`, `close_front` |
| Soft stats | `fmt_loose_side`, `fmt_loose_front`, `fmt_ranks` | `loose_side`, `loose_front`, `ranks` |
| Soft stats | `fmt_type_1` | `formation` |
| Soft stats | `ground_scrub`, `ground_sand`, `ground_forest`, `ground_snow` | `scrub`, `sand`, `forest`, `snow` |
| Soft stats | `mount_effect_1` through `_4` | `mount_effect`: columns 14 through 17 |
| Soft stats | `recruit_priority` | `recruit_priority` |
| Classification CSV | `Name`, `Unit Race`, `Tier`, `Main Faction`, `AOR` | `id`, then same metadata names |
| Fynn keyed EDU | `Name` (the JSON key), an explicitly selected classification column | `id`, the chosen metadata field |
| Replenishment | `Tier`, each supplied race endpoint | `Tier`, the chosen endpoint name |
| Experience or pool | `Unit Race`, `Category`, `BarracksTier`, `T0` through `T4` | same rule column names |

Rule mappings use the complete keys listed above and explicit numeric target
names. New endpoint names can be entered in the mapper. Existing omitted rule
columns and other rule rows survive. Rule IDs are reused by key, independently
of row order; new keyed rows receive deterministic IDs. Empty rule cells remain
blank, distinct from zero. An incomplete presentation key is ignored, while a
duplicate complete key or invalid numeric cell refuses the whole import.

Only header shapes are copied into `tests/fixtures/sheet_workbook_headers.json`.
Test rows are synthetic. The original workbooks and converter sources are read
only. In particular, `(17)` still has `A`, even though the converter expects
`type`. Numeric tier annotations are preserved as entered; there is no implicit
conversion of `1` into `T1`. Fynn native-stat objects are retained as extras unless
an actual flat typed native column is explicitly mapped. They never replace
native fields just because their source names resemble converter output.

Unmapped columns remain project extras, including duplicates and blanks. Duplicate
or empty header labels are qualified by column letter, with collision avoidance.
Unit extras are visible through Show imported columns and survive native-header
exports. Rule extras survive both export layouts without becoming numeric rules.
`Weapon`, `Locked morale`, `fmt_type_2` and unrecognized fields can stay as extras;
they are not invented native edit targets. Unmapped native tuple members,
unknown attributes and hand-written comments remain owned by the native patcher.

## Blanks, zero and clearing

- An omitted column never edits its field. An empty mapped native cell means
  unchanged, rather than a converter default or field deletion.
- `0` is a value. It survives CSV/XLSX import, preview, staging and export.
- Empty mapped classification cells clear that annotation explicitly.
- A list in one cell uses comma-separated values or a JSON array. `[]` clears it.
  For split lists, blank cells are ignored; an entirely blank group is unchanged.
  Explicit `no` or `[]` with no other entries clears the list, matching the native
  list vocabulary. A clear is exported explicitly, so it remains cleared after
  reimport. Absent native lists remain blank and do not create default fields.
- Required tuple members cannot be removed by importing a blank. Use the existing
  typed native editing controls for supported field removals.
- List order and duplicate native members survive import and ordinary edits.
  Deduplicate is an explicit mass-edit operation. Gunpowder weapon tuples keep
  their optional firing effect when reading or editing minimum attack delay.

## Formula subset

Formulas are derived columns, never native or classification edit values. Leave
formula columns unmapped. The evaluator accepts finite numeric constants,
parentheses, unary plus/minus, `+`, `-`, `*`, `/`, and same-worksheet A1 references
with optional `$` anchors. For example `O3+X3+0.8*Y3+Z3`, `L3*2.5` and
`AE3/(O3+X3+0.8*Y3+Z3)` work when all referenced cells are populated numeric
inputs. Dependencies may themselves be supported formulas. No Python `eval`,
Excel engine, executable, macro or external link is invoked.

Functions (including SUM), ranges, cross-worksheet references, named ranges,
structured table references, shared/array/data-table formulas, comparisons,
strings and all other syntax are unsupported. Formula length is bounded to
1,024 characters, AST size to 64 nodes and dependency depth to 64. Cycles,
division by zero, nonfinite results and missing/non-numeric inputs yield an
unavailable derived value, never zero. Blank references never become zero.

Preview, reopened sheet responses and exports expose issues by worksheet, cell,
formula text and code. `unsupported_formula`, `cyclic_formula`, `missing_input`,
`division_by_zero` and `nonfinite_formula` explain unavailable results.
`missing_cache` reports a missing cached value even for a formula we can safely
compute. `stale_cache` reports a numeric cache that disagrees with our supported
calculation. Unsupported caches are never used as computed values, and their
freshness cannot be verified. Supported derived columns recalculate against
current staged mapped values on query and export, using each original ID join.

## Export choices and limits

Export this sheet view supports classifications, Base stats, Attributes, Soft
stats and each of the three rule tables as CSV or XLSX. Exports include all rows
of that view, not just the displayed page or filtered selection. Native headers
produce a current keyed table plus extras, with JSON arrays for lists. Base stats
also includes the four configured comparison columns as computed values.
Imported layout retains that view's selected header row, source column positions,
unknown columns and presentation rows, updating mapped fields by ID. Importing
CSV necessarily gives the layout the worksheet name `CSV`. If an edited list
exceeds its old split-column capacity, imported-layout export refuses to truncate
it; choose native headers to export the complete list.

Choose Computed values for CSV or XLSX. Unsupported values are blank and the
download response reports the formula issues. To retain supported formulas,
explicitly choose XLSX, Imported headers and layout, and Supported formulas.
The writer preserves only successfully evaluated formulas at their original
coordinates and writes current cached computed values. Unsupported formulas
are omitted and reported. Native-header exports always use computed values;
requesting formulas with that layout is refused, preventing references from
silently moving to different columns. No macros, external links, styles or Excel
table/validation objects are copied into the new workbook. This is data
interchange, not an Excel formatting round trip.

The standard-library reader resolves workbook relationships, shared and inline
strings and actual populated cells. It never iterates the declared dimension or
materializes formatted empty rows. ZIP contents are never extracted. Inputs have
size/cell bounds (20 MB compressed, 80 MB aggregate uncompressed, 250,000 populated
cells), reject XML entities and external worksheet relationships, and do not run
the supplied scripts. Legacy project JSON and EDB snapshot comparison remain
separate import choices; the mapping route is used for CSV, XLSX and Fynn EDU.
The former direct CSV/rule/Fynn EDU HTTP import action now refuses imports that
bypass this preview flow. Pure legacy adapter helpers remain available for
offline compatibility callers; the application's validated service owns staging.

The recruitment grid is read-only and is outside the CSV/XLSX mapping views.
Use the separate Balance EDB export for recruitment. A packed roster can be read
without extraction into a real mod, but native Apply requires an extracted EDU;
use disposable copies for verification. Missing vanilla classifications are
reported rather than inferred from the supplied Middle-earth profile.

Phase 116 checked copied user snapshots and copied vanilla packed EDU/EDB data,
including CSV/XLSX round trips for all seven editable views. The supplied (20)
and (17) workbooks were read; rebuilt2.xlsx exceeds the documented archive-size
bound and is refused. Synthetic formatted empty rows also have a bounded import
test. Details, timings and remaining browser checks are in CODEX_HANDOFF.md.
No original workbook modification, Excel/LibreOffice recalculation, interactive
browser verification or in-game behavior is claimed.
