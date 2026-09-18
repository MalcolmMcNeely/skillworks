# A context is a product area

Studio spends the word `slice` twice already, on a Part of a run and on a block of hours in the
activity strip, so `CONTEXT.md` puts it under _Avoid_. The word the code's own shape needs is the same
one. Both uses are right, and no single glossary can hold both, so the repository now holds two
contexts: Studio, the app, and Architecture, the check that holds the shape of the code.
`CONTEXT-MAP.md` names them and the paths each owns, and a word is banned only inside the context
that claims the file.

A context is a **product area**. A large repository splits its contexts by project; a small one, like
this, splits by folder. Neither the size nor the split is the test. The test is whether this is a
different product area, and the sign that it is one is that a word has to mean two things.

## Considered options

**One glossary, one winner.** Rejected. It would ban the word the architecture needs in order to keep
a word Studio spends on two small things, and it would keep doing that every time a second area grew
a language.

**A context per deployable.** Rejected. Studio is one deployable and the check is a library nothing
ships, so the count would be one, and the two languages would still be fighting.

**Split the catalogue out now as a third context.** Rejected for now, and written into the map as the
next one. The catalogue is a product area and `Skill` already means two things, but it has almost no
code of its own here: `plugins/` is empty and `Core/Catalogue` is four types Studio uses to read it.
A context with no code gives the check nothing to judge. It gets its own glossary the day Author or
Publish writes code.

## Consequences

The word check reads `CONTEXT-MAP.md` and keys its lists by context. A file no context claims is
judged by no list, and a path two contexts claim is a breach, so the map cannot drift away from the
tree.

`Slice` joins Studio's banned words only once the activity strip stops spelling it, which is the
discipline ADR 0015 set and ADR 0013 already applied to `Figure`.

A reader now has two glossaries to hold in mind. The map is what stops that being a burden: it says
which one applies where, in one screen.
