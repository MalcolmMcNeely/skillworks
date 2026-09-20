#!/usr/bin/env bash
#
# Fetch origin, and look again when another loop got there first.
#
#   . "$(dirname "$0")/fetch-origin.sh"
#   fetch_origin                 # in the checkout the caller is standing in
#   fetch_origin -C <checkout>   # in another one
#
# A fetch is not a read. It writes refs/remotes/origin/main, recording where the
# remote's main was. Two loops sharing one .git each read that ref, download,
# then write it back, and the second write finds a value it never read. Git
# refuses rather than stamping over what the first one landed.
#
# The refusal says the ref moved, not that the fetch cannot be done, so the
# answer is to read it again. On the second try the other loop has finished and
# the objects are already here, so the try is cheap and almost always the last.
#
# Every other failure is real and goes straight back, so an origin that cannot be
# reached still fails on the first try rather than after five.
#
# Nothing waits between tries. The lock is gone the moment the loop that held it
# finished, which is before this one was ever told no, and the count is bounded,
# so there is no spin to pace.
#
# Prints nothing when it works. Says what git said, on stderr, when it does not.

# Enough for a collision with another loop, few enough that this cannot spin.
FETCH_ATTEMPTS=5

fetch_origin() {  # <git args...>
  local attempt=1 said
  while :; do
    said=$(git "$@" fetch --quiet origin 2>&1) && return 0

    # The whole of what a loser of the race is told. Anything else is its own problem.
    case "$said" in
      *"cannot lock ref"*|*"annot create"*|*"nable to create"*) ;;
      *) printf '%s\n' "$said" >&2; return 1 ;;
    esac

    if [ "$attempt" -ge "$FETCH_ATTEMPTS" ]; then
      printf '%s\n' "$said" >&2
      return 1
    fi
    attempt=$(( attempt + 1 ))
  done
}
