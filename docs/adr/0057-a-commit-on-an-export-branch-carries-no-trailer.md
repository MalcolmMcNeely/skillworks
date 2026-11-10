# A commit on an Export branch carries no trailer

The Export branch is the developer's own branch, and it belongs to a team that may not use Skillworks
and may forbid trailers. The Steering branch's `session-trailer` answer speaks for the loop's
branches, where the trailer is wanted, so it cannot speak for this one too. So the Plugin's hook
leaves a commit as it was typed when `docs/agents/loop.json` is missing on disk and the local
`origin/skillworks/steering` exists, the same test the SessionStart hook uses. It adds no
`Skillworks-Session`, no credit line and no `Ticket`, a `Ticket` the developer typed stays, and the
hook no longer refuses a commit there that it could not rewrite.

This amends ADR 0031, ADR 0046 and ADR 0053. A commit Claude makes on an Export branch leads to no
Session.

## Considered options

**Read `loop.json` from the Steering branch.** Rejected. Its answer is `show` for the loop's branches,
so the trailer would still reach the team's branch.

**A second setting for the Export branch.** Rejected. Nothing reads the trailer there, and the Export
already writes its own commits with none, so a setting would only choose noise.
