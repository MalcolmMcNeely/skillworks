# The Suite runs on an Export branch

ADR 0056 lets a developer do small work on their own branch with no spec, and the skills that do it
end by running `skillworks-suite`, which read `docs/agents/suite.json` from disk and stopped there. So
`skillworks-suite` reads the Suite file from the local `origin/skillworks/steering` when the checkout
holds none, as `steering-file` does. A check's `image` Dockerfile comes from there too, with the rest
of its folder, because Docker builds from that folder. That folder is no file git lists on the
branch, so its tree on the Steering branch joins the check's Proof, and a Steering change to it runs
the check again.

This amends ADR 0056: a script that reads Steering on the developer's branch has the same fallback
as the skills.

## Considered options

**The Suite stops on an Export branch and says to run it on the Target branch.** Rejected. The small
work ADR 0056 allows has no Target branch, so it could never be checked.
