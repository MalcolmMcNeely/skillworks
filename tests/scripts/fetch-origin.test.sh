#!/usr/bin/env bash
#
# The fetch that looks again, read against a throwaway repository.

. "$(dirname "${BASH_SOURCE[0]}")/harness.sh"

SCRIPT=scripts/fetch-origin.sh

# What git says to the loop that lost the race for the ref.
REFUSED="error: cannot lock ref 'refs/remotes/origin/main': is at 1b1e78e but expected 972ef6b"

# A git that turns down its first <n> fetches and is the real git for everything
# else. Counting the tries is how a bounded retry is measured and not guessed at.
refuse_fetches() {  # <n> <what git says>
  local real
  real=$(command -v git)
  {
    printf '#!/bin/sh\n'
    printf 'for a in "$@"; do\n'
    printf '  [ "$a" = fetch ] || continue\n'
    printf '  echo try >> "%s"\n' "$TMP/fetch-tries"
    printf '  if [ "$(wc -l < "%s")" -le %s ]; then\n' "$TMP/fetch-tries" "$1"
    printf '    echo "%s" >&2\n' "$2"
    printf '    exit 1\n'
    printf '  fi\n'
    printf '  break\n'
    printf 'done\n'
    printf 'exec "%s" "$@"\n' "$real"
  } > "$STUBS/git"
  chmod +x "$STUBS/git"
  PATH="$STUBS:$PATH"
}

fetch_tries() {
  if [ -f "$TMP/fetch-tries" ]; then wc -l < "$TMP/fetch-tries" | tr -d ' '; else printf '0'; fi
}

# Sourced rather than run, because what is being read is a function.
run_fetch() {  # <args...>
  OUTPUT=$( . "$ROOT/$SCRIPT"; fetch_origin "$@" 2>&1 )
  STATUS=$?
}

case_a_fetch_that_works_is_asked_once() {
  advance_origin one
  refuse_fetches 0 "$REFUSED"

  run_fetch -C "$WORKTREE"

  assert_status 0 "$STATUS"
  assert_eq "tries" 1 "$(fetch_tries)"
}

case_a_fetch_that_works_says_nothing() {
  run_fetch -C "$WORKTREE"

  assert_status 0 "$STATUS"
  assert_eq "output" "" "$OUTPUT"
}

case_a_refused_ref_is_looked_at_again() {
  advance_origin two
  refuse_fetches 2 "$REFUSED"

  run_fetch -C "$WORKTREE"

  assert_status 0 "$STATUS"
  assert_eq "tries" 3 "$(fetch_tries)"
}

case_a_refused_ref_still_brings_the_commit_down() {
  advance_origin three
  refuse_fetches 1 "$REFUSED"

  run_fetch -C "$WORKTREE"

  assert_status 0 "$STATUS"
  assert_eq "origin/main" \
    "$(git -C "$WORKTREE" rev-parse origin/main)" \
    "$(git -C "$WORKTREE" rev-parse FETCH_HEAD)"
}

case_a_ref_that_never_frees_up_stops() {
  refuse_fetches 99 "$REFUSED"

  run_fetch -C "$WORKTREE"

  assert_status 1 "$STATUS"
  assert_eq "tries" 5 "$(fetch_tries)"
  assert_says "cannot lock ref" "$OUTPUT"
}

case_an_origin_that_cannot_be_reached_is_asked_once() {
  refuse_fetches 99 "fatal: could not read from remote repository"

  run_fetch -C "$WORKTREE"

  assert_status 1 "$STATUS"
  assert_eq "tries" 1 "$(fetch_tries)"
  assert_says "could not read from remote repository" "$OUTPUT"
}

run_cases
