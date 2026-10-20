---
name: context-backfill
description: Check that this clone holds the whole history, read it once into the scratch folder, write every word, map and decision it shows as a Draft on an Answer sheet for a person to mark, and on the next run write each Draft the person accepted into the glossary and the ADRs.
disable-model-invocation: true
---

# Context Backfill

A repo that was built before it had a glossary, a map or ADRs fills them once, from its code and its history. A developer types this command, and nothing it finds reaches the repo until a person has accepted it.

It takes no argument. The scratch folder `.context-backfill/` at the repo root is its only state, so what the folder holds says which run this is.

A person is at the keyboard for every run of this skill, and it never runs in the spec loop. A paragraph a driver adds to the prompt, about a Choice, a `CHOSE` line or a `BLOCKED` line, is not this skill's own. Do not follow it. Ask the person instead.

## Which run this is

Look in `.context-backfill/` before anything else.

- **No `answer-sheet.md`.** This is the first run. Go on from Check the clone.
- **An `answer-sheet.md` with no Answer on it.** Every `Answer:` line and every `Reason:` line is blank, but for the map's `accept` the first run wrote from the talk, which is not an Answer the person marked. Tell the person one thing: mark the sheet. Do nothing else, and stop.
- **An `answer-sheet.md` with at least one Answer.** This is the second run. Go on from The second run.

## Check the clone

Run the check from the repo root:

```bash
context-backfill check
```

It reads `docs/agents/loop.json` for the Tracker and the Target branch, fetches the Target branch from origin, and creates the scratch folder. It adds `.context-backfill/` to `.gitignore` when the line is missing, so an Answer sheet never reaches a commit.

If it refuses, show the person the refusal and the command it names, and stop. A shallow clone is mended by the unshallow fetch, and a partial clone by a full clone. Do not read the history of a clone it refused: the part it holds would read as the whole.

If `docs/agents/loop.json` is missing, the check says so. Tell the person that `/skillworks:skillworks-setup` writes it, and stop.

## Show the fit

On a full clone the check prints the fit: the commits on the Target branch, the first and last dates, the authors, the share of commits with a body beyond the subject, the share that names a ticket, the tickets the Tracker can reach, and the code roots and languages. Show the person the fit as it was printed.

A low share with a body or naming a ticket means few reasons were written down at the time, so the Answer sheet will hold more Questions and fewer Drafts.

The check also writes the fit into `.context-backfill/fit.md`.

## Read the history

Once the check passes, and when `.context-backfill/log.txt` is not there yet, run the history from the repo root:

```bash
context-backfill history
```

It writes the raw material every later pass reads into the scratch folder, once:

- `log.txt`: the full log of the Target branch, with each message's body and the files each commit changed.
- `renames.md`: each rename the log shows.
- With the `github` Tracker, `tickets.md`: each ticket and pull request the commit messages name, with its thread. And `pull-requests.md`: each pull request merged into the Target branch, with its merge commit, its thread and its reviews.
- With the `files` Tracker, `specs.md`: each file under `.specs/`, at every commit that touched it. No service is called.

A later pass reads these files and never calls the Tracker itself, so the Tracker is read once per run. When `log.txt` is already there, a run before this one read the history, so skip this step.

When `gh` is not signed in, the history warns, adds the warning to `fit.md`, and goes on with git alone. Show the person the warning. A missing login costs the ticket threads and not the run: `gh auth login`, then `context-backfill history` again, reads them.

## Run the passes

Five passes run in this order. Each pass writes one file of its own in `.context-backfill/`:

| Pass | Reads | Writes |
|---|---|---|
| The shape pass | the code, `fit.md`, `log.txt` | `shape.md` |
| The words pass | the code, the history files, `shape.md` | `words.md` |
| The decisions pass | the code, the history files, `shape.md` | `decisions.md` |
| The lifetime pass | the history files, `shape.md`, `decisions.md` | `lifetime.md` |
| The sheet pass | `shape.md`, `words.md`, `decisions.md`, `lifetime.md` | `answer-sheet.md` |

The history files are the ones Read the history wrote. A rerun skips every pass whose file is already there, so a run that stopped part of the way picks up at the first pass with no file.

Run each pass in a subagent of its own, through the Agent tool, one at a time and in order. Brief it with the pass's section below, the files it reads, the file it writes, and the Rules for every pass. Size each pass to finish inside the Smart zone, the part of a context window in which a model still keeps every instruction it was given. When the history is too long for one subagent to read inside it, split the pass by date range across subagents run one after another, and have the last one join their finds into the pass's one file.

Write nothing in the repo during the passes. Every file a pass writes is in `.context-backfill/`.

### Rules for every pass

- Use the words Context backfill, Draft, Answer, Answer sheet and Question for those things, and no other words for them.
- Never write a reason the history does not give. A why is a quote or a close paraphrase of a commit body, a ticket, a pull request or a thread, and it names its source. Where no source gives a why, say that no source gives one.
- Quote each piece of evidence with its reference: a commit by its short hash and subject, a ticket or a pull request by its number, a spec by its path, and a code line by its path and line number.
- Read an existing `CONTEXT.md`, `CONTEXT-MAP.md` and `docs/adr/` as evidence. Never offer again what they already hold, and never change them.

