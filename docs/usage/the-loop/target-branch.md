# The Target branch

Part of [the Dev loop](../the-loop.md).

The **Target branch** is the branch a ticket Lands on. `target-branch` in `docs/agents/loop.json`
says which one it is. Setup asks you, and writes your answer there. It takes one of two kinds of
answer.

**A branch name**, such as `main`, `master` or `develop`. That branch is the Target branch for every
ticket of every spec. The loop cuts each Job branch from it, Lands each ticket on it, and pushes to it
straight away. The grill pushes each word and ADR to it as they settle.

```json
{ "target-branch": "main" }
```

Pick a branch name when your team pushes straight to that branch. Your GitHub login must be able to
push to it with no pull request and no status check. The preflight tests this, and stops if the push
would be refused.

**`spec`**. Each spec gets a branch of its own, `spec/<slug>`, and that branch is its Target branch.
Your team reviews the whole spec as one pull request to your default branch.

```json
{ "target-branch": "spec" }
```

Pick `spec` when your default branch is protected, or when your team reviews its work through pull
requests. The preflight checks that the default branch is on the remote, and does not care about its
protection. With `spec`:

- The grill makes `spec/<slug>` from the newest default branch when it settles the first word or ADR.
  It pushes it, and opens a draft pull request to the default branch. Each later word and ADR goes to
  that branch.
- When the grill settled nothing, `/skillworks:to-spec` makes the branch and the draft pull request.
- `/skillworks:to-spec` writes the branch name into the spec, under `## Branch`. The loop reads it
  there.
- Each ticket Lands on `spec/<slug>` exactly as it would on a branch name. Blocking, the push race and
  the Turn work the same. A closed ticket still means its code is on its Target branch.
- After the drift check, the loop marks the pull request ready for review, and stops. It never merges.
  A person reviews it and merges it.
- With the files Tracker, the loop never calls `gh`. It closes the spec, and its last lines tell you
  to open the pull request from the spec's branch on your host, or mark it ready for review.
- The pull request's body closes the spec, so the spec closes when the pull request merges.

Every other part of [the Dev loop](../the-loop.md) is the same for both kinds. Where it says the
Target branch, read the branch name you set, or `spec/<slug>`.
