#!/usr/bin/env bash
#
# Make and remove the throwaway worktree one job of a spec loop is built in.
#
#   scripts/ticket-worktree.sh open  <checkout> <spec> <job>
#   scripts/ticket-worktree.sh close <checkout> <spec> <job>
#   scripts/ticket-worktree.sh plan  <checkout> <spec> <job>
#   scripts/ticket-worktree.sh keep  <checkout> <spec>
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
# `plan` prints the path and the branch a job would get, tab separated, and makes neither.
#
# Worktrees are grouped by spec, so `keep` takes the whole group a stopped run left
# behind: each job's uncommitted work is committed, its branch is renamed out of the
# way so the job can be opened again, and the worktree goes.
#
# `keep` prints one line per job, tab separated: the job, the branch it is kept on,
# and `held` if the worktree had uncommitted changes or `clean` if it had none.

main() {
  set -euo pipefail

  say() { printf 'ok    %s\n' "$*" >&2; }
  warn() { printf 'warn  %s\n' "$*" >&2; }
  die() { printf 'FAIL  %s\n' "$*" >&2; exit 1; }

  usage() {
    printf 'usage: scripts/ticket-worktree.sh open|close|plan <checkout> <spec> <job>\n' >&2
    printf '       scripts/ticket-worktree.sh keep <checkout> <spec>\n' >&2
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
    open|close|plan) case "$JOB" in ''|*[!A-Za-z0-9-]*) usage ;; esac ;;
    keep)            [ -z "$JOB" ] || usage ;;
    *)               usage ;;
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

  # The group is the mark a loop is running, so the last job out takes it down.
  drop_group() { rmdir "$GROUP" 2>/dev/null || true; }

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

    drop_group
    say "$JOB left nothing behind"
  }

  plan_job() {
    printf '%s\t%s\n' "$TREE" "$BRANCH"
  }

  # A name no branch holds yet, so a second stopped attempt sits beside the first.
  kept_name() {  # <job>
    local n=1
    while git -C "$CHECKOUT" rev-parse --verify --quiet \
            "refs/heads/spec-loop/$SPEC/$1-kept-$n" >/dev/null; do
      n=$(( n + 1 ))
    done
    printf 'spec-loop/%s/%s-kept-%s' "$SPEC" "$1" "$n"
  }

  keep_group() {
    git -C "$CHECKOUT" worktree prune
    [ -e "$GROUP" ] || return 0

    local tree job branch kept state
    for tree in "$GROUP"/*; do
      [ -d "$tree" ] || continue
      job=$(basename "$tree")

      # A stray folder answers git about the checkout, so the work committed would be the developer's own.
      [ "$(git -C "$tree" rev-parse --show-toplevel 2>/dev/null)" = "$tree" ] \
        || { warn "$tree is no worktree of its own, so it was left where it is."; continue; }

      branch=$(git -C "$tree" rev-parse --abbrev-ref HEAD)
      # Work on no branch would go with the worktree, and nothing here discards work.
      [ "$branch" != HEAD ] \
        || { warn "$tree is on no branch, so it was left where it is."; continue; }

      state=clean
      if [ -n "$(git -C "$tree" status --porcelain)" ]; then
        git -C "$tree" add -A \
          || die "git would not stage what is in $tree, so nothing was removed."

        # A line ending alone makes a file look changed, and staging it then leaves nothing to
        # commit. Committing that refuses, and the restart this exists to allow would stop here.
        if ! git -C "$tree" diff --cached --quiet; then
          state=held
          git -C "$tree" commit --quiet \
            -m "What a stopped attempt at $job had not committed" >&2 \
            || die "git would not commit what is in $tree, so nothing was removed."
        fi
      fi

      git -C "$CHECKOUT" worktree remove --force "$tree" >&2 \
        || die "git would not remove the worktree at $tree. Branch $branch holds its work."
      kept=$(kept_name "$job")
      git -C "$CHECKOUT" branch --quiet -m "$branch" "$kept" \
        || die "git would not rename branch $branch, which still holds the work of $job."

      printf '%s\t%s\t%s\n' "$job" "$kept" "$state"
    done

    drop_group
  }

  case "$COMMAND" in
    open)  open_job ;;
    close) close_job ;;
    plan)  plan_job ;;
    keep)  keep_group ;;
  esac
}

# Bash reads a script while it runs it, so an edit mid-run changes what runs next.
main "$@"; exit
