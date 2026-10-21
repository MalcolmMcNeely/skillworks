# The backfill evals answer the map question with the real map

The first run of Context backfill stops once and asks the person for the map, so a headless run in a
Blind clone resumes the Session with an answer. The harness answers with the real map's three
contexts, Studio, Architecture and Loop, and their folders, so every run sorts its Drafts the same
way, and the shape pass is scored on its own from what it wrote in `shape.md` before the question.

## Why

The evals compare two versions of the skill on the same Blind clone, and the comparison is only as
sharp as the noise between runs. Two runs of one skill version split Architecture two different ways,
once into Studio and once into Plugin, and every headword and decision count that is kept per glossary
moved with the split. Feeding the real answer takes that movement out of every pass after the shape
pass, and gives the shape pass a score of its own.

## Considered options

**Answer "a map with the contexts you found".** Rejected. It measures the sheet as a person would get
it, which is the honest whole, but the context split then changes between runs of the same skill and
nothing after it is comparable.
