# Words

The YAML block at the end holds the words that lost, one list per context. `CONTEXT-MAP.md` names the
contexts and says which glossary judges which file, and that glossary says which word won.

Every word in `banned-words` was weighed against another word and rejected. No source file uses a word
that lost in the context that claims it, in any letter case. A word that lost in one context is free
in another, and a file no context claims is judged by no list. The check reads the whole text of a
file, so a word that lost cannot survive in a comment or in screen text either.

Every context in the map carries a list, and every list names a context in the map. A context with no
word to ban carries an empty list, written `[]`, so a list that judges nothing says so rather than
going missing.

A match is a whole word, and the words of a name run together. `SkillCall`, `skill_call` and
`skill call` all use the banned **Skill call**, because nothing, an underscore, a hyphen or one
space joins the two words. Any other mark ends the name, so `skill, call` is two words and is free.
A word that merely holds a banned word is free as well, so **Tool call** keeps working: the banned
entry is the compound, and never the bare word "call".

A list grows one line at a time, as its glossary settles each word, and not every loser reaches one.
Several _Avoid_ entries in Studio's glossary are ordinary English the code needs, such as `run` and
`block`, two are another entry's headword, and some are what a platform calls a thing, such as
`fetch` and `http`. A word the code cannot stop using is a word no list can ban. The glossary turns
down the rest on its own, and one joins its list on the day the code reaches for it again.

A folder in `skip-folders` holds a record of a question already answered. Its words are history, and
history is not renamed, so this rule skips it. The placement rules still judge it. No folder here is
such a record, so the list is empty.

Settling a new word adds the winner to the context's glossary with the loser under _Avoid_. The
loser joins that context's list on the day the code reaches for it again.

```yaml
banned-words:
  studio:
    - Firing
    - Skill call
    - Stint
    - Stretch
    - Brush
    - Main thread
  architecture:
    - Feature
skip-folders: []
```
