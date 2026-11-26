# The step map

Part of [the Dev loop](../the-loop.md).

The Dev loop has two stages, the Grill and the spec loop, and each stage of the Dev loop holds steps.
Each step reads some of your Steering. This map says which files, and where your team can change what
the step does. [Steering](../steering.md) has the detail on each file.

To see the text a step reads in your repo, with the source of each part, run
`/skillworks:show-steering <step>`. With no step, it lists the steps.

Two kinds of load:

- **Always** means the file is in the Session from its start. `CLAUDE.md` loads, and it imports the
  five rules in `docs/skillworks/rules/`: `comments.md`, `determinism.md`, `file-placement.md`,
  `testing.md` and `words.md`. The map calls these "`CLAUDE.md` and the rules".
- **On demand** means the step's skill reads the file through `steering-file` only when the step
  needs it. A path that ends in `/` means every file in that folder.

`.claude/settings.json` applies to every Session too. Its allowlist decides which tools a Session can
use with nobody watching.

<!-- step map -->
| Step | Stage | Always loads | Loads on demand | What your team can change |
|---|---|---|---|---|
| `grill` | the Grill | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/domain.md`, `docs/skillworks/adr-format.md`, `docs/skillworks/surfaces.md`. Then the glossary and the folder `adr-folder` names, which `domain.md` points at. | The glossary and the ADRs. The grill writes them as words and decisions settle, each ADR in the shape `adr-format.md` gives. The Surfaces in `surfaces.md`, which decide what the grill asks once the design is settled. |
| `gate` | the Grill | The same Session as the grill | Nothing more | Nothing in a file. Your yes or no is the lever. |
| `write-spec` | the Grill | `CLAUDE.md` and the rules | `docs/skillworks/rules/testing.md`, `docs/skillworks/loop.json`, `docs/skillworks/surfaces.md` | The glossary and the ADRs, which give the spec its words and its decisions. The testing rule, which sets the seams the spec names. The Surfaces in `surfaces.md`, which name the Surfaces section of the spec. |
| `cut` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/issue-tracker.md`, `docs/skillworks/domain.md`. Then the glossary and the folder `adr-folder` names. | "The ticket shape" in `issue-tracker.md`: the size of a ticket, its title and its sections. The glossary and the ADRs, which give the tickets their words. |
| `build` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/issue-tracker.md`, `docs/skillworks/suite.json`, `docs/skillworks/domain.md`, `docs/skillworks/rules/testing.md`, `docs/skillworks/rules/determinism.md`. Then the glossary. | The rules the change must meet, and the checks in `suite.json`. |
| `standards` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/issue-tracker.md`, `docs/skillworks/rules/`, `docs/skillworks/domain.md`, `docs/skillworks/review-standards.md`. Then the glossary. | The rules, and the smells, your checks and "Do not report" in `review-standards.md`. |
| `spec` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/issue-tracker.md`, `docs/skillworks/review-spec.md`, `docs/skillworks/surfaces.md` | "The ticket shape" in `issue-tracker.md`, because the review judges the change by the ticket. The Surfaces in `surfaces.md`, which say where each Surface the spec names lives. Your checks and "Do not report" in `review-spec.md`. |
| `architecture` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/issue-tracker.md`, `docs/skillworks/domain.md`, `docs/skillworks/rules/file-placement.md`, `docs/skillworks/placement-checks.md`, `docs/skillworks/review-architecture.md`. Then the glossary and the folder `adr-folder` names. | `file-placement.md`, the failures, your checks and "Do not report" in `review-architecture.md`, and the commands in `placement-checks.md`. |
| `fix` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/issue-tracker.md`, `docs/skillworks/suite.json`. It acts on the three reports. | The rules the fix must meet. |
| `sweep` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/rules/comments.md` | The keep and cut table in `comments.md`, and `doc-comments`. |
| `suite` | the spec loop | Nothing. No Session runs. | `docs/skillworks/suite.json`, and each Dockerfile a check names as its `image` | Every check, its `ready`, its `ignores`, its `image`, and `runs`. |
| `finish` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/issue-tracker.md`, `docs/skillworks/suite.json` | Nothing. The loop reads back the two conventions in `issue-tracker.md`, so leave them as they are. |
| `deepening-check` | the spec loop | `CLAUDE.md` and the rules | `docs/skillworks/deepening-check.md`, `docs/skillworks/issue-tracker.md`, `docs/skillworks/domain.md`. Then the glossary and the folder `adr-folder` names. | What counts as Strong, your checks, "Do not report" and `limit` in `deepening-check.md`. A `limit` of 0 turns the check off, and it is still a step. |

A judge at the end of the loop that is a step works with `/skillworks:show-steering <step>` like any
other step, such as `/skillworks:show-steering deepening-check`.

The loop runs more than the thirteen steps. What it runs besides them reads Steering too:

| What runs | Always loads | Loads on demand | What your team can change |
|---|---|---|---|
| Landing | `CLAUDE.md` and the rules, in the Session that resolves a conflict | `docs/skillworks/suite.json`, for the Suite again | The checks in `suite.json`. |
| A deepening ticket | What each step above loads, since it is built through them | The same as each step | Nothing in a file. The script writes it from a fixed template, out of one line of the Deepening report's `### Strong` list. |
| The Simplify check | `CLAUDE.md` and the rules | `docs/skillworks/simplify-check.md`, `docs/skillworks/issue-tracker.md` | The four angles, your checks and "Do not report" in `simplify-check.md`. |
| The simplify ticket | What each step above loads, since it is built through them | The same as each step | Nothing in a file. The script writes it from a fixed template, out of every line of the Simplify report's `### Findings` list. |
| The drift check | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/issue-tracker.md`, `docs/skillworks/domain.md`, `docs/skillworks/surfaces.md`. Then the glossary. | The glossary, which judges the names two tickets brought in. The Surfaces in `surfaces.md`, which say where each Surface the spec names lives. |
| The Gap ticket | What each step above loads, since it is built through them | The same as each step | Nothing in a file. The script writes it from a fixed template, out of the drift report's Verdicts and reasons. |
| The Name check | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/issue-tracker.md`, `docs/skillworks/domain.md`. Then the glossary. | The glossary, which decides the word a moved name or a concept named two ways should take. |
| The rename ticket | What each step above loads, since it is built through them | The same as each step | The glossary, whose word each rename takes. The script writes the ticket from a fixed template, out of the Name report's lines. |
| The full run | Nothing. No Session runs. | `docs/skillworks/suite.json` | The checks in `suite.json`. |
| Context backfill | `CLAUDE.md` and the rules | `docs/skillworks/loop.json`, `docs/skillworks/domain.md`, `docs/skillworks/adr-format.md`, `docs/skillworks/suite.json`. Then the glossary and the folder `adr-folder` names. | The shape in `adr-format.md`, which each ADR Draft fills. `adr-folder` in `domain.md`, which says where each accepted ADR goes. It runs once after setup and never in the loop. |

The rules' settings load into every Session, but each one is enforced only once a check exists that
reads it. Until then, `build` and `fix` follow them as prose, and the reviews judge the change by
reading them. `suite` enforces a setting only when a check in `suite.json` reads it, and
`architecture` runs only the commands in `placement-checks.md`. `/skillworks:architecture-tests`
adds those checks.

| Rule | The settings a check enforces |
|---|---|
| `file-placement.md` | `slices`, `concerns`, `max-types-per-folder`, `source-files`, `test-files`, `skip-folders`, `banned-folder-names`, `name-map`, `test-roots`, `test-placement` |
| `determinism.md` | `clock`, `contexts` |
| `words.md` | `banned-words`, `skip-folders` |
| `comments.md` | `doc-comments` |
| `testing.md` | None. No check reads it, so the `standards` review is its only judge. |

The steps, their order and what each one does are Machinery. They are the same in every repo, and no
file changes them. So this map lives here only, and setup copies no map into your repo.
