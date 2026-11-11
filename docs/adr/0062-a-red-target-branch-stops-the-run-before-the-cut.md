# A red Target branch stops the run before the Cut

A fault the Target branch already holds is not the spec's to mend. Left to the loop, it went to the
fix Session: in one run a new package advisory broke the build on the Target branch, and a fix
Session spent an hour suppressing it, a security choice made by the loop that rode into the spec's
pull request. A machine that was not ready was found only at the Suite step, after the Cut and a full
build were paid for.

So each run checks a Baseline after it fetches the Target branch and before the Cut. In a worktree
of its own, cut from the Target branch on `origin`, it runs the `ready` command of each check in
`suite.json`, then the optional `baseline` command, which the team names as it names its checks.
Either one red stops the run, and no Session is asked to mend it. The Suite step keeps its own
readiness check, because a container can stop during a long run.

## Considered options

**Let the fix Session mend a red the Target branch holds.** Rejected. The fault belongs to the team's
own code, a fix there rides into a spec that did not ask for it, and the Session pays for it on every
spec until someone fixes it where it lives.

**Run the whole Suite on the Target branch at the start.** Rejected. It catches red tests as well as
a broken build, but it costs one full Suite on every run, seventeen minutes on the repo that showed
the fault, before any work starts.
