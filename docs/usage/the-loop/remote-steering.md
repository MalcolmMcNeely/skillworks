# Remote Steering

Part of [the Dev loop](../the-loop.md).

Remote Steering is for a developer who works for a client. Part of your Steering is your own way of
working: your method. The client must never get it. The rest is true only in the client's repo, and
the client keeps it when you go.

Keep your method in a private git repo of your own. That repo is your remote Steering. It is a fourth
Layer, beside the repo, the Sidecar and your user files. In each repo you name for it, `steering-file`
reads your remote Steering as well as the repo's Steering.

## The client repo never names the remote

The remote's URL, and the list of repos that read it, sit in one file in your own user files:
`~/.skillworks/remote-steering.json`. That file is outside every repo, so the client repo and its
Sidecar hold no URL, no commit and no file of your remote.

```json
{
  "url": "https://github.com/you/your-method.git",
  "repos": ["https://github.com/client/shop.git"]
}
```

A repo is listed by its `origin` URL, exactly as `git remote get-url origin` prints it. So a second
clone of the same repo reads the remote too. Each teammate who works by your method writes this file
on their own machine.

A repo reads the remote only when its `origin` is on the list and a URL is set. In any other repo,
`steering-file` reads exactly what it read before, and nothing warns.

## What loads in every Session

Your remote holds a `CLAUDE.md` at its root. Put an `@` import in it for each of your files that must
load in every Session, such as `@docs/skillworks/rules/method.md`. An import names a path from the
folder of the file that holds it, inside your remote.

In each repo you named, the Session start loads your remote's `CLAUDE.md` and each file it imports.
It follows imports up to five hops deep, the same as for the Sidecar's `CLAUDE.md`, and the same as
Claude Code. The text comes from the commit the Session holds. The client's `CLAUDE.md` names nothing
of your remote.

Under [Sidecar Steering](sidecar-steering.md), the Session gets both: the Sidecar's `CLAUDE.md` and
its imports, then your remote's.

In a repo you did not name, nothing of your remote loads.

## Each Session holds one commit

Every repo on your machine reads one local copy of the remote, kept in `~/.skillworks/`. Nothing
writes to the remote, and nothing pushes to it.

A Session fetches the tip of the remote's `main` with its first Steering read, and holds that commit
until it ends. Every later read in the Session gives the text of the commit it holds. So a change you
push mid-Session never reaches part of the Session. The next Session reads it.

When the fetch fails, the Session holds the commit last fetched to your machine. Each read then warns
that the text may be old:

```
WARN  remote Steering at https://github.com/you/your-method.git could not be fetched, so the copy last fetched, 3f9a2c1, is read, and its text may be old: ...
```

When your machine has never fetched the remote, the read fails, and names the URL and the fetch's
error. A repo you named must not be worked on without your method.

## Each run holds one commit

A run fetches the tip of the remote's `main` when it starts, and holds that commit until it ends.
Every Session of the run reads the run's commit, and none fetches a newer one. So a change you push
mid-run never reaches part of the run. The next run reads it.

The run writes the commit it holds to `.spec-loop/<n>/remote-steering.sha`, with the spec's number in
place of `<n>`. So you can trace a run's result to the version of your method it read. Git ignores
`.spec-loop/`, so the commit never reaches the client repo.

When the fetch fails, the run holds the commit last fetched to your machine, and its log warns that
the text may be old.

When your machine has never fetched the remote, preflight stops the run before it builds anything,
and names the URL and the fetch's error:

```
ABORT remote Steering at https://github.com/you/your-method.git could not be fetched, and this machine holds no copy of it: ...
```

In a repo you did not name, a run fetches nothing and warns about no remote.

## The remote holds no settings and no path rules

A setting is a fact about one repo. So every YAML block is read from the repo's Steering alone. When a
file in your remote holds a YAML settings block, preflight stops the run and names the file:

```
ABORT remote Steering at https://github.com/you/your-method.git holds a YAML settings block in docs/skillworks/rules/placement.md. A setting is a fact about one repo, so every YAML block is read from the repo's Steering alone. Move each block to the repo's Steering.
```

A path rule names paths in one repo. So path rules stay in the repo's Steering. When your remote holds
`.claude/rules/`, preflight stops the run:

```
ABORT remote Steering at https://github.com/you/your-method.git holds .claude/rules/. A path rule names paths in one repo, so path rules stay in the repo's Steering. Move them to the repo's .claude/rules/.
```

A remote that holds neither passes. Preflight reads the commit the run holds. A repo you did not name
is not checked.

## A file in both Layers is one file

The two Layers only add. Neither replaces any part of the other. You write both, so you keep them
from conflicting.

- A file only one Layer holds is read as it is.
- A file both Layers hold at the same path is read as one file: the repo's text, then the remote's.
- A folder read lists the files of both Layers.

Under [Sidecar Steering](sidecar-steering.md), the Sidecar's text comes first, then the remote's.
