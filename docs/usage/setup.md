# Setup

Setup gets your repo ready for the loop. It checks your machine and your GitHub repo, copies a Seed of
each Steering file into your repo, points `CLAUDE.md` at them, and writes the settings the loop needs
to run with nobody watching. Run it once per repo. Run it again whenever you like: it brings in a
newer Seed and keeps your team's edits.

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
2. **Seed the Steering.** `seed-steering` copies each Seed to its place, keeps a base copy of it in
   `docs/agents/.seeds/`, and adds the loop's working folders to `.gitignore`.
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
| Which side of this overlap do you keep, yours or the Seed's? | On a second run, when your edit and the newer Seed's change touch the same lines. Setup shows both sides, and asks once for each overlap. |
| Which lines of the newer Seed do you want? | When a Steering file differs from its Seed and has no base copy, because your repo was set up before base copies existed. Setup shows the difference and changes the file only by the lines you pick. |
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
| `docs/agents/.seeds/` | A base copy of each Seed, exactly as setup last copied it, and a README. Setup keeps these, and a second run reads them. Do not edit them. |
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

A second run repairs, and brings in a newer Seed after a Plugin update. A Plugin update alone never
changes your Steering.

### Each Steering file

Setup compares three versions of each Steering file: the base copy in `docs/agents/.seeds/`, your
file, and the Plugin's current Seed. The base copy is the Seed as setup last copied it, so setup can
tell your edits from the Plugin's. It says what it did to each file in one line:

| Outcome | When | What setup does |
|---|---|---|
| `wrote` | The Seed is new to your repo. | Writes the file and its base copy. |
| `updated` | You never edited the file, and the Seed moved on. | Replaces the file and its base copy with the new Seed. |
| `kept ..., which you edited` | You edited the file, and the Seed did not move. | Nothing. |
| `kept ..., the same as the seed` | Nothing changed on either side. | Nothing. |
| `merged` | You edited the file, and the Seed moved on in other lines. | Applies the Seed's change, keeps your edit, and shows the change. |
| `asks` | Your edit and the Seed's change touch the same lines. | Shows both sides and asks which to keep. |
| `left out` | You deleted the file. | Nothing. It stays deleted. |
| `kept ..., which differs from the seed` | The file has no base copy, because your repo was set up before base copies existed. | Shows the difference, and asks which lines to take. |
| `kept ..., as you settled it` | You decided on a file with no base copy. | Keeps the file as you left it, and writes its base copy. |

Setup changes no file until you have answered every question. Then it writes the files you decided
on and their base copies.

A file with no base copy gets one after you decide on it, even if you take no lines. From then on,
setup can merge it like any other file.

Setup commits nothing. Review each changed file before you commit.

### The other outputs

- **The label.** A label that is there is left alone.
- **`.gitignore`.** Setup adds only the working folders it does not name yet. It never adds one twice.
- **`CLAUDE.md`.** Setup updates the `## Agent skills` block in place. It never adds a second copy,
  and it leaves every other section alone.
- **`.claude/settings.json`.** Setup adds the allowlist entries that are missing and removes none. It
  leaves every other key as you have it.
