# The Context backfill

The skills steer by a glossary, a context map and ADRs. A repo built before it had any of them
holds the words and the decisions already, in its code and its history, and nobody wrote them
down. The Context backfill reads them out once, after setup, and nothing it finds reaches the repo
until a person has accepted it.

```
/skillworks:context-backfill
```

The command takes no argument. Its only state is the scratch folder `.context-backfill/` at the
repo root, which git ignores. A person is at the keyboard for every run, so the skill never runs in
the loop.

## The check

The first thing the command does is check the clone. It reads the Tracker and the Target branch
from `docs/agents/loop.json`, fetches the Target branch from origin, and reads its history.

### A clone it refuses

A clone that holds only part of the history is refused, because a backfill read from half a
history would say the half was the whole. The refusal names the command that mends the clone:

| The clone | Made with | The mend |
|---|---|---|
| Shallow | `git clone --depth 1` | `git fetch --unshallow`, in the clone |
| Partial | `git clone --filter=blob:none` | `git clone <url>`, a full clone made elsewhere |

A partial clone fetches each old file only when it is read, so reading its history would take
hours. A full clone reads the same history in seconds.

### The fit

On a full clone the check prints the fit: how much history there is, and how much of it carries a
reason.

```
The fit of origin/main:
  Commits: 4
  First: 2019-03-01
  Last: 2021-11-30
  Authors: 3
  With a body: 25% (1 of 4)
  Naming a ticket: 50% (2 of 4)
  Tickets: 41, and 12 pull requests
  Code roots: app, web
  Languages: TypeScript (2 files), Python (1 file)

Scratch folder: .context-backfill/, added to .gitignore
```

| Line | What it counts |
|---|---|
| Commits | The commits on the Target branch. |
| First, Last | The dates of the oldest and the newest of them. |
| Authors | The people who wrote them, one for each email address. |
| With a body | The commits whose message says more than its subject. A trailer alone, such as `Ticket: #14`, is no body. |
| Naming a ticket | The commits whose message has a `Ticket:` trailer, or names an issue as `#<n>` with the GitHub Tracker. |
| Tickets | With the GitHub Tracker, the issues and pull requests `gh` can read. With the files Tracker, the tickets under `.specs/`, and the specs that hold them. |
| Code roots | The folders that hold a project file, such as a `.csproj`, a `package.json` or a `pyproject.toml`. |
| Languages | The languages of the files on the Target branch, most files first. |

A body and a ticket are where a reason was written at the time, and the backfill never writes a
reason the history does not give. A low share of either means fewer of its finds will come with
their reason.

When `gh` cannot read the tickets, such as when it is not signed in, the Tickets line says so and
the fit is printed from git alone.

The check also creates `.context-backfill/`, adds it to `.gitignore` when the line is missing, and
writes the fit into `.context-backfill/fit.md`.

## What the first run reads

Once the check passes, the command reads the history once into `.context-backfill/`. Every later
pass of the first run reads these files, and none of them calls the Tracker, so the Tracker is read
once per run.

| File | What it holds |
|---|---|
| `log.txt` | The full log of the Target branch: each commit's message with its body, and the files it changed. |
| `renames.md` | Each rename the log shows, with its commit and subject. |
| `tickets.md` | With the GitHub Tracker: each ticket and pull request a commit message names, with its thread. |
| `pull-requests.md` | With the GitHub Tracker: each pull request merged into the Target branch, with its merge commit, its thread and its reviews. |
| `specs.md` | With the files Tracker: each file under `.specs/`, at every commit that touched it. |

With the GitHub Tracker the command reads through `gh`. With the files Tracker it reads the specs
through git and calls no service, so it works where the only remote is a bare repo.

### A missing `gh` login

When `gh auth status` fails, the command adds a warning to the fit in `fit.md` and goes on with git
alone. The log and the renames are still written. A missing login costs the ticket and pull
request threads, which are where most reasons were written at the time, and not the run. Sign in
with `gh auth login` and run the command again to read them.

## The passes

Once the history is read, the first run works through five passes, in order. Each runs in a
subagent of its own and writes one file in `.context-backfill/`:

| Pass | Writes | What it finds |
|---|---|---|
| Shape | `shape.md` | Whether the repo is one context or several, and why. |
| Words | `words.md` | The words the code and the prose both use, with one meaning each. |
| Decisions | `decisions.md` | The changes that pass the three tests of an ADR. |
| Lifetime | `lifetime.md` | The decisions that were later undone. |
| Sheet | `answer-sheet.md` | The Answer sheet, from the four files before it. |

A run that stops part of the way, such as when you close the Session, picks up where it stopped.
Each pass whose file is already there is skipped, so no pass is paid for twice.

Nothing in the repo changes during the first run. Every file it writes is in the scratch folder.

