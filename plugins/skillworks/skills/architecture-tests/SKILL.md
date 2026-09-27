---
name: architecture-tests
description: Turn the rules in docs/agents/rules/ into architecture tests the team owns, with a common tool for the language where one fits and a starter test in the team's own language where none does, then wire each test into the Suite and the placement checks. Use when the user wants the rules enforced, after setup, or again when the repo gains a language or a rule.
---

# Architecture tests

The rules in `docs/agents/rules/` are data a test enforces. Until a test reads them, they are prose an agent may or may not follow. This skill writes those tests into the team's repo. The team owns them from then on, like any other test.

The Plugin ships no checker. Every test this skill writes is either a common tool for the language, set up to read the rule, or a starter test in the team's own language that reads the rule's YAML and checks the files.

[REFERENCE.md](REFERENCE.md) maps each rule to the common tools for each language, and names the rules that need a starter test. Read it before you propose anything.

If `docs/agents/rules/`, `docs/agents/suite.json` or `docs/agents/placement-checks.md` is missing, stop, and tell the user to run `/skillworks:skillworks-setup` first, because this skill wires its tests into the files setup writes.

## 1. Read the rules and find the languages

Read each rule in `docs/agents/rules/`, and the YAML block at its end. The settings are what a test checks: a starter test reads them from the rule at every run, and never copies them, so a changed setting changes what the test checks.

Read `CONTEXT-MAP.md` where the repo has one, because a rule reaches only the code the map gives it.

Find the repo's languages from its project files and its source files: a `.csproj` or `.sln`, a `package.json` with a `tsconfig.json`, a `go.mod`. Name the test runner each one already uses. A starter test runs in that runner, so the team needs no extra runtime.

Python and Java tools are not in the reference yet. For a repo in either, offer a starter test, and say that no common tool was weighed.

## 2. Ask which rules to enforce

Show the user a table: each rule, the settings it reads, and for each language the tool or starter test the reference names. Mark each rule that already has a test, from the tables in `docs/agents/placement-checks.md` and the checks in `docs/agents/suite.json`.

Ask which rules the team wants enforced. Offer every rule that has no test yet, and recommend the ones whose settings are filled in. A rule whose settings are empty, such as `slices: []`, judges nothing, so its test proves nothing until the team fills them.

## 3. Choose a tool or a starter test

For each rule the team picked, and each language it reaches:

- **A common tool**, where the reference names one for the language. Prefer a tool the repo already has: a second boundary tool beside the one in use is two answers to one question. The tool's config says what the rule says, and names the settings it copies, so a reader can see where they came from.
- **A starter test**, where the reference names none, or the team would rather own the code. It is written in the team's language, in the test runner the repo uses, and it reads the rule's YAML block itself. It checks the files the rule reaches, and skips what the rule skips: `skip-folders`, and any folder with its own `.git`.

Where the reference says a rule is left to the team, say why, and write nothing for it.

Say which one you chose for each rule, and why, before you write it.

## 4. Write each test red first, then prove it green

Follow `/skillworks:tdd`, one rule at a time.

1. **Red.** Make the test fail on a breach you build for it: a fixture folder, a file the test writes and then removes, or a setting the test is handed. A test you never saw fail may test nothing.
2. **Green.** Run it on the team's code, and read the result.

A rule the code breaks today is reported to the team, and never quietly weakened. Do not loosen the test, add the breach to a skip list, or change a setting to get green. Name each breach, and ask the team to choose: fix the code, or change the setting in the rule. A test that is not green on the team's code does not join the Suite, because the loop would stop on it before every Landing.

## 5. Wire it in

Each write below is one the team approves, so show it before you make it.

1. **The Suite.** Add the test's command to `docs/agents/suite.json`, with its `folder`, and with the `ignores` that keep it asleep: the paths, as git pathspecs from the repo root, that cannot change what it checks. Leave the rule files out of `ignores`, because a changed setting has to run the check again. Run `skillworks-suite` and read that the new check passes.
2. **The placement checks.** Fill both tables in `docs/agents/placement-checks.md`. The first says which check proves which rule, so a review can cite a breach by the check's name. The second holds the exact command that runs the check, its folder, and any command to run first. List the narrowest command that proves the rule, and leave out a slow one that proves something else.
3. **The allowlist.** Add the command of any tool new to the repo to `permissions.allow` in `.claude/settings.json`, in the form `Bash(<command>:*)`, so the loop is not stopped by a Denial.

## 6. Run it again

The team runs this skill again when the repo gains a language or a rule. A rerun tests only what is new:

- Find the rules and languages that no row of `docs/agents/placement-checks.md` covers yet.
- Keep every existing test as it is. The team owns it, so an edit to it is the team's, and a rerun is not a reason to rewrite it.
- Offer the new rules and the new languages, and go through steps 3 to 5 for each one the team picks.

## Report

End with a table: each rule the team picked, the test that proves it, the command the Suite runs, and whether it is green. Under it, name each breach the code has today, and each rule left to the team, with the reason.
