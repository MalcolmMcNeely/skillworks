# File placement

The YAML block at the end holds the settings these rules name. When code breaks a rule, move or
split the code until it fits. The settings change only when the developer asks.

## One shape

C# and TypeScript share one shape: feature folders first, concern folders beneath.

- A **feature** folder is named for the part of Studio its code serves. A type goes in the feature it
  belongs to.
- A **concern** folder groups types that play one role inside a feature. `name-map` names the roles
  that always get one. A feature that grows may add others.
- In the front end, the layer folders `api`, `components`, `lib` and `routes` are the concerns, and
  `src/Skillworks.Studio.Web/.dependency-cruiser.cjs` holds the boundaries between them.
- Code that serves no feature goes in a folder named for what it does. Every folder name says what
  its code serves or does, so the names in `banned-folder-names` are never used, in any letter case.
- Folders in `skip-folders` hold code nobody writes by hand. These rules skip them.

## Files

A file's **subject** is its name up to the first dot.

- A C# file holds one top-level type, named as the subject. A private nested type or a `file` type
  can stay with the type it serves. Any other nested type gets its own file. A `Program.cs` with
  top-level statements is the one file with no type.
- A large type splits across aspect files: `BlobRepository.Async.cs` holds `partial BlobRepository`.
- A C# namespace is the project name, then the folder path: a file in
  `Skillworks.Core/<Feature>/<Concern>/` is in `Skillworks.Core.<Feature>.<Concern>`.

## Tests

A file whose name matches a pattern in `test-files` is a test. Its subject drops the test marker and
any aspect, so `BlobRepository.Lease.Tests.cs` tests `BlobRepository`. It holds `partial
BlobRepositoryTests`, and the other aspect files of that test class hold the other parts.

- Test folders mirror source folders. A C# test in project `X.Tests` sits at the same relative path
  as its subject's file in project `X`.
- A front-end test sits beside its module.
- Hosts, fakes and the records a test reads a response into are support files, not tests. Put them
  beside the tests that use them, or in a folder named for what they do. The size limit, the name map
  and the banned names apply to them too.

## Folder size

A folder holds at most `max-types-per-folder` types. The count is the number of different subjects
among the files in `source-files` that sit directly in the folder.

- A type, its aspect files and the test beside it share a subject, so they take one place.
- A test with no module beside it counts as one.
- Subfolders count for nothing, so splitting a full folder into feature or concern folders always
  makes room.

## Name map

Each pattern in `name-map` is a name with `*` at the start or the end, such as `*Store` or `Store*`.
It matches the subject, and letter case counts.

- A subject that matches one pattern sits in that pattern's folder.
- A subject that matches several patterns sits in the folder of any one of them.
- A subject that matches none goes where its feature puts it.

```yaml
max-types-per-folder: 10
source-files:
  - .cs
  - .ts
  - .tsx
test-files:
  - "*.Tests.cs"
  - "*.test.ts"
skip-folders:
  - Migrations
  - bin
  - obj
  - node_modules
banned-folder-names:
  - utils
  - helpers
  - common
  - shared
  - misc
name-map:
  "*Store": Stores
```
