# A judge at the end of the loop never edits, and its checks are the Plugin's own

Once every ticket of a spec has Landed, the loop runs a Deepening check and a Simplify check before
the drift check. Each is a judge in a Fresh Session. It records a report with the spec and changes no
code. The script turns what it found into tickets from a fixed template, and a build Session applies
each one through the steps every ticket takes. So every change the loop makes, at the end as in the
middle, gets the three reviews, the sweep, the Suite and Landing, and there is one way for the loop to
change code and one set of stops for it.

Both judges are Hidden skills of the Plugin, `spec-deepen` and `spec-simplify`. `spec-deepen` takes
its rules from `codebase-design`, and `improve-codebase-architecture` stays as it is, for a person who
wants the report and the grill. `spec-simplify` looks from the four angles Claude Code's `/simplify`
uses: reuse, simplification, efficiency and altitude.

## Considered options

**Let each new step edit the code, with a standards review and a sweep after it.** Rejected. It is a
second way to change code beside the ticket steps, and it needs Nudges, a Keep and stop lines of its
own. A refactor made that way skips the spec and architecture reviews.

**Run Claude Code's `/simplify` as the build of a simplify ticket.** Rejected. On the Target branch,
after every ticket has Landed, its default diff is empty or only the last commit, so it would not see
the spec's work. Its text is not ours, so a Claude Code update can change what the loop does, and no
test can match it. And it ties the loop to Claude Code a little further.

**Give `improve-codebase-architecture` an unattended mode.** Rejected. One file would hold two
processes, one that asks a person and one that asks nobody, and the tests and the driver match the
exact text of a skill, so a change to one process could break the other.

## Consequences

A candidate that goes against an ADR never becomes a deepening ticket. A person made that decision,
so only a person reopens it, and the report lists the candidate for them.
