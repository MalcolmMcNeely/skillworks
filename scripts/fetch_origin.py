#
# Fetch origin, and look again when another loop got there first.
#
#   from fetch_origin import fetch_origin
#   fetch_origin(runner, checkout, err)
#
# A fetch is not a read. It writes refs/remotes/origin/main, recording where the
# remote's main was. Two loops sharing one .git each read that ref, download, then
# write it back, and the second write finds a value it never read. Git refuses
# rather than stamping over what the first one landed.
#
# The refusal says the ref moved, not that the fetch cannot be done, so the answer
# is to read it again. On the second try the other loop has finished and the objects
# are already here, so the try is cheap and almost always the last.
#
# Every other failure is real and goes straight back, so an origin that cannot be
# reached still fails on the first try rather than after five.
#
# Nothing waits between tries. The lock is gone the moment the loop that held it
# finished, which is before this one was ever told no, and the count is bounded, so
# there is no spin to pace.
#
# Answers True when it worked, and says nothing. Answers False when it did not, and
# writes what git said to err.

# Enough for a collision with another loop, few enough that this cannot spin.
ATTEMPTS = 5

# The whole of what a loser of the race is told. Anything else is its own problem.
RACE = ("cannot lock ref", "annot create", "nable to create")


def fetch_origin(runner, checkout, err):
    attempt = 1
    while True:
        ran = runner.run(["git", "-C", str(checkout), "fetch", "--quiet", "origin"])
        if ran.status == 0:
            return True

        said = (ran.out + ran.err).rstrip("\n")
        if not any(mark in said for mark in RACE):
            err.write(said + "\n")
            return False

        if attempt >= ATTEMPTS:
            err.write(said + "\n")
            return False
        attempt += 1
