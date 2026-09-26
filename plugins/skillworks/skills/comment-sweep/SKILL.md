---
name: comment-sweep
description: Sweep comments back to what this repo's comments rules keep, cutting first and then compressing each survivor to one line. Use when the user asks to sweep, cut, tidy or trim the comments on a diff, a commit range or a set of files.
---

# Comment sweep

Two passes over the comments in scope. **Cut** decides which comments exist. **Compress** decides how long they are. Keep the passes separate. Judged together, a weak comment survives because effort was just spent rewording it.

The sweep only removes and shortens, and turns a banned doc comment into an ordinary one.

Default target is the uncommitted diff. Given paths or a commit range, use that.

## The rules

`docs/agents/rules/comments.md` at the repo root holds the rules, and nothing else does. Read it before pass 1. It decides what a doc comment is, where doc comments may go, and which comments earn their place. Where an example below and the rules disagree, the rules win.

If the file is missing, stop. Tell the user that `docs/agents/rules/comments.md` is missing and that nothing was swept.

## Pass 1: Cut

For every comment in scope, ask what the rules ask. Keep the comments the rules keep. Cut the rest, and leave the survivors' wording alone. Length is pass 2's job.

| Comment | Verdict |
|---|---|
| `// increment the counter` | Cut: restates the line below it |
| `// constructor` | Cut: the syntax already says so |
| `// loop through the users` | Cut |
| `// retry 3 times`, above `retries: 3` | Cut: the value says so |
| `// returns null on a cache miss, not undefined` | Cut: says what the code does, not why |
| `// 3 retries: the vendor rate-limits bursts above 4` | Keep: the reason lives nowhere in the code |
| `// must run before the auth middleware or the session is empty` | Keep: a hidden ordering constraint |

Linter and compiler directives (`eslint-disable`, `@ts-expect-error`, `#pragma`) and licence headers are out of scope. They are instructions to tools and legal text, not comments for a reader.

A doc comment the rules allow is out of scope too. One the rules ban is in scope: judge it like any other comment.

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

**Done when** every surviving comment is one line and meets the rules.
