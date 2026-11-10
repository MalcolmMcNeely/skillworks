# In PR mode the developer owns the branch and the pull request

A team's branch rule and its pull request rule win over the loop's. A team may name each branch by a
rule such as `<prefix>/<ticket-key>/<slug>`, and its tracker may move a ticket only on a push of a
branch with that name. A team may also say that a pull request opens only on an explicit go-ahead,
with a title, body and labels its own skill writes. The `spec/<slug>` branch and the draft pull
request the grill opened broke both.

So the value `spec` of `target-branch` becomes `pr`, for PR mode. The developer makes the branch,
starts the grill on it, and opens the one pull request after the loop ends. Skillworks cuts no branch,
opens no pull request and marks none ready. The grill, `to-spec` and `context-backfill` write on the
branch they start on, and stop on the default branch, on a branch under `skillworks/` and on no
branch. The Export is PR mode with the Steering kept off the developer's branch, so `"export": true`
needs `"target-branch": "pr"`.

A `loop.json` that still says `spec` is refused, with a line that says to write `pr`. Spec mode cut a
branch and opened a pull request, and PR mode does neither, so reading the old value as the new one
would change what a team gets without telling it.

This amends ADR 0036: each spec is still one pull request, and the grill no longer creates the branch
or the pull request.

## Considered options

**Skillworks cuts the branch from a pattern the team sets in `loop.json`.** Rejected. A pattern can
match the shape of a name but not the ticket key in it, so the developer still has to supply that,
and the branch is then the developer's in all but the command that cuts it.

**Keep spec mode beside PR mode.** Rejected. No team asked for the grill to open its pull request, and
two modes are two paths to test.
