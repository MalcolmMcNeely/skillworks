# The hook writes every trailer a commit carries

Claude Code told each Session to end its commit message with a `Co-Authored-By` line, and models
wrote that line as a paragraph of its own. Git reads trailers only from the last paragraph, so the
`Ticket` line above it became body text, and Land refused the commit after its Session had gone. The
docs already said where a trailer goes, and the models broke the rule anyway. So no model types a
trailer the loop relies on. Claude Code's own commit credit is always off, and the Plugin's
`PreToolUse` hook adds each trailer with `git commit --trailer`, which git always puts in the
message's trailer block: `Skillworks-Session` on every commit, `Ticket` on a loop Session's commits
with the value the driver hands that Session, and `Co-Authored-By: Claude <noreply@anthropic.com>`
when `co-authored-by` in `docs/agents/loop.json` says `show`. Pull requests keep Claude Code's own
credit, set from the same answer.

## Considered options

**Keep Claude Code's credit, and let the hook add only `Ticket`.** Rejected. Git would put `Ticket`
in the credit's block, but the model would still type a trailer, and a typed trailer is what went
wrong.

**Name the model in the credit, as Claude Code does.** Rejected. The `PreToolUse` hook is not told
the model, and a Session can switch models or hand work to a sub-agent on another one. A fixed line
is always true, and the Session trailer leads to the exact model.

**Remove a credit line the model typed.** Rejected. The line sits inside shell quoting, and an edit
there can break the message or the command. The hook refuses the commit with its reason, and the
Session runs it again without the line, as it already does for a commit the hook cannot rewrite.

**Let git's `replace` rule settle a second credit line.** Rejected. It deletes the nearest
`Co-Authored-By` line, which can be a person's. For `Ticket` it is safe, because a loop Session works
on one ticket, so the hook replaces a `Ticket` line the model typed.

**Hand a hand run's Session its ticket through a command.** Rejected. The model would still have to
remember to run the command. A hand run types its own `Ticket` line, and the credit instruction that
stranded it is gone.

## Consequences

The finish step still checks that git reads the `Ticket` trailer, so a commit the hook never saw,
such as one made through a git alias, is mended before Land. A repo with no `co-authored-by` key keeps
whatever credit Claude Code gives it, because it chose nothing. A commit made with `-F` holds its
message in a file the hook cannot read, so a credit line typed there is not refused.
