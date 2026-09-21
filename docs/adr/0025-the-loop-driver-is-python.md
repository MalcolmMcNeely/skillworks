# The loop driver is Python

Every process Git Bash starts on this machine costs about 2.9 seconds. Native Python and PowerShell
start the same program in 59 milliseconds. `tests/scripts/spec-loop.test.sh` runs 28 cases in 53
minutes, and almost all of that is the tax rather than the work: the cheapest case in the file
asserts on a dry run and still costs 43 seconds. A build session cannot run the suite inside the 600
second cap the Bash tool puts on a command, so it loses the result and polls for it instead.

The same move answers a second question. `scripts/spec-loop.sh` is 468 lines of bash carrying
nineteen lines of JavaScript inside a string, and `docs/research/harness/driver-language.md` had
already picked Python over Node for it on three other grounds: Python starts `.cmd` files on Windows,
it can end a `claude` turn rather than only kill it, and it reaches Job Objects from stdlib. Speed
was not among those three, and it is the largest of the four.

So `scripts/` moves to Python, bottom up, one program and its test at a time: `ticket-worktree`,
then `land-ticket`, then `spec-loop`. `fetch-origin` is a library the other three read, so it moves
with the first of them, and its bash copy lives until the last one goes. `skillworks-preflight.sh`
stays bash for good, because it exists to tell a new machine whether it can run the loop, and it
cannot be written in the language it is checking for.

## Considered options

**Run the bash suite under WSL or in a container.** Warm WSL starts git in 14.5 milliseconds, faster
than native Windows, and the change is close to nothing. It was rejected because the scripts would
then be tested on Linux bash and run on Git Bash. The `MSYS_NO_PATHCONV` workarounds in them exist
only on Windows, and a Linux test would never reach one. It also leaves the driver itself slow, since
the real loop pays the same tax on every `git`, `gh` and `claude` it starts.

**Cut the number of spawns instead.** Building one template repository and copying it per case would
take `make_repo` off the critical path. It was rejected as too small. The cheapest case in the file
costs 43 seconds with no repository work worth the name, so the tax is spread through the suite
rather than gathered in the fixture.

**Node rather than Python.** `.mjs` is already in `source-files`, so Node is cheaper to adopt, and
that is the argument against it. Node half fits the rules today, and half fitting is what keeps a gap
invisible. Node also cannot start `npm.cmd` or `aspire.cmd` on Windows, and `land-ticket.sh` runs
four npm commands.

## Consequences

ADR 0021 said Loop's code is shell and node. It is shell and Python. `node` leaves the loop
altogether: it was there to read JSON, and `json` is stdlib.

A test can no longer fake a program by writing a shell file onto `PATH`, because Windows reads
`PATHEXT` and pays no attention to a shebang. Every program the driver reaches goes through a
**Runner**, which is injected the way the Clock is. A separate, small set of tests starts the real
binaries, so something still proves that `gh` takes the arguments the driver builds for it.

`.py` joins `source-files`, and `__pycache__`, `.venv`, `venv` and `site-packages` join
`skip-folders` in the same commit. `SourceTree.cs` walks the tree rather than asking git, so a
virtual environment arriving before its skip entry would flood the check with folders named `utils`
and `helpers`.

`test-files` gains `*_test.py` rather than `*.test.py`. `foo.test` is not a name Python can import,
and pytest could not collect the file.

`DocComments.cs` gains a docstring detector. Python writes docstrings by reflex, so
`doc-comments: false` would be broken by the first file to land carrying one.

Determinism stays out of reach for Python, as it already is for bash. `MachineClock.cs:62` filters on
`.cs` before it reads the context list, and `loop` is not among the contexts that rule judges anyway.
Nothing gets worse. Closing it is a job of its own.
