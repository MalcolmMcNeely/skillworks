# Every Load comes from the repository

Claude Code writes memory files under `~/.claude/projects/<repo>/memory/` and loads them into every
session. They are Loads, and their source is the machine rather than the repository, so one commit
steers two machines differently and a run cannot be read back from what the repository holds. Loop
turns auto-memory off, with `autoMemoryEnabled: false` in the repository's `.claude/settings.json`,
so every Load comes from a file the repository carries. `skillworks-setup` writes the same line into
every repository it configures.

## Considered options

**A developer's own settings.** Rejected. `~/.claude/settings.json` reaches every repository on one
machine and no repository on any other, which is the spread the decision is trying to close. It also
loses: Claude Code reads its five settings sources in the order user, project, local, flag, policy,
and the last one to name a key wins.

**A managed policy file.** `managed-settings.json`, or the `HKLM\SOFTWARE\Policies\ClaudeCode` key,
holds the line for every machine in the company, and no developer can undo it. Rejected for now,
because the rollout has to stay small and reversible and a policy is neither. It stays available the
day the company wants the line locked.

**The plugin.** Claude Code reads settings from five sources and a plugin is not one of them. A
plugin ships skills. Only `skillworks-setup` can write a repository's settings.

## Consequences

The memory files stay on disk. Removing the line is one commit, and the files the machine already
holds come back with it.

The line beats a developer's own toggle, because `/config` writes auto-memory to the user's settings
and the project file wins. A developer who wants memory back in one repository writes it into
`.claude/settings.local.json`, which is per-machine and never committed. `skillworks-setup` leaves
that file alone, because a conflict there can only be deliberate.

`scripts/skillworks-preflight.sh` warns when the line is missing, and warns rather than fails,
because a team that removed it on purpose should not have their loop stop.
