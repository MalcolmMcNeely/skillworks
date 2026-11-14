# Setup turns off what Skillworks never uses

Claude Code loads tools, connectors and features into every Session that Skillworks never calls,
and each one costs context on every turn. Skillworks is for developers who want to work with AI and
do not yet know which of these they need, so setup turns them off in the settings file it already
writes, for people and the loop alike: a deny entry for each unused tool, plan mode included, since
the Grill does that job, and `disableWorkflows`, `disableClaudeAiConnectors` and
`autoCompactEnabled: false`. A Session that fills its context stops, rather than compacting into the
Dumb zone, and a loop Session that stops fails its step loudly. A developer who wants a feature back
edits the settings.

## Considered options

**Turn off only what no person uses by hand, and give the rest to the loop alone.** Rejected. It
leaves a beginner paying for `/loop`, `/schedule`, notebooks and connectors they never asked for,
and needs a second settings file and a merge in the driver to carry the loop's share.

**A settings file of the loop's own, owned by the Plugin with a keep list in `loop.json`.**
Rejected. The Plugin's version would decide what a Session loads, which ADR 0023 rules out.

## Consequences

Never denied: the tools Skillworks calls, `Skill`, `Agent`, `Bash`, `PowerShell`, `Read`, `Edit`,
`Write`, `ToolSearch` and `SendMessage`, and the hooks.

A deny entry and `disableClaudeAiConnectors` cannot be undone in `.claude/settings.local.json`,
because a deny wins over any allow and the connector switch stays on once any source sets it.
Without Sidecar Steering, getting one back means editing the settings file the team shares.

Setup cannot tell a line the team deleted from one it never wrote, so a re-run reads each default it
would add back to the developer, and adds only what they agree to.
