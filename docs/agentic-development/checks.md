# Checks

The [README](../../README.md) lists the commands. This page says how the loop runs them, and what
the script tests do.

## The Suite file

`docs/agents/suite.json` is the Suite file. It lists the checks, with the folder each one runs in and
what must be ready first. The loop runs the checks it names and nothing else, so a check added to the
README goes in that file too. Every readiness command runs first, one by one. Then the checks run
together, and a red check lets the others finish. The output keeps the order of the file, each
check's output whole, whatever finished first. A check with `when` names the paths that wake it, each
a file or a folder from the repo root, and runs only when the ticket's own change touches one. A check
that did not run says so in one line of the output. Its `runs` is 2, because the container-backed
Span tests flake here, so the loop runs a red Suite a second time before it believes it.

## The script tests

The loop's scripts live in the Plugin, at `plugins/skillworks/scripts/`, and their tests sit at the
same path under `tests/`. The script tests build a throwaway repository in a temporary directory and
touch nothing else. The scripts are Python, so `uv` has to be on PATH for their tests to run. pytest
is asked for on the command line, because the scripts carry no project file. The hook scripts are
node, and their tests sit beside the script tests and use the test runner built into node, so they
add no dependency. node expands the quoted pattern itself.

The script tests come in two sets, told apart by one flag on the same path. The command in the
README runs the fast set, which answers for `gh` and `claude` through the Runner, so it needs neither
installed and starts no model session. It is the set a landing runs, so landing is never gated on a
login.

The other set starts the real `gh` and the real `claude`, far enough to prove each one accepts the
argument lines the driver builds for it and no further. It also starts `claude` with the Plugin, to
prove the Plugin forces its output style and resolves a `skillworks:` skill. That session asks for a
model the API does not offer, so no model answers. One more session, on Haiku, makes a commit in a
throwaway repository, to prove the Plugin's hook names the Session in it. That is the one model
session the set starts. It needs both programs on PATH. It changes no issue, and it takes under a
minute:

```
uv run --with pytest pytest tests/plugins/skillworks/scripts --real-binaries
```

## The ten-minute wait

A session waits ten minutes on a command before it gives up, rather than the two minutes it would
otherwise. `.claude/settings.json` sets that. The script suite took 184, 299, 321 and 413 seconds
across four runs of the same tests on this machine, and the spread is machine load, so two minutes
loses the result and a session has to run the suite in the background and poll it instead. The wait
is a ceiling and never a delay, so a run that takes three minutes still answers in three.

This does not reach the loop itself, which runs for hours and still has to be started in the
background.
