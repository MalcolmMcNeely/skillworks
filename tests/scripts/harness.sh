#!/usr/bin/env bash
#
# Support for the shell tests. A test file sources this, defines case_*
# functions, then calls run_cases.
#
# Every case gets a repository of its own in a temporary directory, so no case
# can see what another one left behind, and none can touch this one.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
REAL_PATH="$PATH"

CASES_RUN=0
CASES_FAILED=0
CASE_FAILED=0
CASE_NOTES=""

fail() {
  CASE_FAILED=1
  CASE_NOTES="$CASE_NOTES      $*"$'\n'
}

# --- assertions -------------------------------------------------------------

assert_status() {  # <wanted> <got>
  [ "$1" = "$2" ] || fail "exit status: wanted $1, got $2"
}

assert_eq() {  # <what> <wanted> <got>
  [ "$2" = "$3" ] || fail "$1: wanted '$2', got '$3'"
}

# Newlines become bars, so a multi-line message stays on one line of the report.
assert_says() {  # <wanted> <said>
  case "$2" in
    *"$1"*) ;;
    *) fail "message: wanted '$1', got: $(printf '%s' "$2" | tr '\n' '|')" ;;
  esac
}

# --- a repository to act on -------------------------------------------------

# Enough settings that a commit works and nothing warns, on any machine.
configure() {
  git -C "$1" config user.name "Test"
  git -C "$1" config user.email "test@example.invalid"
  git -C "$1" config commit.gpgsign false
  git -C "$1" config core.autocrlf false
}

write_commit() {  # <repo> <file> <text> <message>
  printf '%s\n' "$3" >> "$1/$2"
  git -C "$1" add -A
  git -C "$1" commit --quiet -m "$4"
}

# A remote and a checkout of it, level with each other.
make_repo() {
  TMP=$(mktemp -d)
  # Git reads /tmp as C:/tmp here, not where the shell put it. A drive letter suits both.
  command -v cygpath >/dev/null && TMP=$(cygpath -m "$TMP")
  ORIGIN="$TMP/origin.git"
  WORKTREE="$TMP/work"
  STUBS="$TMP/stubs"
  PATH="$REAL_PATH"
  mkdir -p "$STUBS"

  git init --quiet --bare --initial-branch=main "$ORIGIN"
  git init --quiet --initial-branch=main "$WORKTREE"
  configure "$WORKTREE"
  write_commit "$WORKTREE" base.txt "base" "Base"
  git -C "$WORKTREE" remote add origin "$ORIGIN"
  git -C "$WORKTREE" push --quiet origin main
}

commit_for_ticket() {
  write_commit "$WORKTREE" work.txt "work" "$(printf 'Do the work\n\nTicket: #%s' "$1")"
}

commit_naming_nothing() {
  write_commit "$WORKTREE" work.txt "work" "Do the work"
}

# Counting the tries is how a bounded retry is measured and not guessed at.
refuse_pushes() {
  printf '#!/bin/sh\necho try >> "%s"\nexit 1\n' "$TMP/push-tries" > "$ORIGIN/hooks/pre-receive"
  chmod +x "$ORIGIN/hooks/pre-receive"
}

push_tries() {
  if [ -f "$TMP/push-tries" ]; then wc -l < "$TMP/push-tries" | tr -d ' '; else printf '0'; fi
}

# --- stubs ------------------------------------------------------------------

# A recorded call is how a test says a session was never started.
stub() {
  printf '#!/bin/sh\necho "%s $*" >> "%s"\n' "$1" "$TMP/calls" > "$STUBS/$1"
  chmod +x "$STUBS/$1"
  PATH="$STUBS:$PATH"
}

called() {
  grep -q "^$1 " "$TMP/calls" 2>/dev/null
}

# --- running ----------------------------------------------------------------

run_script() {  # <script> <args...>
  local script="$1"
  shift
  OUTPUT=$(bash "$ROOT/$script" "$@" 2>&1)
  STATUS=$?
}

run_cases() {
  local name
  for name in $(declare -F | awk '{ print $3 }' | grep '^case_' | sort); do
    CASE_FAILED=0
    CASE_NOTES=""
    make_repo
    "$name"
    rm -rf "$TMP" 2>/dev/null || true
    CASES_RUN=$(( CASES_RUN + 1 ))
    if [ "$CASE_FAILED" = 1 ]; then
      CASES_FAILED=$(( CASES_FAILED + 1 ))
      printf 'FAIL  %s\n%s' "$name" "$CASE_NOTES"
    else
      printf 'ok    %s\n' "$name"
    fi
  done
  printf '      %s run, %s failed\n' "$CASES_RUN" "$CASES_FAILED"
  [ "$CASES_FAILED" -eq 0 ]
}
