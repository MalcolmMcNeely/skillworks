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

The hook keeps each commit's own text word for word and adds only `--trailer` arguments after it, so
an allow rule the command matched still matches. How git settles a trailer the message already holds
lives in the repo's local git config, which every worktree of a clone shares:
`trailer.Skillworks-Session.ifExists=addIfDifferent`, `trailer.Co-Authored-By.ifExists=addIfDifferent`
and `trailer.Ticket.ifExists=replace`. Before each commit it rewrites, the hook writes all three with
`git config --local` in the repo at the Session's `cwd`, when one is missing or holds another value,
and it writes the Plugin's value over a team's own. A locked config gets 3 more tries, 200 ms apart.
When the write still fails, or `cwd` is no repo, the commit goes on with its trailers and without the
rules. The hook never answers "allow", so the team's own permission rules decide each commit.

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

**Put the rules before `commit`, as `git -c trailer.<key>.ifExists=... commit`.** Rejected. Claude
Code matches an allow rule against the command the hook hands back, and `git -c k=v commit` does not
match `Bash(git commit:*)`. Every commit a loop Session made in `acceptEdits` mode then asked for an
approval nobody gave.

**Put the rules in the `env` block of `.claude/settings.json`, as `GIT_CONFIG_COUNT` and its
pairs.** Rejected. A loop Session cannot write under `.claude/`, and `GIT_CONFIG_COUNT` can clash
with a team's own.

**Have the hook answer "allow" for the commit it rewrites.** Rejected. An "allow" skips the team's
own ask rules, and the hook has no call to overrule them.

## Consequences

The finish step still checks that git reads the `Ticket` trailer, so a commit the hook never saw,
such as one made through a git alias, is mended before Land. A repo with no `co-authored-by` key keeps
whatever credit Claude Code gives it, because it chose nothing. A commit made with `-F` holds its
message in a file the hook cannot read, so a credit line typed there is not refused. A clone's
`.git/config` gains three lines on the first commit the hook rewrites there, and setup writes nothing
for them. `addIfDifferent` never removes or changes a person's `Co-Authored-By` line. A commit made
before the rules are written falls back on git's own rule, and the `ticket-trailer` check in `finish`
stays the net for a `Ticket` that went wrong.
