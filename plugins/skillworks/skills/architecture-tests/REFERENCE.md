# The rules, and what can test each one

One section per rule file in `docs/agents/rules/`, and one row per rule, with the settings it reads. Each row names the common tool for TypeScript, .NET and Go where one fits, and the starter test where none does.

A **starter test** is a test the team writes in its own language and runs in its own test runner. It reads the rule's YAML block at every run, walks the files the rule reaches, and skips `skip-folders` and any folder with its own `.git`. The rules any language checks the same way need one: folder size, banned folder names, the name map, where tests sit, and banned words.

A dash means the rule does not reach that language. "Left to the team" means no common tool and no plain file check can prove the rule, so a review judges it.

Python and Java tools were not weighed. A repo in either gets a starter test.

## `file-placement.md`

| Rule | TypeScript | .NET | Go | Starter test |
|---|---|---|---|---|
| **A Slice comes first.** `slices` | @boundaries/eslint-plugin, with one element per Slice and one for `shared`, so a first-level folder that is neither is an unknown file | — | — | Every folder at the first level under a code root is in `slices` or is `Shared`, in the language's case, and `Shared` sits nowhere deeper |
| **A Concern comes beneath, in a front end.** `concerns` | @boundaries/eslint-plugin, with the Concerns as elements beneath each Slice | — | — | Every folder inside a front-end Slice is in `concerns` |
| **A Slice never reads another Slice.** | dependency-cruiser, a forbidden rule from `^src/([^/]+)/` to any path under `src/` outside `$1` and `shared`; or @boundaries/eslint-plugin | ArchUnitNET or NetArchTest: types in one Slice's namespace have no dependency on another Slice's namespace | go-arch-lint, one component per Slice; or depguard in golangci-lint | — |
| **`Shared` never reads a Slice.** | dependency-cruiser, a forbidden rule from `^src/shared/` to any Slice; or @boundaries/eslint-plugin | ArchUnitNET or NetArchTest: types in `Shared` have no dependency on a Slice's namespace | go-arch-lint, with `Shared` allowed no Slice | — |
| **`Shared` has one door.** | — | — | — | Every folder in `Shared` is a headword of the glossary the context map names, or its plural |
| **A Slice keeps its name everywhere.** | — | — | — | Each Slice folder sits at the same depth, under the same name in each language's case, in every code root that holds it |
| **Two Slices may hold a type with the same name.** | — | — | — | Left to the team: the rule forbids nothing, and the merge it warns against is a review's call |
| **A new job gets a new Slice.** | — | — | — | Every name in `slices` is a headword of the glossary, so a Slice cannot appear before its word |
| A C# file holds one top-level type, named as the subject | — | StyleCop.Analyzers, SA1402 and SA1649 | — | Left to the team: telling a type from a nested type needs a C# parser |
| Global usings go in the project file | — | — | — | No `.cs` file holds only `using` lines, and outside a test project no `<Using>` names a Slice's namespace |
| A large type splits across aspect files | — | — | — | Left to the team: proving a file holds `partial` of its subject needs a C# parser |
| A C# namespace is the root namespace, then the folder path | — | IDE0130, with `dotnet_style_namespace_match_folder` and `EnforceCodeStyleInBuild` | — | — |
| Where tests sit. `test-files`, `test-roots` | — | — | — | Every file matching `test-files` mirrors the code file it tests: at the same path in project `X` for a test in `X.Tests`, beside it in a front end, or beneath the test root `test-roots` maps |
| Folder size. `max-types-per-folder` | — | — | — | No folder holds more different subjects among its source files than `max-types-per-folder` |
| Name map. `name-map` | — | — | — | A subject that matches a pattern in `name-map` sits in that pattern's folder |
| Banned folder names. `banned-folder-names` | — | — | — | No folder is named for an entry in `banned-folder-names`, in any letter case |
| What every starter test reads. `source-files`, `skip-folders` | — | — | — | Read by every starter test above: the file kinds it counts, and the folders it skips |

## `determinism.md`

| Rule | TypeScript | .NET | Go | Starter test |
|---|---|---|---|---|
| Shipping code reads time through the Clock. `clock`, `contexts` | ESLint core `no-restricted-properties` and `no-restricted-syntax`, for `Date.now`, `new Date()`, `performance.now`, `setTimeout` and `setInterval` | Microsoft.CodeAnalysis.BannedApiAnalyzers, with every reach in the rule's table in `BannedSymbols.txt`, in each project of the contexts in `contexts` | forbidigo in golangci-lint, for `time.Now`, `time.Since`, `time.Sleep`, `time.After` and `time.NewTimer` | Left to the team where no tool fits: the rule asks for code read as code, and a text match flags a reach inside a string |
| A test waits on a fact, never on a duration | ESLint core `no-restricted-syntax` on `setTimeout` in test files | Microsoft.CodeAnalysis.BannedApiAnalyzers, with `Thread.Sleep` and `Task.Delay` banned in test projects, and support files exempt | forbidigo in golangci-lint, on `time.Sleep` in `_test.go` files | Left to the team beyond the sleeps: what a wait waits on is a review's call |

## `words.md`

| Rule | TypeScript | .NET | Go | Starter test |
|---|---|---|---|---|
| No source file uses a word that lost. `banned-words`, `skip-folders` | — | — | — | Each source file, in the whole of its text, holds no entry of the list for the context that claims it, in any letter case, with the words of a name run together by nothing, an underscore, a hyphen or one space |

## `comments.md`

| Rule | TypeScript | .NET | Go | Starter test |
|---|---|---|---|---|
| Doc comments go where the setting says. `doc-comments` | — | — | — | With `false`, no source file holds a doc comment. With `true`, no test file does. A doc comment is what the rule says it is in each language |
| A comment records why | — | — | — | Left to the team: whether a comment says why is judgement, which `/skillworks:comment-sweep` and review make |
