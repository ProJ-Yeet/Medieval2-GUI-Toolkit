## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` **from the repo root**
  (`D:/College/Coding 2/Unit Transfer`), never from `main/`. There is one graph
  and it lives at the root; running it from `main/` builds a second copy of the
  same tree. AST-only, no API cost.

## Which document to open

| You want | Read |
|---|---|
| where the work stands, what is next | `main/docs/STATE.md` |
| what is left to build, the locked decisions | `main/docs/ROADMAP.md` |
| a finished phase's write-up, and why a rule is a rule | `main/docs/ROADMAP_ARCHIVE.md` |
| how a release is cut | `main/docs/RELEASE.md` |
| a stage from before 2026-08-08, or a file format | `main/docs/HANDOFF_ARCHIVE.md` |

`RELEASE.md` is the only prose copy of the release rules. `STATE.md` holds the
live numbers (current 2.x, current beta, which line is next) and nothing else
about releasing. Do not restate either one somewhere else.

## Delegation

This project has subagents in `.claude/agents/`. Five of them run on **Haiku**
and one on **Sonnet**. Use them: they do the reading, and only their summary
comes back into this context, so the expensive model spends its tokens on the
decision rather than on the output of a grep.

| agent | model | hand it |
|---|---|---|
| `suite-runner` | haiku | running one suite or all 103, and reporting what failed |
| `scout` | haiku | "where does X live", "what calls Y", "what would a change to Z touch" |
| `doc-digest` | haiku | a question answered out of STATE.md, ROADMAP.md, RELEASE.md or the release notes |
| `mod-probe` | haiku | what the installed mods' own data files actually contain |
| `release-check` | haiku | verifying a release against the strict rules, before and after the build |
| `patch-hand` | sonnet | a mechanical edit that is already fully specified |

**Delegate when** the job is self-contained, the output is far larger than the
answer, and a stale or slightly clumsy result is cheap to spot. Test output,
greps across 100k lines, long documents and mod data are all of that.

**Do not delegate** the decision itself - what to build, what a failure means,
how a release is worded, anything touching `STATE.md`, `ROADMAP.md` or the
release notes, and anything that needs this conversation's history to make
sense. An agent starts cold: if briefing it costs more than doing the work, do
the work.

Brief an agent with the whole task in one message, including paths and the shape
of the answer you want. Run independent agents in parallel in a single message.
To continue with one that is already running, `SendMessage` to it by name rather
than spawning a second.