### The map question

After the shape pass, the run stops once and asks you in talk: one glossary, or a map with these
contexts. It names the contexts it found, the folders each one claims, and the words that mean two
things in two parts of the code. A word with two meanings is what calls for a map. Size alone does
not, and neither does the number of folders.

Answer with one glossary, or with the map as it is, or rename, merge or split the contexts it
named. Your answer goes into `shape.md`, and every later pass sorts its finds by it. This is the
only question of the first run.

## The Answer sheet

The first run ends with one file to mark: `.context-backfill/answer-sheet.md`. Every word, map
and decision the run found is on it as a Draft, with the evidence that holds it quoted. The run
also lists the changes it saw and chose not to offer, one line each, with the test each one fails.

The sheet has four sections:

| Section | What it holds |
|---|---|
| Words | The map first, when you chose one, then a Draft for each word. |
| Decisions | A Draft for each decision, and for each reversal. |
| Questions | Each change the history shows but never explains. |
| Thin | Each Draft with one signal and no reason written at the time. |

In each section the strongest evidence comes first. You can stop reading where the evidence gets
weak, and you lose nothing you would have accepted.

Each Draft looks like this:

```markdown
### Draft W3: Verdict
Answer:
Context: loop
**Verdict**:
A judge's call written for the driver, and never for a person.
_Avoid_: Mark, grade, status
Evidence:
- commit 3f2a9c1 "Rename Grade to Verdict: a grade is a number, a verdict is a call"
- issue #41 "the driver reads the verdict line"
```

The heading names the kind and the number: `M` for the map, `W` for a word and `D` for a
decision. The `Context:` line is there only with a map. The text between it and `Evidence:` is the
text that will be written into the repo.

A reversal, a decision that was later undone, is one Draft that holds two ADRs: the old one, marked
superseded, and the new one that names it. One Answer covers both. Each ADR sits under a `####`
heading, which is the title it is written with:

```markdown
### Draft D4: SQLite gave way to Postgres
Answer:
#### Keep the dates in SQLite
Status: superseded by the decision below
The dates live in SQLite, because one file is all a laptop needs.

#### Keep the dates in Postgres
This supersedes the decision above. The dates moved to Postgres, because two readers wrote at once.
Evidence:
- commit 4b5c6d7 "Add SQLite"
- issue #31 "two readers lock the file"
```

The ADRs have no numbers yet, so the status line and the first sentence say "the decision below"
and "the decision above". The second run puts the numbers in.

### Marking the sheet

Write one of three words on each `Answer:` line:

| Answer | What it does |
|---|---|
| `accept` | The Draft is written into the repo. |
| `reject` | The Draft is dropped. |
| `?` | The Draft stays, and the next run talks it through with you. |

A blank `Answer:` line is unanswered, and stays on the sheet. The map's `Answer:` line is already
`accept` from the map question. Change it if you changed your mind.

When a Draft is nearly right, edit its text in place and write `accept`. The text on the sheet is
the text that is written, and not the text the run wrote.

### Questions

A Question is a change the history shows and never explains: the commits say what moved, and no
commit body, ticket or thread says why. The backfill never writes a reason the history does not
give, so it asks you instead.

A Question has a `Reason:` line where a Draft has its `Answer:` line. When you know why the change
was made, write the reason on that line, in a sentence or two. The next run turns it into a
decision Draft, so your reason goes through the same three tests as every other find before it
is written. When you do not know, write `?`, or leave the line blank.

### Handing the sheet over

The sheet is a file, so you can send it to the teammate who was there when a choice was made. They
mark the lines they remember and write the reasons they know, with no Session and no Skillworks.
Put the file back at `.context-backfill/answer-sheet.md` before the next run.

### An unmarked sheet

When you type the command and the sheet is there with no Answer and no reason on it, the command
tells you to mark the sheet, and does nothing else. The map's `accept`, which the first run wrote
from the map question, does not count as an Answer here. A run typed by habit never applies a
blank sheet.

## The second run

Type the command again once the sheet is marked. The run that finds at least one Answer on the
sheet is the second run. Run it on the Target branch, or on the default branch in `spec` mode. It
writes the text that is on the sheet, so a Draft you edited is written as you edited it.

### What it writes

| Answer | Where it is written |
|---|---|
| `accept` on the map | `CONTEXT-MAP.md` at the repo root, as the sheet holds it. Two Steering files change with it, as the next section says. |
| `accept` on a word | The glossary, in alphabetical order, with its `_Avoid_` line and no evidence. With one glossary, that is `CONTEXT.md` at the repo root. With a map, it is the `CONTEXT.md` of the context the `Context:` line names, where the map says that context lives. The file is created when there is none. |
| `accept` on a decision | A new ADR in `docs/adr/`, numbered one above the highest number there, with the Draft's title as its heading and its text as its body. |
| `reject` | Nowhere. The Draft is dropped. |
| `?` or blank | Nowhere yet. The Draft stays on the sheet. |