### The shape pass

Read the code roots, the folders, the type names, the package boundaries, and the words that recur in commit subjects. Say whether the repo is one context or several, and give the reason.

Polysemy decides it: one word that means two things in two parts of the code calls for a map. Size alone does not, and neither does the number of folders. For a map, name each context, the folders it claims, and the words that mean two things, each with its two meanings and their evidence.

Write the finding into `shape.md`, under `## Finding`.

### The map question

After the shape pass and before the words pass, stop once and ask the person in talk: one glossary, or a map with these contexts. Name the contexts the shape pass found, with the folders each claims, and the polysemy that calls for them. The person may rename, merge or split the contexts.

Write the person's answer into `shape.md`, under `## Answer`, with each context, the folders it claims, and one sentence on what it is. Every later pass sorts each find by this answer.

This is the one question of the first run. When `shape.md` already holds an `## Answer`, do not ask it again.

### The words pass

Offer a word Draft for a name that appears both in the code, as a type, a module or a folder, and in prose, as a commit subject, a ticket or a thread, with one meaning the code holds. Read commit subjects and tickets as hard as types: the words of a process are often in no type at all.

Write each Draft as the glossary will hold it: the word in bold followed by a colon, then a definition of one or two sentences that says what the word is, not what it does. Add an `_Avoid_` line with the names the renames show lost to it, and leave the line out when no rename shows one. With a map, name the context that claims the word.

Never offer a word that is already in a glossary of the repo. Read an existing glossary as evidence of the team's taste in words, and write each definition in that taste.

Write the Drafts into `words.md`, each with its evidence and the number of signals that hold it.

### The decisions pass

Look for the signals of a decision: a dependency added or removed; a folder created, deleted or renamed; a store, a bus, an auth provider or a deployment target chosen; and a body or a thread that says why.

Judge each change by the three tests of an ADR. All three must be true:

1. **Hard to reverse.** Changing the choice later costs something real.
2. **Surprising without context.** A reader who looks at the code would wonder why it was done that way.
3. **The result of a real trade-off.** There were real alternatives, and one was picked for a reason.

A change that passes the three tests and has a written reason becomes an ADR Draft: a title, then one to three sentences that say what was decided and why. A change that passes the three tests and has no written reason becomes a Question, and never a Draft: say what changed and when, with its evidence, and leave the why open.

A change that fails a test never reaches the sheet. List it under `## Failed a test`, one line each: the change, its commit, and the test it fails.

Write the Drafts, the Questions and that list into `decisions.md`, each Draft and each Question with its evidence and the number of signals that hold it.

### The lifetime pass

Find the decisions that were later undone. A reversal rarely says revert. Its signals are a dependency removed after it was added, a folder deleted or renamed back, a setting put back, and a later thread that names the old choice.

A reversal becomes one Draft that holds two ADRs. The old decision has a status line that says it is superseded by the new one. The new decision's first sentence says it supersedes the old one. One Answer covers the pair. Where `decisions.md` holds a Draft for either side of the pair, the reversal Draft takes its place.

A reversal with no written reason for either side is a Question, as in the decisions pass.

Write the reversals into `lifetime.md`, each with its evidence, the number of signals that hold it, and the Draft in `decisions.md` it takes the place of.

### The sheet pass

Write the Answer sheet, `.context-backfill/answer-sheet.md`, in the shape below. A later run reads this shape, so keep to it exactly.

The sheet has four sections, in this order: `## Words`, `## Decisions`, `## Questions` and `## Thin`.

- Each Draft is a `###` heading that names its kind and number: `### Draft M1: <title>` for the map, `### Draft W<n>: <word>` for a word, and `### Draft D<n>: <title>` for a decision or a reversal. Number each kind from 1, through every section.
- Under the heading comes an `Answer:` line, left blank for the person to mark. With a map, a `Context:` line follows it and names the context that claims the Draft. Then comes the Draft's text, exactly as it will be written into the repo. Then comes an `Evidence:` list that quotes each commit, ticket or code line with its reference.
- A Question is a `### Question Q<n>: <title>` heading with a `Reason:` line in place of the `Answer:` line, left blank for the person to write the reason on, or `?`. Its text says what changed and when, and never why.
- With a map, the map is the first Draft under Words, its `Answer:` already `accept` from the talk, and the person may change it. Its text is the map as `CONTEXT-MAP.md` will hold it, with each context, where it lives, and one sentence on what it is. Without a map, there is no map Draft.
- A reversal's text holds both ADRs: under a `####` heading for each, the old decision first, with its status line, and the new decision second. Each `####` heading is the title its ADR is written with. Neither ADR has a number yet, so write the old one's status line as `Status: superseded by the decision below`, and begin the new one with `This supersedes the decision above.` The second run puts the numbers in.
- In each section, put the strongest evidence first: more signals, and a reason written at the time, before fewer.
- A Draft with one signal and no written reason goes under Thin, and not under Words or Decisions.

