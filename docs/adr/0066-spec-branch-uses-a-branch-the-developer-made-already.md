# spec-branch uses a branch the developer made already

In PR mode `spec-branch` refused any name already on `origin` or in the clone. A developer who had
cut their branch by hand, and started the grill on it, could not name it, and the grill could not go
on. Many teams cut the branch first, and the rule that blocked them guarded nothing the loop needs.

So `spec-branch` uses a branch that is already there. A branch on `origin` opens at its own tip. A
branch only in the clone is pushed first. When a worktree, such as the checkout, already holds the
branch, that worktree is the grill worktree, because git checks a branch out in one place only, and
`to-spec` removes a grill worktree only when it sits under `.spec-loop/grill/`.

Two refusals stay, because they are what ADR 0064 fixed: the default branch, and a name an open spec
holds. Two specs still never share a branch, and a developer who starts on the default branch can
still grill many specs at once.

This amends ADR 0064.

## Considered options

**Drop every branch rule, and write on whatever branch the checkout is on.** Rejected. It brings back
what ADR 0064 fixed: two specs on one branch, and one grill at a time.
