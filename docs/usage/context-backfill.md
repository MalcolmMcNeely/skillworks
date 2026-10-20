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

The check also creates `.context-backfill/`, and adds it to `.gitignore` when the line is missing.

## What comes next

The command shows the fit and stops. Later versions read the history, write the Answer sheet, and
land what you accept. This page grows as they arrive.
