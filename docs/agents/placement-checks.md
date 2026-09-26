# The placement checks

`.claude/rules/file-placement.md` holds the eight Slice rules the code was written under. Read them there, and judge placement and direction against what they say. Read the context map beside it too, because a rule reaches only the code the map gives it, and a path two contexts claim breaches `contexts`.

Cite a breach by the name of the check that catches it:

| Check | The rule it runs |
|---|---|
| `slice-folders` | 1, a Slice comes first |
| `concern-folders` | 2, a Concern comes beneath, in the front end |
| `slices-stay-apart` | 3, a Slice never reads another Slice |
| `shared-stays-below` | 4, `Shared` never reads a Slice |
| `shared-names-a-word` | 5, `Shared` has one door |
| `slice-names-match` | 6, a Slice keeps its name everywhere |

Rules 7 and 8 have no check behind them, and nor does the exemption that lets a test read a Slice. The front end is held by `src/Skillworks.Studio.Web/.dependency-cruiser.cjs`, which names its own breaches, so quote whichever name the run printed. The table is an index from a breach back to a rule, and the rules themselves stay in the one file.

## The checks that prove placement

A review runs these commands, each in its folder from the repo root, and nothing else. Where a row names a command to run first, run it first in the same folder, unless the path it names is there in that folder:

| Command | Folder | Run first |
|---|---|---|
| `dotnet test tests/Skillworks.Architecture.Tests` | `.` | |
| `npm run lint` | `src/Skillworks.Studio.Web` | `npm ci`, unless `node_modules` is there |

The first runs `Skillworks.Architecture` over the whole tree. The second runs dependency-cruiser over the front end. The rest of the Suite proves nothing about placement, and the API tests alone take six minutes.

## The two bends

Holding the author and the reviewer to one document is the point of the Architecture axis, so two items of the arrangement baseline in [`arrangement-baseline.md`](arrangement-baseline.md) bend wherever the repo has written the rule down:

- **A shared folder with a written door is not grab-bag growth.** The baseline item is about a folder nobody decided on. Judge against the door the repo wrote, not against the name.
- **Duplication across a boundary can be correct.** Where the repo says two modules may hold one name, the merge is the defect, not the duplication.
