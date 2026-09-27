# Setup

Setup gets your repo ready for the loop. It checks your machine and your GitHub repo, copies a Seed of
each Steering file into your repo, points `CLAUDE.md` at them, and writes the settings the loop needs
to run with nobody watching. Run it once per repo. Run it again whenever you like: it never
overwrites a file your team has.

## Before you start

You need these on your machine:

- `git`.
- `gh`, logged in. Check with `gh auth status`.
- `claude` on your `PATH`. The loop starts a Session with it for each step.
- `uv` on your `PATH`. The loop's scripts are Python and run under it.
- `node`, if you want the preflight to check your settings. Without it the preflight warns and goes
  on.

Your repo needs these:

- An `origin` remote on GitHub, with Issues turned on. GitHub Issues is the Tracker.
- `main` as the default branch.
- Permission for your GitHub login to push to `main` straight away. The loop Lands every ticket by
  pushing to `main`, so a rule that asks for a pull request or a status check stops it.

## Install the Plugin

The Plugin comes from a Marketplace in a clone of Skillworks. Clone it once, anywhere on your
machine:

```
git clone https://github.com/MalcolmMcNeely/skillworks.git
```

Then open Claude Code in your repo and add the Marketplace. Its folder is `plugins` in that clone:

```
/plugin marketplace add <your clone>/plugins
/plugin install skillworks@skillworks
```

Then run setup:

```
/skillworks:skillworks-setup
```

Setup writes the Marketplace and the Plugin into `.claude/settings.json`, so a teammate who clones
your repo gets the Plugin on trust, with no install by hand. The Marketplace path is relative when
the clone of Skillworks sits inside your repo, and in full when it does not. In full, each teammate
needs their clone of Skillworks at the same path.

## What setup does

1. **Preflight.** `skillworks-preflight` checks the tools, the login, the remote, the default branch
   and that you may push to `main`. Then it creates the `ready-for-agent` label on GitHub. If a check
   fails, setup stops and writes nothing.
2. **Seed the Steering.** `seed-steering` copies each Seed to its place, and adds the loop's working
   folders to `.gitignore`.
3. **Point `CLAUDE.md` at the docs.** Setup adds an `## Agent skills` block that names your tracker
   docs and domain docs, and imports each rule.
4. **Write the settings.** Setup writes the Marketplace, the Plugin, the allowlist and
   `"autoMemoryEnabled": false` into `.claude/settings.json`.
5. **Report.** Setup says what it wrote and what it kept, and what your team fills in before the loop
   can finish a ticket.

Expect one permission prompt on a first run, at the preflight. The allowlist that clears it is written
in step 4.

## The questions setup asks

Setup asks nothing on a clean repo except the one yes it needs. It asks more only where your repo
already holds an answer of its own.

| Question | When setup asks it |
|---|---|
| Do you agree to the allowlist and to turning auto-memory off? | Always, once, before it writes `.claude/settings.json`. It reads each allowlist entry out, and the memory line with them. The allowlist lets the loop run `git push` and `gh issue close` with no prompt. That is the point, and also the risk. |
| Which lines of the newer Seed do you want? | When a Steering file is already there and differs from its Seed. Setup shows the difference and changes the file only by the lines you pick. |
| Which Marketplace, or which Plugin setting, do you keep? | When `.claude/settings.json` already names the `skillworks` Marketplace or the Plugin with another value. Setup shows both. |
| Keep auto-memory on, or turn it off? | When `.claude/settings.json` says `"autoMemoryEnabled": true`. With memory on, memory files on each machine steer the loop, so it runs differently from one machine to the next. Setup never changes it without asking. |

## The files setup writes

Review these before you commit them.

| File | What it holds |
|---|---|
| `docs/agents/rules/comments.md` | The comments rule. Its settings start empty. |
| `docs/agents/rules/determinism.md` | The determinism rule. Its settings start empty. |
| `docs/agents/rules/file-placement.md` | The file placement rule. Its settings start empty. |
| `docs/agents/rules/words.md` | The words rule. Its lists start empty. |
| `docs/agents/issue-tracker.md` | The `gh` calls the loop makes, the ticket shape, and the two conventions the loop leans on. |
| `docs/agents/domain.md` | Where your glossary and your ADRs live. |
| `docs/agents/placement-checks.md` | The commands that prove placement. It starts with none. |
| `docs/agents/smell-baseline.md` | The code smells the `standards` review looks for. |
| `docs/agents/arrangement-baseline.md` | The failures of placement the `architecture` review looks for. |
| `docs/agents/suite.json` | Your Suite. It starts with no checks, and the loop stops until you add one. |
| `docs/agents/loop.json` | The loop's settings. `target-branch` starts as your remote's default branch. |
| `.gitignore` | The loop's working folders: `.spec-loop/`, `.handoff/` and `.claude/worktrees/`. Each machine has its own, and nobody shares them. |
| `CLAUDE.md` | The `## Agent skills` block. If your repo has `AGENTS.md` and no `CLAUDE.md`, setup edits `AGENTS.md` instead. |
| `.claude/settings.json` | The Marketplace, the Plugin, the allowlist and `"autoMemoryEnabled": false`. |

Setup writes nothing under `~/.claude`, and it leaves `.claude/settings.local.json` alone.

[Steering](steering.md) says what each of these files does and what your team can change in it.

## What your team fills in

The Seeds judge nothing until your team fills them in. Before the loop can finish a ticket:

- **`docs/agents/suite.json`**: add the checks that prove your code. [The Suite](suite.md) has the whole
  file.
- **The allowlist** in `.claude/settings.json`: add each tool your Suite runs, such as a build or a
  test runner. A Session with nobody watching cannot ask you, so a missing entry is a Denial.
- **The rules' settings**, as your team settles them.

Then the loop is ready:

```
/skillworks:grill-with-docs  →  /skillworks:spec-loop <spec#>
```

## Run setup again

A second run repairs, and never overwrites. Here is what it does to each output:

- **The label.** A label that is there is left alone.
- **A Steering file that is there** is kept. If it matches its Seed, setup says so. If it differs,
  setup shows the difference between your file and the Seed, and changes nothing unless you pick
  lines to take. A Plugin update can bring a newer Seed, so a second run is how you see what changed.
- **A Steering file that is missing** is written from its Seed.
- **`.gitignore`.** Setup adds only the working folders it does not name yet. It never adds one twice.
- **`CLAUDE.md`.** Setup updates the `## Agent skills` block in place. It never adds a second copy,
  and it leaves every other section alone.
- **`.claude/settings.json`.** Setup adds the allowlist entries that are missing and removes none. It
  leaves every other key as you have it.
