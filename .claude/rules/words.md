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

A list grows one line at a time, as its glossary settles each word. Several _Avoid_ entries in
Studio's glossary are ordinary English the code needs, such as `run` and `block`, and one is another
entry's headword, so they are not on the list.

A folder in `skip-folders` holds a record of a question already answered. Its words are history, and
history is not renamed, so this rule skips it. The placement rules still judge it. No folder here is
such a record, so the list is empty.

Settling a new word is one line here. Add the winner to the context's glossary with the loser under
_Avoid_, then add the loser to that context's list.

```yaml
banned-words:
  studio:
    - Firing
    - Skill call
    - Stint
    - Stretch
    - Brush
    - Main thread
  architecture: []
skip-folders: []
```
