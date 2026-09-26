#
# Fetch origin, and look again when another loop got there first.
#
#   from fetch_origin import fetch_origin
#   fetch_origin(runner, checkout, err, wait)
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
# Waits double between tries, or several loops fetching at once spend every try inside one clash.
#
# `wait` is handed in so a test can record the waits without spending them.
#
# Answers True when it worked, and says nothing. Answers False when it did not, and
# writes what git said to err.

# Enough for a collision with another loop, few enough that this cannot spin.
ATTEMPTS = 5

FIRST_WAIT = 1

# The whole of what a loser of the race is told. Anything else is its own problem.
RACE = ("cannot lock ref", "annot create", "nable to create")


def fetch_origin(runner, checkout, err, wait):
    attempt = 1
    pause = FIRST_WAIT
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
        wait(pause)
        pause *= 2
        attempt += 1
