#!/usr/bin/env bash
#
# Make and remove the throwaway worktree one job of a spec loop is built in.
#
#   scripts/ticket-worktree.sh open  <checkout> <spec> <job>
#   scripts/ticket-worktree.sh close <checkout> <spec> <job>
#   scripts/ticket-worktree.sh check <checkout> <spec>
#
# A job is one ticket, or the drift check at the end. It gets a worktree and a
# branch of its own, cut from the newest `origin/main`, and both go when it
# passes. The checkout is only ever what they are cut from, so the developer
# keeps it, on any branch, with any edits in it, for the whole run.
#
# A branch here is not the branch this repo says it does without. Git will not
# check `main` out twice, so a worktree needs one, and it never leaves the
# machine: the job pushes to `main` and the branch goes with the worktree.
#
# `open` prints the worktree's path on stdout and nothing else, so the driver
# can read it. Everything else it says goes to stderr.
#
# Worktrees are grouped by spec, so `check` turns down a spec whose group is
# already there: another loop is working on it, or a failed one left it behind.

main() {
  set -euo pipefail

  say() { printf 'ok    %s\n' "$*" >&2; }
  die() { printf 'FAIL  %s\n' "$*" >&2; exit 1; }

  usage() {
    printf 'usage: scripts/ticket-worktree.sh open|close <checkout> <spec> <job>\n' >&2
    printf '       scripts/ticket-worktree.sh check <checkout> <spec>\n' >&2
    exit 64
  }

  # Named in full, because the way out it offers is read after a cd somewhere else.
  SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

  COMMAND="${1:-}"
  CHECKOUT="${2:-}"
  SPEC="${3:-}"
  JOB="${4:-}"

  [ -n "$CHECKOUT" ] || usage
  case "$SPEC" in ''|*[!0-9]*) usage ;; esac
  # A job names a folder and a branch, so anything else escapes the group or breaks the ref.
  case "$COMMAND" in
    open|close) case "$JOB" in ''|*[!A-Za-z0-9-]*) usage ;; esac ;;
    check)      [ -z "$JOB" ] || usage ;;
    *)          usage ;;
  esac

  git -C "$CHECKOUT" rev-parse --git-dir >/dev/null 2>&1 \
    || die "$CHECKOUT is not a git worktree. Nothing was made or removed."

  CHECKOUT=$(git -C "$CHECKOUT" rev-parse --show-toplevel)
  GROUP="$CHECKOUT/.claude/worktrees/spec-$SPEC"
  TREE="$GROUP/$JOB"
  BRANCH="spec-loop/$SPEC/$JOB"

  branch_exists() { git -C "$CHECKOUT" rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; }

  removal() { printf "bash '%s' close '%s' %s %s" "$SELF" "$CHECKOUT" "$SPEC" "$1"; }

  open_job() {
    [ ! -e "$TREE" ] || die "$TREE is already there. Remove it with: $(removal "$JOB")"
    ! branch_exists || die "branch $BRANCH is already there. Remove it with: $(removal "$JOB")"

    git -C "$CHECKOUT" fetch --quiet origin \
      || die "could not fetch from origin, so nothing could be cut from it."
    git -C "$CHECKOUT" rev-parse --verify --quiet origin/main >/dev/null \
      || die "origin has no main branch to cut a worktree from."

    mkdir -p "$GROUP"
    git -C "$CHECKOUT" worktree add --quiet -b "$BRANCH" "$TREE" origin/main >&2 \
      || die "git would not make a worktree at $TREE."
    printf '%s\n' "$TREE"
  }

  close_job() {
    # Git forgets a worktree whose folder somebody deleted by hand.
    git -C "$CHECKOUT" worktree prune

    # Ignored build output holds the worktree open, and the commit is already on the remote.
    if [ -e "$TREE" ]; then
      git -C "$CHECKOUT" worktree remove --force "$TREE" >&2 \
        || die "git would not remove the worktree at $TREE."
    fi
    if branch_exists; then
      git -C "$CHECKOUT" branch --quiet -D "$BRANCH" >&2 \
        || die "git would not delete branch $BRANCH."
    fi

    # The group is the mark a loop is running, so the last job out takes it down.
    rmdir "$GROUP" 2>/dev/null || true
    say "$JOB left nothing behind"
  }

  check_group() {
    git -C "$CHECKOUT" worktree prune
    [ -e "$GROUP" ] || return 0

    local reason job found=0
    reason=$(printf 'spec #%s already has a worktree group at %s. Another loop is working on this spec, or a failed one left it behind. Nothing was started.' "$SPEC" "$GROUP")
    for job in "$GROUP"/*; do
      [ -e "$job" ] || continue
      found=1
      job=$(basename "$job")
      reason=$(printf "%s\n      %s\n        carry on in it: cd '%s/%s'\n        throw it away:  %s" \
        "$reason" "$job" "$GROUP" "$job" "$(removal "$job")")
    done
    # An empty group holds no job to carry on in, so the folder is the only way out.
    [ "$found" = 1 ] || reason=$(printf "%s\n        throw it away:  rmdir '%s'" "$reason" "$GROUP")
    die "$reason"
  }

  case "$COMMAND" in
    open)  open_job ;;
    close) close_job ;;
    check) check_group ;;
  esac
}

# Bash reads a script while it runs it, so an edit mid-run changes what runs next.
main "$@"; exit
