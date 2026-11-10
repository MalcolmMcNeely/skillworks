# A session on an Export branch reads its Steering from the Steering branch

With the Export, the Steering lives on the Steering branch alone, so a session started on an Export
branch had no rules, no `## Agent skills` block in `CLAUDE.md`, and no Steering file on disk. The grill
skipped the Surfaces, `to-spec` could not see that the Export was on, and every skill that reads a
rule ran without it. Claude Code loads `CLAUDE.md` once, when a session starts, so moving to the
Target branch part way through a session never brings the rules in.

So a session on an Export branch reads its Steering from `origin/skillworks/steering`, by three parts:

- The Plugin's SessionStart hook gives the session the `CLAUDE.md` of the Steering branch and each
  file it imports with `@`, when `docs/agents/loop.json` is missing on disk and the local
  `origin/skillworks/steering` exists.
- Every skill reads a Steering file through one command, `steering-file <path>`. It prints the file
  from disk, and from the local `origin/skillworks/steering` when the file is missing on disk.
- The grill cuts the Target branch before its first question, when `docs/agents/loop.json` is missing
  on disk. It is the only skill that cuts. `domain-modeling` and `to-spec` no longer cut, and stop on
  an Export branch.

Nothing fetches. The hook has 5 seconds, and `cut-target-branch` fetches and pushes the Steering
branch for each spec, so the local copy is new enough. A skill that writes a Steering file stops on an
Export branch, because a Steering change is made and committed on the Steering branch.

This amends ADR 0054: the grill cuts the Target branch at its start, and not when the first word or
ADR settles.

## Considered options

**A separate skill that cuts, then a new session.** Rejected. It costs a session thrown away and a
step for each spec, and the grill already runs on the Export branch.

**Each skill stops on an Export branch.** Rejected. A developer in a team that does not use
Skillworks often does small work on their own branch with no spec, and a skill that stops is no help
there.

**Each skill reads the rules itself.** Rejected. Each skill must remember to, and the session's own
work outside a skill would still have no rules.

**Fetch the Steering branch before each read.** Rejected. Every session start and every read would
wait on the network, and the hook could run out of time.
