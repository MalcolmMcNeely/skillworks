# Context backfill writes nothing a person has not accepted

The Context backfill reads a repo's code and history and writes what it finds as Drafts on an
Answer sheet in `.context-backfill/`, a folder setup keeps out of git. A word, a map or an ADR
reaches `CONTEXT.md`, `CONTEXT-MAP.md` or `docs/adr/` only after a person has written accept beside
it, and the skill never fills in a reason the history does not give.

## Why

Every other skill in the Plugin writes a word or an ADR the moment it settles, because a person
settled it in the same session. The backfill settles nothing: it reads what people wrote years ago
and works out what they meant. A study that asked a model to supply the reason for changes whose
reason was never written down found it right about one time in four. A record in `docs/adr/` is read
by every later Session as a fact, so a wrong one steers every later change, and nobody is left who
remembers it was a guess.

## Considered options

**Write each find straight into the repo with a `proposed` status.** Rejected. A proposed ADR in
`docs/adr/` is read like any other: `docs/agents/domain.md` tells a Session to read them all, and
nothing tells it to doubt one.

**Talk each find through in the session.** Rejected. The person who knows why is often not the one at
the keyboard. A file can be handed to the teammate who was there, and a session cannot.

**Let the skill write a reason it inferred, marked as inferred.** Rejected. The mark does not
survive. The next grill reads the sentence and not the mark, and one wrong reason in four is still
the record's content.

## Consequences

A backfill is two runs and not one: a run that writes the sheet, and a run that applies the Answers.
A find with no reason in the history is a Question on the sheet, and it becomes an ADR only when a
person writes the reason.
