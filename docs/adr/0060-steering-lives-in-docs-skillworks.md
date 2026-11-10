# Steering lives in docs/skillworks

Every file of a repo's Steering lives under `docs/skillworks/`, and no longer under `docs/agents/`.

`docs/agents/` came with the skills Skillworks borrowed on its first day, and other tools use it as
well. A team that ran one of them before setup already holds `docs/agents/issue-tracker.md` and
`docs/agents/domain.md` on its default branch. Setup merged the seed into those files on the Steering
branch, so a ticket that edits one carries Skillworks text onto the team's own branch, or stops the
Export. A folder named for the Plugin is a path no other tool writes.

Claude Code gives neither folder a meaning of its own. The rules reach every session through the
`@` imports in `CLAUDE.md`, and neither folder is a protected path, so the loop still writes its
Steering under `acceptEdits`.

This amends ADR 0035. The Steering stays in one folder, and only the folder's name changes.

## Considered options

**Keep `docs/agents/`, and warn in setup when a seed path is already on the default branch.**
Rejected. The warning reports the collision, but every team that used another tool with the same
folder still hits it.
