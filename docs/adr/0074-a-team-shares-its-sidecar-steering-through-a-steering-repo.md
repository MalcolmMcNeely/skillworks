# A team shares its Sidecar Steering through a Steering repo

This supersedes ADR 0067 and ADR 0068. Remote Steering was one developer's own method, read from a
bare repo in their user files and added after each repo's text. It could not hold a setting, so a team
under Sidecar Steering still kept a full copy of its Steering in each member's Sidecar, and the copies
drifted.

Now the Sidecar is a clone of a Steering repo. The Sidecar is already a git repo, so it gains a remote
and nothing else. Each repo names its own Steering repo, so one machine can serve many clients. The
Steering repo holds the whole Steering of one repo, settings and Claude Code's settings among them, and
the Sidecar's specs and tickets stay out of it. Every script reads the Steering as files on disk, as
it does today, so no step makes a git call to read a file.

A person's Session pulls the Steering repo once when it starts, and before it loads the rules, so
every text in that Session comes from one commit. A run pulls once when it starts, and its Sessions
pull nothing, so a run reads one commit from start to end. A pull that fails warns, and the Session or
run goes on with the copy on disk. A team member changes the Steering with plain git in the Sidecar:
edit, commit, push. No script pushes to the Steering repo.

The shared Claude Code settings install the Plugin from GitHub at a pinned commit, so nothing in them
belongs to one machine, and a team moves to a new Plugin by moving the pin in the same repo as the
Steering that Plugin reads.

## Considered options

**Keep remote Steering, and let the remote win a file both Layers hold.** Rejected. It keeps the bare
repo, a git call for each read, and the merge of two Layers, and makes the merge larger to carry JSON
and YAML. Every script would need a resolver that reads the remote too.

**One Steering repo for each client, with a folder for each of its repos.** Rejected for now. A client
with one repo, the common case, gets one Steering repo either way, and the folder adds a path to
resolve and two clones of one repo on one machine. A client with many repos copies the text the repos
share.

**Pull only at `/grill` and `/spec-loop`.** Rejected. The SessionStart hook loads the rules before a
command runs, so a later pull leaves the Session holding older rules than the files it reads.

## Consequences

A developer's own method no longer goes to every repo they work in. It lives in their own
`~/.claude/CLAUDE.md`, which Claude Code loads in every Session.