One word Draft, to fix the shape:

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

## End the first run

When the sheet is written, tell the person:

- Where the sheet is: `.context-backfill/answer-sheet.md`.
- How many Drafts and Questions it holds, in each section.
- How to mark it: `accept`, `reject` or `?` on each `Answer:` line, and a reason, or `?`, on each `Reason:` line. A Draft's text may be edited in place, and the text on the sheet is the text that is written.
- That the sheet is a file, so they can hand it to the teammate who was there.
- That they type this command again once the sheet is marked.
- That deleting `.context-backfill/` starts over.

Then list each change that failed a test, from `## Failed a test` in `decisions.md`, one line each, so the person knows what the skill saw and chose not to offer.

Then stop. Change nothing in the repo.

## The second run

### Apply the sheet

Run the apply from the repo root, on the Target branch. When `target-branch` is `spec`, run it on the default branch, or on `spec/context-backfill` once an earlier apply made it:

```bash
context-backfill apply
```

It reads `.context-backfill/answer-sheet.md`, and writes the text that is on the sheet, never the text a pass wrote, so a Draft the person edited is written as edited:

- An accepted map goes into `CONTEXT-MAP.md` at the repo root. In the same commit it adds an empty banned-words list, written `[]`, to `docs/agents/rules/words.md` for each context the map names, and switches the Domain docs line in `CLAUDE.md` to multi-context. It edits nothing else in Steering, and never adds a word to a banned-words list.
- Each accepted word goes into the glossary, in alphabetical order, with its `_Avoid_` line and never with its evidence. Without a map, that is `CONTEXT.md` at the repo root. With a map, it is the `CONTEXT.md` of the context the `Context:` line names, at the path the map gives it. It creates the file when there is none.
- Each accepted decision goes into `docs/adr/`, numbered one above the highest number there, with the title as its heading and the Draft's text as its body. It ends with one line, `Recovered from history:`, and the commits and tickets it came from.
- An accepted reversal goes in as two ADRs with two numbers in a row, each titled by its `####` heading, and each ending with the same `Recovered from history:` line. The old decision comes first, with the status line `Status: superseded by ADR-<new number>`. The new decision comes second, and its first sentence is `This supersedes ADR <old number>.`
- A Question whose `Reason:` line holds a reason comes back on the rewritten sheet as a decision Draft under Decisions, with the Question's text, the reason as its why, the same evidence and a blank `Answer:` line. No ADR is written from it in this run. A Question whose `Reason:` line is `?` or blank stays a Question.
- Each rejected Draft is dropped, and is written nowhere.
- A word, a map or an ADR already in the repo is never changed.

It makes one `Glossary:` commit for the map and its Steering edits, naming the map, then one `Glossary:` commit for each glossary file, naming the file and the number of words, then one `ADR:` commit for each ADR, with its title, so a reversal makes two. It stages by path, so other work in the tree stays out of every commit. It prints the commits it made, then pulls with rebase and pushes to the Target branch. When `target-branch` is `spec`, a protected default branch would refuse the push, so it commits on `spec/context-backfill`, cut from the default branch, pushes that branch, and on the first push opens a draft pull request to the default branch. A later apply goes to the same branch and opens no second pull request.

It then rewrites the sheet to hold only what is left: the `?` lines, the unanswered lines, and a decision Draft for each written reason. It prints what is left.

If it refuses, show the person the refusal and stop. It refuses a sheet with no Answer on it, with one message: mark the sheet. It refuses before it writes anything when an Answer is not one of the three words, when the checkout is not on the Target branch or, in `spec` mode, on the default branch or `spec/context-backfill`, when an accepted word names a context no map holds, and when an accepted map names no context or the repo lacks the words rule or the Domain docs line the map has to change. A refusal after the commits says the commits are made and names the command that sends them.

### Talk the `?` lines through

Take each `?` line on the rewritten sheet, one at a time. Show the person the Draft or the Question with its evidence, and ask for an Answer. An Answer in talk is one of the same three words as on the sheet: `accept`, `reject` or `?`. The person may change the Draft's words before they accept it, and the words they give are the words that are written.

For a Question, the person gives the reason, or `?`. Never write a reason the person did not give. A reason given in talk comes back from the apply as a decision Draft with a blank `Answer:` line, so take that Draft through next.

Apply each Answer as it is given: write it on the Draft's `Answer:` line, or on the Question's `Reason:` line, in the sheet, with the words the person gave, and run `context-backfill apply` again. Then go on to the next `?` line. A `?` given in talk leaves the line on the sheet for a later run.

### End the second run

When nothing is left on the sheet, say so, and say that deleting `.context-backfill/` starts over. When lines are left that the person did not answer, name them, and say that they type this command again once they are marked.

Then name the next step. Read `docs/agents/suite.json`:

- When it names no check, the next step is `/skillworks:architecture-tests`, which turns the rules into tests the team owns.
- When it names a check, the next step is the first loop: `/skillworks:grill`, then `/skillworks:spec-loop <spec#>`.
