#!/usr/bin/env bash
#
# Support for the shell tests. A test file sources this, defines case_*
# functions, then calls run_cases.
#
# Every case gets a repository of its own in a temporary directory, so no case
# can see what another one left behind, and none can touch this one.

# A native form, because whether the shell converts one on the way out to uv is not set here.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && { pwd -W 2>/dev/null || pwd; })
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
  # A developer who records resolutions would otherwise have them replayed here.
  git -C "$1" config rerere.enabled false
  # A developer who prefers diff3 would otherwise change what a conflict measures.
  git -C "$1" config merge.conflictStyle merge
}

write_commit() {  # <repo> <file> <text> <message>
  printf '%s\n' "$3" >> "$1/$2"
  git -C "$1" add -A
  git -C "$1" commit --quiet -m "$4"
}

# A remote and a checkout of it, level with each other.
make_repo() {
  TMP=$(mktemp -d)
  # PATH splits on colons, so a drive letter here would be two entries and find neither.
  STUBS="$TMP/stubs"
  # Git reads /tmp as C:/tmp here, not where the shell put it. A drive letter suits both.
  command -v cygpath >/dev/null && TMP=$(cygpath -m "$TMP")
  ORIGIN="$TMP/origin.git"
  WORKTREE="$TMP/work"
  PATH="$REAL_PATH"
  mkdir -p "$STUBS"

  git init --quiet --bare --initial-branch=main "$ORIGIN"
  git init --quiet --initial-branch=main "$WORKTREE"
  configure "$WORKTREE"
  write_commit "$WORKTREE" base.txt "base" "Base"
  git -C "$WORKTREE" remote add origin "$ORIGIN"
  git -C "$WORKTREE" push --quiet origin main
}

# A case that changes more than one file on the other side needs the checkout itself.
other_checkout() {
  local other="$TMP/other"
  rm -rf "$other"
  # A clone checks out before it can be configured, so the setting goes in on the command.
  git clone --quiet -c core.autocrlf=false "$ORIGIN" "$other"
  configure "$other"
  printf '%s' "$other"
}

# A commit somebody else pushed, so only a fetch can find it.
push_from_elsewhere() {  # <file> <text> <message>
  local other
  other=$(other_checkout)
  write_commit "$other" "$1" "$2" "$3"
  git -C "$other" push --quiet origin main
}

advance_origin() {  # <name>
  push_from_elsewhere "$1.txt" "$1" "Somebody else's $1"
}

# --- stubs ------------------------------------------------------------------

# A recorded call is how a test says a session was never started.
stub() {
  printf '#!/bin/sh\necho "%s $*" >> "%s"\n' "$1" "$TMP/calls" > "$STUBS/$1"
  chmod +x "$STUBS/$1"
  PATH="$STUBS:$PATH"
}

# A rename is a keep's last step and the group goes in name order, so jobs before this one are kept.
#
# Real git refuses a ref where a folder of refs sits. A stub on PATH cannot do it: Windows
# reads PATHEXT, so a native program never starts an extensionless shell file.
refuse_keeping() {  # <spec> <job>
  git -C "$WORKTREE" branch "spec-loop/$1/$2-kept-1/blocker" main
}

called() {
  grep -q "^$1 " "$TMP/calls" 2>/dev/null
}

calls() {
  cat "$TMP/calls" 2>/dev/null
}

# --- running ----------------------------------------------------------------

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
