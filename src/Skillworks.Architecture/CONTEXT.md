# Architecture

How the code of this repository is laid out, and the check that holds it there. Studio is the app;
this context is the shape Studio's code has to keep.

## Language

**Context**:
One product area, with a language of its own. Two contexts exist when one word has to mean two things
and neither meaning can win.
_Avoid_: Domain, area, boundary

**Glossary**:
The file that holds a Context's words. `CONTEXT-MAP.md` names one for each Context, and that file is
what the check reads to decide whether a word has been settled.
_Avoid_: Dictionary, lexicon, vocabulary

**Headword**:
One word a Glossary settles, written bold and alone on its line. It is the name a folder in `Shared`
has to carry.
_Avoid_: Term, entry, keyword

**Slice**:
The folder that holds everything one job of the app needs. An agent changing that job opens the Slice
and nothing else.
_Avoid_: Feature, module, vertical, component

**Shared**:
The one folder for code no single Slice owns. It sits at the top of a code root and nowhere else.
_Avoid_: Common, utils, helpers, misc

**Concern**:
A folder inside a Slice that groups the types playing one role.
_Avoid_: Layer, tier, category

**Code root**:
The folder a project's code starts in: a folder holding a `.csproj`, and the front end's `src`.
_Avoid_: Project root, source root

**Subject**:
A file's name up to its first dot. A type, its aspect files and the test beside it share one.
_Avoid_: Stem, base name

**Source file**:
A file the check reads, tests included.

**Code file**:
A source file that is not a test.

**Support file**:
A code file that tests use: a host, a fake, or a record a test reads a response into.
_Avoid_: Fixture, stub, double

**Aspect file**:
One part of a type too large for a single file, named `Subject.Aspect.cs`.
_Avoid_: Partial, split file

**Rule**:
One thing the code has to be true of. Its text lives in `.claude/rules/`, and the settings it names
live in the YAML block at the end of that file. The `contexts` rule is the one exception: its text
and its settings live in `CONTEXT-MAP.md` at the repository root, because the map is what a reader
opens to learn which glossary judges a file.

**Breach**:
One place the code is not true of a Rule. It names the Rule, the path and what to do.
_Avoid_: Violation, error, failure
