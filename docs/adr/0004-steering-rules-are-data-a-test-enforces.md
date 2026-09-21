# Steering rules are data that a test enforces

Claude puts too many files in one folder, too many types in one file, and too many comments in
both. Written rules alone do not stop it: a comment rule held on 10 runs of 15, and 859 of the
repo's comment lines were XML doc comments that no build reads. So the rules for where code goes and
how it is commented live in two files, `.claude/rules/file-placement.md` and
`.claude/rules/comments.md`, and `tests/Skillworks.Architecture.Tests` reads the YAML block in each
and fails when the code breaks it. Changing a rule means editing one of those files and nothing else.

A folder shape and the presence of a doc comment are facts, so a test can decide them. Whether a
`//` comment is worth keeping is not a fact, so that rule stays as text, and `/comment-sweep` cleans
up what the text misses. The research behind this is in
[steering how Claude writes code](../research/claude/steering-code-style.md) and
[where a comment rule sits, measured](../research/measurements/comment-density-measured.md).

## Considered options

**A `PreToolUse` hook.** It blocks a bad write before it lands. It was rejected because it fires on
every write, blocks the half-moved state of any restructure, and never sees a `git mv` run from Bash.
A test runs where `/implement` already has to pass the full suite before it can close a ticket.

**Text only.** It was rejected because the flat folders already in this repo are what text alone
produced.

**An output style with `keep-coding-instructions: false`.** It scored 15 of 15 on comment density,
but it also drops Claude Code's instructions on scope and verification, and nobody has priced that.
The doc comment check covers what it fixed.

## Consequences

The spec loop runs the sweep and the review as its own steps, in one session through
`claude -p --resume`: `/implement N --stop-after-tests`, then `/comment-sweep`, then `/code-review`
with the commit and the close. A step written into a skill can be skipped, and a step in the script
cannot. Run by hand with no flag, `/implement` still does every step itself.

_The first of those three sentences is superseded by
[ADR 0024](0024-a-review-axis-edits-and-the-sweep-follows-the-last-writer.md). The loop now runs
seven steps, the review is three of them, and each runs in a session of its own. The other two
sentences stand._

The existing code breaks the rules, so it is restructured before or with the test, never after:
feature folders then concern folders, one type per file, namespaces that match folders, and test
folders that mirror source folders. The front end moves from layer first to feature first, so the
paths in `.dependency-cruiser.cjs` change once.

The loop keeps the plain-words output style, renamed `skillworks`. `skillworks-setup` writes it to
`.claude/output-styles/` and sets it in `.claude/settings.json` when no style is set.