Each ADR ends with one line that names the commits and tickets it came from:

```
Recovered from history: commit 9c1d2e3, pull request #20
```

That line tells a reader the ADR was recovered from the history and not settled in a grill, and
where to check it. A word, a map or an ADR already in the repo is never changed.

### How a reversal is written

An accepted reversal is written as two ADRs with two numbers in a row, each with its own `ADR:`
commit. With `0002` the highest number in `docs/adr/`, the example above is written as:

- `0003-keep-the-dates-in-sqlite.md`, the old decision, with the status line
  `Status: superseded by ADR-0004`.
- `0004-keep-the-dates-in-postgres.md`, the new decision, whose first sentence is
  `This supersedes ADR 0003.`

Both end with the same `Recovered from history:` line. A search for the old choice finds why it
lost.

### A written reason

A reason you wrote on a Question's `Reason:` line is written nowhere in this run. It comes back on
the rewritten sheet as a decision Draft under Decisions: the Question's text with your reason as its
why, the same evidence, and a blank `Answer:` line. Mark it like any other Draft, so your reason
faces the same Answer as every other find before it is written. A Question whose `Reason:` line is
`?` or blank stays on the sheet as a Question.

### What a map changes in Steering

A map changes how the checks read the repo, so two Steering files change in the same commit as the
map:

- `docs/agents/rules/words.md` gets an empty banned-words list, written `[]`, for each context the
  map names. The words rule wants a list for every context in the map, so a map with no lists would
  turn the Suite red.
- The Domain docs line in `CLAUDE.md` says multi-context, in the words setup writes for a repo with a
  map. Every Session reads that line to find the glossaries.

Nothing else in Steering changes. No word is ever added to a banned-words list: a word joins a list
when the team decides the code must stop using it, and that is not the backfill's call.

### What it commits

| Commit | Subject |
|---|---|
| One for the map, with its Steering edits | `Glossary: the map in CONTEXT-MAP.md` |
| One for each glossary file | `Glossary: 2 words in CONTEXT.md` |
| One for each ADR | `ADR: <the ADR's title>` |

The map comes first, so no commit leaves the repo with glossaries and no map to find them by. Each
commit holds only the files it names, so other work in your tree stays out. The run prints the
commits it made, then pulls with rebase and pushes them.

### Where the commits go

`target-branch` in `docs/agents/loop.json` decides where the commits go:

| `target-branch` | Where the commits go |
|---|---|
| A branch name, such as `main` | Straight onto that branch. No pull request is opened. |
| `spec` | Onto a branch of their own, `spec/context-backfill`, cut from the default branch. The default branch is not touched. The first push opens a draft pull request from that branch to the default branch. |

A protected default branch refuses a direct push, and `spec` mode is how a team works with one. That
is why the commits never go to the default branch in `spec` mode. Every later apply, such as the one
for an Answer you give in talk, goes to the same branch and opens no second pull request. Merge the
pull request when you are ready for the words and ADRs to reach the default branch.

It then rewrites the sheet to hold only what is left: the `?` lines, the unanswered lines, and a
decision Draft for each reason you wrote under a Question.

### What it refuses

The run writes nothing when:

- The sheet has no Answer on it. It tells you to mark the sheet.
- An `Answer:` line holds a word that is not `accept`, `reject` or `?`.
- The checkout is not on the Target branch. In `spec` mode, the checkout is not on the default
  branch or on `spec/context-backfill`.
- An accepted word names a context that no map holds, on the sheet or in the repo.
- An accepted map names no context, or setup has not written the words rule or the Domain docs
  line the map has to change.

### The `?` lines

After it writes what you accepted, the run talks each `?` line through with you, one at a time. It
shows you the Draft or the Question with its evidence, and asks for an Answer. Give one of the same
three words as on the sheet: `accept`, `reject` or `?`. You can change a Draft's words before you
accept it. Each Answer you give is applied as you give it, the same way as an Answer on the sheet.

## Starting over

Delete the scratch folder:

```
rm -rf .context-backfill
```

The next run starts from the check, reads the history again, and asks the map question again.
There is no flag for it. To run one pass again, delete only that pass's file, and the files of the
passes after it.

## What comes next

When nothing is left on the sheet, the run says so, and says that deleting `.context-backfill/`
starts over. Then it names the next step:

- When `docs/agents/suite.json` names no check yet, `/skillworks:architecture-tests`, which turns
  the rules into tests your team owns.
- When it names a check, your first loop: `/skillworks:grill`, then `/skillworks:spec-loop <spec#>`.
