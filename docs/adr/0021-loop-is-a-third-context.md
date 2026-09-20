# Loop is a third context

The Claude setup and the scripts that drive it are a product area of their own, and no glossary
governed them. `.claude/` and `scripts/` were claimed by no context, so nothing judged the words in a
skill file or the shape of a script. That setup is what this repository exists to publish, and it was
the one part of the tree with no language settled for it.

So `.claude/CONTEXT.md` holds Loop's glossary, `CONTEXT-MAP.md` claims `.claude`, `scripts` and
`tests/scripts` for it, and `words.md` carries its list. **Load** is its first word: one instruction
file reaching a session, named so a session can be read for what it was given.

The map already said a context waits until it has code the check can judge. Loop's code is shell and
node, so `.sh`, `.ps1` and `.mjs` joined `source-files` and the rule is met rather than bent.

## Considered options

**Its words sit in Studio's glossary until later.** This is what the map says about the catalogue,
which has no code at all. It was rejected because Loop does have code, and because a word that
belongs to the agent setup put in the app's glossary teaches the next reader that the two are one
thing. They are not: Studio does not know the setup exists.

**A glossary with no judged code.** It was rejected because it breaks the map's own rule on the day
it is written, and a rule broken by the first file to use it is not a rule.

## Consequences

`tests/scripts` holds the tests for `scripts`, which is the mirror a C# project already has to its
`.Tests` project and which the check had no way to express. `test-roots` names that pair as data, so
a language with no project file is not stuck with "beside".

`.handoff` joined `skip-folders`. It is transient and belongs to one machine, so judging it would let
the same commit pass in one checkout and fail in the next. That is a second reason for a folder to be
skipped, and the text had only the first.

The check reads the filesystem and never asks git, so a folder being ignored by git does not put it
out of reach. Anything that should be left alone has to say so in `skip-folders`.
