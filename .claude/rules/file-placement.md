# File placement

The YAML block at the end holds the settings these rules name. When code breaks a rule, move or
split the code until it fits. The settings change only when the developer asks.

## One shape

C# and TypeScript share one shape: Slices first, Concerns beneath.

- A **code root** is the folder a project's code starts in: a folder that holds a `.csproj`, and the
  front end's `src`.
- A **Slice** is the folder that holds everything one job of Studio needs. `slices` names them. A
  type goes in the Slice whose job it serves.
- A **Concern** groups the types that play one role inside a Slice. In the front end `concerns` names
  them, and `src/Skillworks.Studio.Web/.dependency-cruiser.cjs` holds the boundaries between them.
- **`Shared`** holds the code no one job owns, and a folder inside `Shared` is named for a word in
  the glossary.
- Every folder name says what its code serves or does, so the names in `banned-folder-names` are
  never used, in any letter case.
- Folders in `skip-folders` hold code these rules never judge. A folder earns its place for one of
  two reasons: nobody writes its code by hand, or it is transient and belongs to one machine, so no
  one else will ever read what is in it. Judging either would let the same commit pass on one
  machine and fail on the next.
- A folder with its own `.git`, such as an agent's worktree, is another checkout. These rules skip it
  too.

`src/Skillworks.Core/Watch/Activations` shows the shape beneath a Slice: the folder holds the types
of an Activation, and `Queries` beneath it holds `ActivationQueries`, as `name-map` says.

## Slices

An agent asked to change one job opens that job's Slice and nothing else. Eight rules keep it that
way.

They reach only the contexts that set `slices` to `true` in `CONTEXT-MAP.md`, because a Slice is
named for a job an app does and not every context is an app. Code no context claims, and code in a
context that declares no Slices, is judged by the rest of these rules and by none of the eight.

1. **A Slice comes first.** Every folder at the first level under a code root is a Slice from
   `slices`, or `Shared`. `Shared` sits at that level and nowhere else, in any letter case. A file
   that sits at a code root itself, such as the program entry point or the router, is untouched.
2. **A Concern comes beneath, in the front end.** A folder inside a front-end Slice is named for a
   role from `concerns`, and that list is closed. In C# a folder inside a Slice is free grouping,
   held by `max-types-per-folder` and `name-map`.
3. **A Slice never reads another Slice.** No code file in a Slice names another Slice's namespace or
   imports from another Slice's folder. The rule reaches the first level only, so a Slice reading its
   own folders is free.
4. **`Shared` never reads a Slice.** The arrow runs one way, so a Slice can be read in full without
   opening anything above it.
5. **`Shared` has one door.** Every folder in `Shared` names a word from the glossary of the context
   that claims it, or the plural of one, because a folder holds many of a thing. Code with no word of
   its own settles one in the glossary before the folder appears, and machinery settles a word like
   everything else. The test runs on the piece and not on the word: a word in the glossary does not
   pull a Slice's code down with it. `Skill` is a word, but only the list of Skill names the Filter
   offers sits in `Shared`, while the Map, the Tiles and the skill report stay in Watch. What moves
   is what no one job owns, however many jobs happen to read it.
6. **A Slice keeps its name everywhere.** A Slice folder sits at the same depth, and under the same
   name in that language's own case, in every project that holds its code, and in the front end.
7. **Two Slices may hold a type with the same name.** They are two types about two jobs. Merging them
   is the defect, not the duplication.
8. **A new job gets a new Slice.** The glossary names the job, then `slices` gains a line, then the
   folder appears.

Rules 3 and 4 hold code files only. A test may read any Slice, because a test that checks a seam has
to see both sides of it. The exemption belongs to being a test, so no list of exempt tests is kept,
because a list goes stale.

A Slice name and `Shared` are matched in each language's own case: `Watch` and `Shared` in C#,
`watch` and `shared` in the front end. Rule 1 turns down a folder holding the right word in the wrong
case, and turns down `Shared` in any case below the first level, which is the work
`banned-folder-names` did for `shared` before `Shared` earned its place.

## Files

A file's **subject** is its name up to the first dot. A **source file** is a file in `source-files`,
tests included. A **code file** is a source file that is not a test. A **support file** is a code file
that tests use: a host, a fake or a record a test reads a response into.

- A C# file holds one top-level type, named as the subject. A private nested type or a `file` type
  can stay with the type it serves. Any other nested type gets its own file. A `Program.cs` with
  top-level statements is the one file with no type.
- Global usings go in the project file as `<Using>` items, so no C# file holds only usings. A
  `<Using>` reaches every file the project builds, so outside a test project it never names a Slice:
  rule 3 could not then tell which file did the reading.
- A large type splits across aspect files: `BlobRepository.Async.cs` holds `partial BlobRepository`.
- A C# namespace is the project's root namespace, then the folder path: a file in
  `Skillworks.Core/<Slice>/<Folder>/` is in `Skillworks.Core.<Slice>.<Folder>`.
- The root namespace is the `<RootNamespace>` in the project file when it is set and not empty, and
  the project file name otherwise. A `<RootNamespace>` in a shared build file, such as
  `Directory.Build.props`, does not count.

## Tests

A file whose name matches a pattern in `test-files` is a test. Its subject drops the test marker and
any aspect, so `BlobRepository.Lease.Tests.cs` tests `BlobRepository`. It holds `partial
BlobRepositoryTests`, and the other aspect files of that test class hold the other parts.

- Test folders mirror the folders of the code files they test. A C# test in project `X.Tests` sits at
  the same relative path as the code file it tests in project `X`.
- A front-end test sits beside the code file it tests.
- A test in a language with no project file sits beside the code file it tests, or at the same
  relative path beneath a test root. `test-roots` maps a test root to the folder it mirrors, so a
  script and the test that proves it stay apart the way a C# project and its `.Tests` project do.
- Support files sit beside the tests that use them, or in a folder named for what they do. The size
  limit, the name map and the banned names apply to them too.

## Folder size

A folder holds at most `max-types-per-folder` types. The count is the number of different subjects
among the source files that sit directly in the folder.

- A type, its aspect files and the test beside it share a subject, so they take one place.
- A test with no code file beside it counts as one.
- Subfolders count for nothing, so splitting a full folder into folders beneath it always makes
  room.

## Name map

Each pattern in `name-map` is a name with `*` at the start or the end, such as `*Queries` or
`Queries*`. It matches the subject, and letter case counts.

- A subject that matches one pattern sits in that pattern's folder.
- A subject that matches several patterns sits in the folder of any one of them.
- A subject that matches none goes where its Slice puts it.

```yaml
slices:
  - Watch
  - Sessions
concerns:
  - api
  - components
  - lib
  - routes
max-types-per-folder: 10
source-files:
  - .cs
  - .ts
  - .tsx
  - .sh
  - .ps1
  - .mjs
  - .py
test-files:
  - "*.Tests.cs"
  - "*.test.ts"
  - "*.test.tsx"
  - "*.test.sh"
  - "*_test.py"
skip-folders:
  - Migrations
  - bin
  - obj
  - node_modules
  - __pycache__
  - .venv
  - venv
  - site-packages
  - .handoff
banned-folder-names:
  - utils
  - helpers
  - common
  - misc
name-map:
  "*Queries": Queries
test-roots:
  tests/scripts: scripts
```
