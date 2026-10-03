# Steering

Steering is what your repo tells the loop about itself: its rules, its tracker docs, its review files
and its Suite. Setup copies a Seed of each file into your repo, and your team owns the files
from then on. A Plugin update never changes them by itself. A second run of setup brings in a newer
Seed and keeps your edits: [Setup](setup.md#run-setup-again) says how. Edit them by hand whenever your
team changes its mind, and commit the edit like any other change.

This page is the one living list of what a team steers and what is fixed. An ADR records a decision
as it was made. When a list changes, this page changes, and the ADR stays as it was.

Every Steering file lives in `docs/agents/`, so you find all of it in one place. A few files sit
somewhere else, because a tool or a design puts them there. They are at the end of the list.

Each file below says what it does, which part of the loop reads it, and what your team can change in
it. [The loop](the-loop.md) has the steps these parts name, and [the stage map](the-loop/stage-map.md)
says which stage loads each file.

## Every Steering file always exists

Each step of the loop leans on its Steering file, so every file setup seeds always exists. To want
less of a file, empty it down rather than delete it. Setup writes a missing file again, even one your
team deleted. The loop stops before any ticket runs when a file is missing, and its `ABORT` line names
the file and says to run setup.

## What always loads

Some Steering has to be in every Session from the start. The rules are that kind. `CLAUDE.md` loads
each one with an `@` import:

```markdown
@docs/agents/rules/comments.md
@docs/agents/rules/determinism.md
@docs/agents/rules/file-placement.md
@docs/agents/rules/testing.md
@docs/agents/rules/words.md
```

So `comments.md`, `determinism.md`, `file-placement.md`, `testing.md` and `words.md` load into every
Session, and into every step of the loop. Keep them short, because every Session pays for each line.

The preflight checks that each rule in `docs/agents/rules/` still has its import. Without that check,
one deleted line would turn a rule off without a word. A new rule you add to the folder needs a new
import line in `CLAUDE.md`, or the preflight stops. The loop runs the same check, so it stops too,
before any ticket runs.

## What loads on demand

Every other file in `docs/agents/` loads only when a skill reads it. A Session that does not need a
baseline does not carry it. So a long baseline costs only the step that reads it.

## The rules, in `docs/agents/rules/`

Each rule is prose with one YAML block at the end. The prose says what the rule asks for. The YAML
block holds its settings.

The settings that name what a rule judges start empty, so nothing is judged until your team fills
them in: `contexts`, `slices`, `concerns`, `test-roots`, `banned-words` and the words rule's
`skip-folders`. The others ship with a default your team can change: `doc-comments`, `clock`,
`max-types-per-folder`, `source-files`, `test-files`, the placement rule's `skip-folders`,
`banned-folder-names` and `name-map`.

| File | What it does | What reads it | What your team can change |
|---|---|---|---|
| `comments.md` | Says which comments earn their place, and where doc comments may go. Its keep and cut table is your team's taste in comments. | Every Session. The `sweep` step judges each comment by its table. The `standards` review reads it too. | The table, the prose, and `doc-comments`: `true` lets code files carry doc comments, `false` lets no file carry them. |
| `determinism.md` | Says how code reads time, and how a test keeps the order of events: before it acts while the code runs, it waits on a fact that shows the code is ready. So a test that fails means the code is wrong. | Every Session. The `standards` review judges the change by it. No check reads the Order of events section, so only the `standards` review judges it. | The prose, `clock` (the type your code reads time through), and `contexts` (which parts of the code the rule judges). |
| `file-placement.md` | Says where each file goes: folder shape, file names, where tests sit, and how many types a folder holds. | Every Session. The `architecture` review judges the change by it. | Every setting: the Slices, the folder size, the name map, the test file patterns, the folders to skip and the banned folder names. |
| `testing.md` | Holds your team's taste in tests: what to mock and what not to, the fake library your tests use, when a stand-in written by hand is right, one logical assertion per test, test names that say what and not how, and how high and how few the seams are. It has no settings. | Every Session, and `tdd` when it writes a test. The `standards` review is its only judge, because no check reads it. | All of its prose. |
| `words.md` | Lists the words that lost against a glossary word, one list per context. No source file uses a word that lost. | Every Session. The `standards` review judges the change by it. | The lists. A word joins a list when your glossary settles it and the code reaches for the loser again. |

A check can read a rule's YAML block and fail the Suite on a breach. The Plugin ships no such check.
It is yours to add, as a check in your Suite.

## The files in `docs/agents/`

| File | What it does | What reads it | What your team can change |
|---|---|---|---|
| `issue-tracker.md` | Says how the skills read and write each Tracker. The skills write both Trackers through `tracker-publish`, and the `gh` calls stay for reading `github`. With `files` it names the `.specs/` files and their frontmatter. It holds the ticket shape, and the two conventions the loop leans on: a commit names its ticket, and a ticket is closed with a note of what was done, as a comment on GitHub or as a `## Closing note` in the ticket's file. | `/skillworks:to-spec` and `/skillworks:to-tickets`, the `spec` review, `finish`, and the drift check. | "The ticket shape": the size of a ticket, its title and its sections. That is your team's taste in tickets. Leave the two conventions as they are, because the loop reads them back. |
| `domain.md` | Says where your glossary and your ADRs live, and how a skill reads them. | A skill that explores your code, sent there by the pointer in `CLAUDE.md`. The `architecture` review reads it first, and the `standards` review reads it to find your glossary. | Where your domain docs live, for example one `CONTEXT.md` or a `CONTEXT-MAP.md` with one glossary per context. |
| `review-standards.md` | What the `standards` review checks. It holds the smell baseline, the code smells the Plugin ships, which the review looks for even when your repo documents nothing. It holds your team's own checks, each a hard breach or a judgement call. It holds a "Do not report" list. | The `standards` review, and no other step. | The smells: add one your team cares about, or cut one it does not. A rule your repo writes down always beats a smell. Your checks: each says what to look for, whether it is a hard breach or a judgement call, and the paths it covers when it covers fewer than all. "Do not report": the paths and the kinds of finding the review skips. |
| `review-architecture.md` | What the `architecture` review checks. It holds the arrangement baseline, the failures of placement and direction and their weighting, which the review looks for even when your repo documents nothing. It holds your team's own checks, each a hard breach or a judgement call. It holds a "Do not report" list. | The `architecture` review, and no other step. | The failures and their weighting. A rule your repo writes down always beats a failure. Your checks: each says what to look for, whether it is a hard breach or a judgement call, and the paths it covers when it covers fewer than all. The review skips a small change inside one module, but never one that a check of yours covers, so a check with no paths makes it review every change. "Do not report": the paths and the kinds of finding the review skips. |
| `review-spec.md` | What the `spec` review checks, beyond whether the change is the one the ticket asked for. It holds no baseline, because that check lives in the review itself. It holds your team's own checks, each a hard breach or a judgement call. It holds a "Do not report" list. | The `spec` review, and no other step. | Your checks: each says what to look for, whether it is a hard breach or a judgement call, and the paths it covers when it covers fewer than all. "Do not report": the paths and the kinds of finding the review skips. The Seed holds no check, so the review checks only the ticket until you add one. |
| `placement-checks.md` | Names the commands that prove placement, each with its folder and anything to run first. It also maps each check back to the rule it runs. | The `architecture` review. It runs these commands and nothing else. | The commands. The Seed names none, so the review can only judge placement by reading until you add them. |
| `suite.json` | The Suite: the checks that decide green for your repo. | The `suite` step, the Suite again after a rebase, the full run, and `skillworks-suite`. | Every check, its `ready` command, its `ignores`, its `image`, and `runs`. [The Suite](suite.md) has the whole file. The Seed names no check, so the loop stops until you add one. A check can name a Dockerfile you keep in `docs/agents/` as its `image`. |
| `loop.json` | The loop's settings. `tracker` names where your specs and tickets live: `github` for GitHub Issues, or `files` for committed files in `.specs/`. `target-branch` names the branch the loop Lands on, or says `spec` to review each spec as one pull request. | Setup, which asks for all three and writes them. The preflight and the loop's scripts, through one reader. The skills that read or write a spec or a ticket, to find the Tracker. The grill, `/skillworks:to-spec`, `implement` and the drift check, to find the branch they push to or judge. | `tracker`: `github` or `files`. The Seed sets it to `github`, and setup asks. `target-branch`: a branch name, such as `main` or `master`, or `spec`. The Seed sets it to your remote's default branch. `co-authored-by`: `show` or `hide`. The Seed sets it to `hide`, and setup asks. [The loop](the-loop/tracker.md) says how to choose each one. |
| `surfaces.md` | Lists your Surfaces: the places a change can have to reach besides the code that does the work, such as the README or the user docs. [The Surfaces file](#the-surfaces-file) has an example. | The grill, which asks about each Surface a change touches. `/skillworks:to-spec`, which writes each answer into the spec's Surfaces section. The `spec` review and the drift check, which find each Surface the spec names and check it is in step. The Name check does not read it: it reads the diff and the glossary alone. | Every Surface. Add your own, and delete one your repo does not have. |

A hard breach is always fixed and never left. That holds for a check in a review file marked hard,
and for a breach of a rule marked hard. A judgement call may be left, with the reason in the
review's report and in the ticket's Closing note.

A check that should also shape the build goes in a rule in `docs/agents/rules/`, and not in a review
file. A rule loads into every Session, so the build reads it too. A review file is read only by its
review.

## The Surfaces file

A change often has to reach more than its code. A new setting needs a line in the user docs. A new
command needs a line in the README. The grill asks about these places, so nobody leaves one behind
without deciding it. `docs/agents/surfaces.md` names them. The grill asks once the design is settled,
one Surface at a time, and skips a Surface the change does not touch. The spec carries each answer in
its Surfaces section. Each ticket carries the Surfaces its change touches. The `spec` review and the
drift check each check that those Surfaces are in step.

Each `##` section is one Surface, with three parts:

- **Where it lives:** the file or folder that holds it.
- **The question:** the one question the grill asks about it.
- **What to capture:** what the answer has to hold, so the builder can bring the Surface into step.

The Seed holds two Surfaces, the README and the user docs. Delete one your repo does not have. Add a
section for each other place your team keeps in step. A team that keeps a sample app might add:

```markdown
## The sample app

- **Where it lives:** `samples/`
- **The question:** Does a visitor who clones the repo need to see this change used in the sample
  app?
- **What to capture:** Which sample project changes, and what it shows once the change Lands: a new
  example, or a change to one already there.
```

A file with no Surface in it costs nothing: the grill skips the step.

The README Surface is the one Surface the loop treats in a special way, because each ticket that adds
a sentence to a README makes it longer for every newcomer. The loop changes the README only as the
spec's README item says. The item's limit is the Surface's "What to capture", which your team owns.
The Seed's default is a changed line and one new setup or run step. The heading must stay
`## The README`, so that the loop can find it. A repo with no README Surface gets no README rules, and
the loop treats its README as any other file.

## The Steering outside `docs/agents/`

These files stay where a tool or a design places them.

| File | What it does | What reads it | What your team can change |
|---|---|---|---|
| `CLAUDE.md` | Loads into every Session. Setup adds an `## Agent skills` block that points at the tracker docs and the domain docs, and imports each rule. | Claude Code, at the start of every Session. | Anything outside the block. Inside the block, keep one import for each rule. |
| `.claude/settings.json` | Holds the Plugin's Marketplace, the allowlist the loop needs to run with nobody watching, the read rule `Read(~/.claude/plugins/**)` and one for a Marketplace folder outside the repo, so a skill can read its own files, `"autoMemoryEnabled": false`, and the prompt cache keys `promptCacheTtl` and `subagentPromptCacheTtl`, each `"1h"`, so each ticket reads its prompt from a warm cache. | Claude Code, for every Session in the repo. | The allowlist: add each tool your Suite runs, such as a build or a test runner. A Session with nobody watching cannot ask you, so a missing entry is a Denial. Auto-memory, off by default: set `autoMemoryEnabled` to `true` and memory files on each machine steer the loop, so it runs differently from one machine to the next. The cache keys: a value your team sets is kept. |
| `CONTEXT.md`, or `CONTEXT-MAP.md` and one `CONTEXT.md` per context | Your glossary: the words your repo uses, and the words that lost under _Avoid_. | The grill writes it as words settle. The reviews and the drift check judge names by it. The Name check reads it beside the spec's diff, to find each name whose meaning moved and each concept two tickets named two ways. | All of it. It is your domain. |
| `docs/adr/` | Your decisions, one file each, with the options you turned down. | The grill writes an ADR as a decision settles. The `architecture` review reads the ADRs that touch the change. | All of it. Write a new ADR to change a decision, rather than editing an old one. |
| A linter's own rules file, such as `.dependency-cruiser.cjs` | The rules a linter enforces, in the place the linter looks. | The linter, when a Suite check or a placement check runs it. | All of it. A review skips what a linter already enforces. |

## What is fixed

Some opinions are how Skillworks works. They are Machinery: the same in every repo, run from the
Plugin, and no team edits them. There is no file for them, so do not look for one.

- The three review axes: Standards, Spec and Architecture. Each review must cite a line or drop the
  finding.
- The test-first method in `tdd`: red before green, vertical slices, tests at seams, and the
  anti-patterns. Your taste in tests is not fixed. It is the testing rule, `testing.md`.
- The deep-module view in `codebase-design`.
- The plain writing in `unslop`, and the output style the Plugin forces on every Session.
- The rules for writing a document an agent reads, in `skillsmith`. Claude loads it when it edits a
  skill, a `CLAUDE.md` or a rule file.
- The trailers on every commit: the Session trailer always, the `Ticket` trailer in the loop, and the
  credit line for Claude as `co-authored-by` in `docs/agents/loop.json` says.
- The three trailer rules the hook writes into `.git/config`:
  `trailer.Skillworks-Session.ifExists=addIfDifferent`,
  `trailer.Co-Authored-By.ifExists=addIfDifferent` and `trailer.Ticket.ifExists=replace`. The hook
  writes the Plugin's value over one your team set.
- The skills, the scripts they drive and the hooks: the steps of the loop, their order, the Nudge, the
  Keep, the Turn, and the round a red Suite goes.

A fix to any of these reaches every repo with the next Plugin update. Your Steering stays as your team
left it.
