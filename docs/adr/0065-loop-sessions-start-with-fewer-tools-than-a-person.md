# Loop Sessions start with fewer tools than a person

Claude Code loads tools, connectors and features into every Session that the loop never calls, and
each one costs context on every turn of every Session a spec runs. The loop now starts each Session
with `docs/skillworks/loop-settings.json`, a Steering file that denies those tools and turns off
workflows and claude.ai connectors. A person's own Sessions keep all of them, because a person uses
`/loop`, `/schedule`, notebooks, plan mode and their connectors, and the loop does not. The settings
file people share gets one line only, `idleCompaction: false`, because idle compaction breaks a
Grill that has to stay in one unbroken context and takes nothing a person uses away.

## Considered options

**The deny list in the settings file people share.** Rejected. A bare tool name in
`permissions.deny` removes the tool from every Session the file reaches, so each teammate would lose
`/loop`, notebooks and their claude.ai connectors in work that has nothing to do with the loop, and
denying `ExitPlanMode` breaks plan mode.

**The Plugin owns the list, and a team names what to keep in `loop.json`.** Rejected. The Plugin's
version would then decide what a loop Session loads, which ADR 0023 rules out, and the keep list is
logic a plain settings file does not need.

**A person turns a tool back on in `.claude/settings.local.json`.** Not possible. `--settings` wins
over the local file, a deny wins over any allow, and `disableClaudeAiConnectors` set anywhere cannot
be undone. On Windows the local file does not reach a loop worktree at all.

## Consequences

The team owns the file. Setup writes it only when it is missing and never edits it, so a line the
team deleted stays deleted. A key the file leaves out takes Claude Code's own default, and preflight
says nothing about the file.

`--settings` takes one file. Under Sidecar Steering the driver already passes the Sidecar's
`.claude/settings.json`, so it merges the two into one before the Session starts.
