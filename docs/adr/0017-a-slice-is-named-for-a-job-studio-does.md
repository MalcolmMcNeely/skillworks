# A Slice is named for a job Studio does

The Watch page's code sits in four folders of `Skillworks.Core`, one of `Skillworks.Studio.Api` and
one of the front end, and the front-end one is called `skills`, which is not what the page is called.
An agent asked to change one page therefore opens most of the repository, and that cost grows with
every page. So the first folder under a code root is now a **Slice**, named for a job Studio does, and
`CONTEXT.md` already lists the jobs: Watch, Author, Test and Publish, with Sessions beside them. Two
are built, so `Watch` and `Sessions` are the Slices, and the other three are one line each when they
land.

A Slice never reads another Slice. Two Slices may hold a type with the same name, and merging them is
the defect, not the duplication: `Core/Activations/Activation.cs` and
`Core/Sessions/Activations/Activation.cs` are two different records today and were right to be.

## Considered options

**Name Slices for concepts Studio holds**, as the tree does now: Activations, Skills, Spend,
Provenance, Sessions. Rejected. Little would move, but the Watch page would stay spread over four
folders and the tree would say what Studio knows rather than what it does.

**Make Health, Telemetry, Catalogue and Home Slices too.** Rejected. The glossary names Studio's jobs
and none of these is among them: Health is how a **part** of Studio is doing, Telemetry is a switch
two pages show, Home is the page that leads to the jobs. Worse, Watch already draws the Health lamps
and the Telemetry switch, so the rule that a Slice never reads another Slice would need an exception
on its first day, and an exception on the first day is an exception forever.

## Consequences

Level one reads `Watch`, `Sessions` and `Shared`. Thin, and true: Studio does two jobs today. Roughly
120 files sit in the two Slices and 105 in `Shared`, because Studio is a reader and most of its code
is the reading machinery. That ratio moves as the other three jobs land, and not before.

The rule that a Slice never reads another Slice holds code files only. A test may read any Slice,
because a test's job is to check a seam and a seam test has to see both sides: the alphabet test reads
six folders by hand on purpose, and the API tests drive the whole app through one host. A list of
exempt tests would be a second place the truth lives, and it would go stale.

`Skillworks.Core/Registration` names every Slice, so it cannot survive. Each Slice registers itself in
a file at its own root and `Program.cs` calls each one, which removes the single file coupled to
everything.
