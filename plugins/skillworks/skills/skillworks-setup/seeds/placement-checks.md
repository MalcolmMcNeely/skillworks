# The placement checks

`.claude/rules/file-placement.md` holds the rules the code was written under. Read them there, and judge placement and direction against what they say. Read the context map beside it too, where the repo has one, because a rule reaches only the code the map gives it.

Cite a breach by the name of the check that catches it. Where a rule has no check behind it, cite the rule by its number. List each check here as the repo gains one:

| Check | The rule it runs |
|---|---|

The table is an index from a breach back to a rule, and the rules themselves stay in the one file.

## The checks that prove placement

The Suite file, [`suite.json`](suite.json), names every check the repo runs. A review runs only the checks listed here, and no other check in the Suite. List each one that proves placement, as it is written in the Suite file:

| Suite check | What it runs |
|---|---|

While this table is empty, no check proves placement, and a review judges placement by reading the rules alone.

## The two bends

Holding the author and the reviewer to one document is the point of the Architecture axis, so two items of the arrangement baseline in [`arrangement-baseline.md`](arrangement-baseline.md) bend wherever the repo has written the rule down:

- **A shared folder with a written door is not grab-bag growth.** The baseline item is about a folder nobody decided on. Judge against the door the repo wrote, not against the name.
- **Duplication across a boundary can be correct.** Where the repo says two modules may hold one name, the merge is the defect, not the duplication.
