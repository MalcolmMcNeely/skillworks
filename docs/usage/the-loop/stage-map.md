# The stage map

Part of [the Dev loop](../the-loop.md).

Each stage of the loop reads some of your Steering. This map says which files, and where your team can
change what the stage does. [Steering](../steering.md) has the detail on each file.

Two kinds of load:

- **Always** means the file is in the Session from its start. `CLAUDE.md` loads, and it imports the
  five rules in `docs/agents/rules/`: `comments.md`, `determinism.md`, `file-placement.md`,
  `testing.md` and `words.md`. The map calls these "`CLAUDE.md` and the rules".
- **On demand** means a skill reads the file only when that stage needs it.

`.claude/settings.json` applies to every Session too. Its allowlist decides which tools a Session can
use with nobody watching.

<!-- stage map -->
| Stage | Always loads | Loads on demand | What your team can change |
|---|---|---|---|
| The grill | `CLAUDE.md` and the rules | `domain.md`, your glossary, `docs/adr/`, `surfaces.md` | The glossary and the ADRs. The grill writes them as words and decisions settle. The Surfaces in `surfaces.md`, which decide what the grill asks once the design is settled. |
| The gate | The same Session as the grill | Nothing more | Nothing in a file. Your yes or no is the lever. |
| The spec | `CLAUDE.md` and the rules | `issue-tracker.md`, your glossary, `docs/adr/`, `surfaces.md` | The glossary and the ADRs, which give the spec its words and its decisions. The Surfaces in `surfaces.md`, which name the Surfaces section of the spec. |
| The tickets | `CLAUDE.md` and the rules | `issue-tracker.md` | "The ticket shape" in `issue-tracker.md`: the size of a ticket, its title and its sections. |
| `build` | `CLAUDE.md` and the rules | `domain.md`, your glossary, and `suite.json` when it runs `skillworks-suite` | The rules the change must meet, and the checks in `suite.json`. |
| `standards` | `CLAUDE.md` and the rules | `review-standards.md`, your glossary | The rules, and the smells, your checks and "Do not report" in `review-standards.md`. |
| `spec` | `CLAUDE.md` and the rules | `issue-tracker.md`, `surfaces.md`, `review-spec.md` | "The ticket shape" in `issue-tracker.md`, because the review judges the change by the ticket. The Surfaces in `surfaces.md`, which say where each Surface the spec names lives. Your checks and "Do not report" in `review-spec.md`. |
| `architecture` | `CLAUDE.md` and the rules | `domain.md`, your glossary, `docs/adr/`, `review-architecture.md`, `placement-checks.md` | `file-placement.md`, the failures, your checks and "Do not report" in `review-architecture.md`, and the commands in `placement-checks.md`. |
| `fix` | `CLAUDE.md` and the rules | Nothing more. It acts on the three reports. | The rules the fix must meet. |
| `sweep` | `CLAUDE.md` and the rules | Nothing more. `comments.md` is already loaded. | The keep and cut table in `comments.md`, and `doc-comments`. |
| `suite` | Nothing. No Session runs. | `suite.json`, and each Dockerfile a check names as its `image` | Every check, its `ready`, its `ignores`, its `image`, and `runs`. |
| `finish` | `CLAUDE.md` and the rules | `issue-tracker.md` | Nothing. The loop reads back the two conventions in `issue-tracker.md`, so leave them as they are. |
| Landing | `CLAUDE.md` and the rules, in the Session that resolves a conflict | `suite.json`, for the Suite again | The checks in `suite.json`. |
| The drift check | `CLAUDE.md` and the rules | `issue-tracker.md`, your glossary, `surfaces.md` | The glossary, which judges the names two tickets brought in. The Surfaces in `surfaces.md`, which say where each Surface the spec names lives. |
| The Gap ticket | What each step above loads, since it is built through them | The same as each step | Nothing in a file. The script writes it from a fixed template, out of the drift report's Verdicts and reasons. |
| The Name check | `CLAUDE.md` and the rules | `issue-tracker.md`, `CONTEXT-MAP.md`, your glossary | The glossary, which decides the word a moved name or a concept named two ways should take. |
| The rename ticket | What each step above loads, since it is built through them | The same as each step | The glossary, whose word each rename takes. The script writes the ticket from a fixed template, out of the Name report's lines. |
| The full run | Nothing. No Session runs. | `suite.json` | The checks in `suite.json`. |

The rules' settings load into every Session, but each one is enforced only once a check exists that
reads it. Until then, `build` and `fix` follow them as prose, and the reviews judge the change by
reading them. `suite` enforces a setting only when a check in `suite.json` reads it, and
`architecture` runs only the commands in `placement-checks.md`. `/skillworks:architecture-tests`
adds those checks.

| Rule | The settings a check enforces |
|---|---|
| `file-placement.md` | `slices`, `concerns`, `max-types-per-folder`, `source-files`, `test-files`, `skip-folders`, `banned-folder-names`, `name-map`, `test-roots` |
| `determinism.md` | `clock`, `contexts` |
| `words.md` | `banned-words`, `skip-folders` |
| `comments.md` | `doc-comments` |
| `testing.md` | None. No check reads it, so the `standards` review is its only judge. |

The steps, their order and what each one does are Machinery. They are the same in every repo, and no
file changes them. So this map lives here only, and setup copies no map into your repo.
