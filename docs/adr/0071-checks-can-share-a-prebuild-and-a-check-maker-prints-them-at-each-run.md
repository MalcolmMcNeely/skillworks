# Checks can share a Prebuild, and a Check maker prints them at each run

A .NET repo with about 24 test projects had one Suite check over the whole solution, at 16 to 21
minutes, so any change ran every test project. Splitting it into one check per project was not safe.
The checks run together, each `dotnet test` builds its own project references, and checks that share
a library built it at once into the same `bin` and `obj` folders, which read as reds and Flakes.
[ADR 0034](0034-the-suite-runs-its-checks-together-and-a-check-can-wait-for-its-paths.md) told such a
team to join its checks into one, and that one check was the cost.

Three things change.

**Checks can share a Prebuild.** A check may name a Prebuild: one command the Suite runs once,
before the checks that name it, which then run together without building. A Prebuild runs only when
one of its checks has to run, and a Prebuild that fails is red for every check that names it, because
code that does not compile is the ticket's to mend. A check that names an `image` cannot name a
Prebuild, because it runs on a copy of the files, apart from what the Prebuild built.

**A Check maker prints checks at each Suite run.** The Suite file may name a command that prints
checks, and the Suite runs them as if the file named them. The keys beside it, such as `ready` and
`ignores`, reach every check it prints. It reads the repo as it is, so a new test project gets its
check, and a new reference changes a check's inputs, with no edit to the Suite file. A Check maker
that fails is red, for the same reason as a Prebuild.

**The Plugin ships a .NET Check maker and a .NET Rerun.** The Check maker reads a solution and prints
one check per test project, a Prebuild that builds the solution, and a Rerun for each check that runs
only the tests that went red. Each check ignores the project folders its test project does not reach,
so a missed file costs a run and never lets a red land. A team leaves projects out with patterns,
and never by marking its own project files.

## Considered options

**Checks in a set run one after another.** Safe, with no new command. Rejected: tests are the slow
part, and this makes a set take the sum of its test times.

**A helper writes the checks into the Suite file.** The file stays the whole list, easy to read.
Rejected: a new project leaves the file out of step until someone runs the helper, and a check to
catch that is one more thing to keep. A Check maker cannot be out of step.

**A check names the paths it reads, from the project graph.** Rejected by
[ADR 0039](0039-the-suite-keeps-proofs-and-a-check-names-what-it-ignores.md): a path the graph does not
show, such as test data or a build file at the root, would let a check sleep and a red change land.

**Each team writes its own Check maker.** Keeps the Plugin free of .NET. Rejected: the graph rules are
the same in every .NET repo, so each team would write the same script again, untested.

**A Prebuild that builds only the projects whose checks will run.** Rejected: the Suite would have to
hand check facts to a command, a new contract, to save a build that took 4% of the time.

**A Prebuild that runs in a check's image.** Rejected for now: no team needs a .NET runner in Linux.
Turning the pair down today closes no door, because allowing it later breaks no Suite file.

## Consequences

This replaces the line in ADR 0034 that a team whose checks collide joins them into one check.
Running the checks together still holds.

The Plugin now holds facts about one toolchain. [ADR 0030](0030-steering-is-the-repos-and-machinery-is-the-plugins.md)
keeps facts about one repo out of it, and these are not: the Suite reads only the printed checks and
knows nothing of .NET. A team with another toolchain writes its own Check maker in the same shape.

The Suite file no longer lists every check. The Suite output does, so a reader who wants the list
reads a run.
