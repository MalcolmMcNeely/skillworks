# Glossary words are committed as they settle

More than one person runs agent work against this repo, and a grill can sit open for an hour while
the developer thinks. A word settled in that hour lives only in one session's context, so a teammate
grilling beside it can reserve the same word for something else, and one of the two designs then has
to be re-grilled. So every skill that writes `CONTEXT.md` or an ADR commits and pushes the change at
the moment it settles, rather than at the end of the session. The subject line starts `Glossary:` or
`ADR:`, so the log says which kind of change it was without anyone opening it.

A push has to pull first, so the check comes free with it. A skill that pulls a teammate's change to
either file reads it, and speaks up when it touches ground this session already settled. What to
re-ask is then a question for the session that read it.

## Considered options

**Commit at the end of the session.** `/to-spec` already does this, and it is what this replaces as
the first guard rather than the only one. It was rejected because the window it leaves open is the
whole grill, and the grill is exactly where the words are chosen.

**Reserve words out of band, in a shared file or a tracker issue.** It was rejected because a second
place to look is a second place to forget, and the glossary is already the one place the words live.

## Consequences

The history carries many small commits that touch one file. That is the price, and the prefix is
what keeps them readable.

A skill stops mid-conversation to run git. `/domain-modeling` holds the rule, so `/grill-with-docs`,
`/wayfinder` and `/improve-codebase-architecture` all inherit it. Staging is by path, so work in
progress elsewhere in the tree is never swept into a glossary commit.

A word can now be pushed for a design that is later abandoned. Removing it is one more small commit,
and a word nobody uses costs less than a word two designs fight over.
