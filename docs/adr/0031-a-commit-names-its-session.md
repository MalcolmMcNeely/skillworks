# A commit names its Session

Every commit a Session makes carries a `Skillworks-Session: <id>` trailer, where the id is the
`session.id` telemetry carries, so a commit leads to the Session that wrote it. A `PreToolUse` hook
in the Plugin adds it to each `git commit` Claude runs, and denies, with its reason, a commit it
cannot rewrite safely, so Claude runs it again in a plain form. A link that goes missing without a
word is worse than none, because a reader trusts the history that has it.

The Keep makes its commit inside a script, where no hook sees it. So the driver picks each Session's
id before it starts the Session, and records it beside the ticket's worktree. The Keep names every
Session that ran on the ticket, since the Session running at the stop never reported its id.

## Considered options

**A git `prepare-commit-msg` hook.** Rejected. Git takes its hooks from each clone and never from a
plugin, so a fresh clone with nothing installed would make commits with no trailer and no warning.

**Reuse the `Claude-Session:` key.** Rejected. Claude Code on the web writes it with a URL, so one
key would hold two kinds of value.

**Let a commit the hook cannot rewrite run as it is.** Rejected. It is the quiet miss the trailer
exists to prevent.

## Consequences

The trailer is optional where a ticket Lands, because the hook and the Keep are what make it
reliable. An amend by a second Session adds a second line, and both stay, because both Sessions
wrote the commit. A git alias hides the word `commit`, so a commit made through one is not seen.
