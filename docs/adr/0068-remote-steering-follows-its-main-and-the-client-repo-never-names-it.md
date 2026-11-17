# Remote Steering follows its main, and the client repo never names it

A developer's remote Steering is a private repo, one for every client. The client repo holds no trace
of it: not its URL, and not a commit. The URL sits in the developer's own user files, so each
teammate sets it once on their own machine.

Every run reads the tip of the remote's `main`. The run fetches it when it starts and holds that
commit until it ends, so a change the developer pushes mid-run never reaches a ticket of that run. The
run writes the commit in its own files under `.spec-loop/`, which never go to the client, so a run's
result can still be traced to the version of the method it read. A person's Session fetches when it
starts as well, so the grill reads the same text as the run that builds its spec.

When the fetch fails, the Session or run reads the last copy it fetched, and warns. A machine that
has never fetched the remote stops the run at preflight, because a repo the developer named must not
be built without their method.

A change to the remote reaches every client on its next run. That is what the developer wants: the
method is one thing, and ADR 0067 makes a conflict between the two Layers the developer's to avoid.

## Considered options

**A pin in each client's `loop.json`.** Rejected. It holds each client still and records the version
in the client's history, but the client repo then shows a commit of a repo it cannot read, and the
developer has to move every client's pin by hand to share one change to the method.

**The URL in the client's `loop.json`.** Rejected. It names the developer's private repo to the
client.
