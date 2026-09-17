# Words

The YAML block at the end holds the words that lost. `CONTEXT.md` holds the glossary and says which
word won.

Every word in `banned-words` was weighed against another word and rejected. No source file uses one,
in any letter case. The check reads the whole text of a file, so a word that lost cannot survive in
a comment or in screen text either.

A match is a whole word, and the words of a name run together. `SkillCall`, `skill_call` and
`skill call` all use the banned **Skill call**, because nothing, an underscore, a hyphen or one
space joins the two words. Any other mark ends the name, so `skill, call` is two words and is free.
A word that merely holds a banned word is free as well, so **Tool call** keeps working: the banned
entry is the compound, and never the bare word "call".

The list grows one line at a time, as the glossary settles each word. Several _Avoid_ entries in
`CONTEXT.md` are ordinary English the code needs, such as `run` and `block`, and one is another
entry's headword, so they are not on the list.

A folder in `skip-folders` holds a record of a question already answered, such as a captured
prototype. Its words are history, and history is not renamed, so this rule skips it. The placement
rules still judge it.

Settling a new word is one line here. Add the winner to `CONTEXT.md` with the loser under _Avoid_,
then add the loser to the list.

```yaml
banned-words:
  - Firing
  - Skill call
  - Stint
  - Stretch
  - Brush
  - Main thread
skip-folders:
  - prototypes
```
