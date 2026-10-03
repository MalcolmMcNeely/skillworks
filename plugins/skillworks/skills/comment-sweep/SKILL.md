---
name: comment-sweep
argument-hint: "[paths or a commit range]"
description: Sweep comments back to what this repo's comments rules keep, cutting first and then compressing each survivor to one line. Use when the user asks to sweep, cut, tidy or trim the comments on a diff, a commit range or a set of files.
---

# Comment sweep

Two passes over the comments in scope. **Cut** decides which comments exist. **Compress** decides how long they are. Keep the passes separate. Judged together, a weak comment survives because effort was just spent rewording it.

The sweep only removes and shortens, and turns a banned doc comment into an ordinary one.

## What is in scope

The default target is the uncommitted change: every file `git status` lists, untracked files included. A file git does not track yet shows in no `git diff`, so read it whole. When the request names paths or a commit range, sweep that instead. Any other text that arrives with the request is not a target: a script that starts the sweep adds instructions of its own after the command.

Two kinds of comment are out of scope in every file, and neither pass touches them: a doc comment the rules allow, and anything the rules say a sweep leaves alone. A doc comment the rules ban is not one of them: judge it like any other comment.

For every other comment, the target decides. In a file the request names by path, each one is in scope. In a change, the uncommitted one or a commit range, each one in a file the change created is in scope. In a file the change only modified, the ones in scope are the ones the change added or reworded. A comment the change did not touch stays as it is, because the sweep tidies one change, and a reader of that change should find no line in it that the change had no reason to touch.

## The rules

`docs/agents/rules/comments.md` at the repo root holds the rules, and nothing else does. Read it before pass 1. It decides what a doc comment is, where doc comments may go, and which comments earn their place. Its keep and cut table, under "What a sweep keeps and cuts", is the team's taste: judge by it, and leave alone what it says to leave alone.

If the file is missing, stop. Tell the user that `docs/agents/rules/comments.md` is missing, that `/skillworks:skillworks-setup` writes it, and that nothing was swept. Under the spec loop this is work you cannot do, so begin the report with a line that starts with `BLOCKED` and holds that message: the driver reads that line and stops the loop at once.

## Pass 1: Cut

For every comment in scope, ask what the rules and their keep and cut table ask. Keep the comments they keep. Cut the rest, and leave the survivors' wording alone. Length is pass 2's job.

**Done when** every comment in scope has been judged.

## Pass 2: Compress

Each surviving comment becomes one line. A surviving doc comment that the rules ban becomes an ordinary comment. Say the reason and stop, with no preamble ("Note that…", "This function…") and no restating of the mechanism it qualifies.

A comment that resists one line is usually explaining rather than recording. Re-ask whether it survives at all.

```
// This function handles the case where a user has several active
// sessions. Because the session store is keyed by user ID rather than
// session ID, we have to compare timestamps to find the most recent
// one, otherwise we might pick up an expired session.
```

becomes

```
// Session store is keyed by user, not session, so the newest timestamp wins.
```

**Done when** every surviving comment in scope is one line and meets the rules.
