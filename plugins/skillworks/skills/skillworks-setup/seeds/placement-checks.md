# The placement checks

`.claude/rules/file-placement.md` holds the rules the code was written under. Read them there, and judge placement and direction against what they say. Read the context map beside it too, where the repo has one, because a rule reaches only the code the map gives it.

Cite a breach by the name of the check that catches it. Where a rule has no check behind it, cite the rule by its number. List each check here as the repo gains one:

| Check | The rule it runs |
|---|---|

The table is an index from a breach back to a rule, and the rules themselves stay in the one file.

## The checks that prove placement

A review runs the commands listed here, each in its folder from the repo root, and nothing else. Where a row names a command to run first, run it first in the same folder, unless the path it names is there in that folder.

List the narrowest commands that prove placement, and leave out the slow ones that prove something else. Write one row per command, and put the command and the folder in backticks. A front end's boundary lint, for example, is the command `make lint`, the folder `web`, and run first `make install`, unless `deps` is there.

| Command | Folder | Run first |
|---|---|---|

While this table is empty, no command proves placement, and a review judges placement by reading the rules alone.

## The two bends

Holding the author and the reviewer to one document is the point of the Architecture axis, so two items of the arrangement baseline in [`arrangement-baseline.md`](arrangement-baseline.md) bend wherever the repo has written the rule down:

- **A shared folder with a written door is not grab-bag growth.** The baseline item is about a folder nobody decided on. Judge against the door the repo wrote, not against the name.
- **Duplication across a boundary can be correct.** Where the repo says two modules may hold one name, the merge is the defect, not the duplication.
