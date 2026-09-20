#!/usr/bin/env bash
#
# Land one finished ticket on main.
#
#   scripts/integrate-ticket.sh <worktree> <ticket-number>
#
# Exits 0 once the ticket's commit is on the remote's main. Exits non-zero with
# the reason on stderr, having pushed nothing.
#
# A script of its own, so the risky part can be proved against a throwaway
# repository without running a session.

main() {
  set -euo pipefail

  # Enough for a collision with another loop, few enough that this cannot spin.
  ATTEMPTS=3

  say() { printf 'ok    %s\n' "$*"; }
  die() { printf 'FAIL  %s\n' "$*" >&2; exit 1; }

  WORKTREE="${1:-}"
  TICKET="${2:-}"

  usage() {
    printf 'usage: scripts/integrate-ticket.sh <worktree> <ticket-number>\n' >&2
    exit 64
  }

  [ -n "$WORKTREE" ] || usage
  case "$TICKET" in ''|*[!0-9]*) usage ;; esac

  git -C "$WORKTREE" rev-parse --git-dir >/dev/null 2>&1 \
    || die "$WORKTREE is not a git worktree. Nothing was pushed."

  # A commit does not carry unfinished work, so pushing would leave it behind.
  [ -z "$(git -C "$WORKTREE" status --porcelain)" ] \
    || die "#$TICKET has uncommitted changes in $WORKTREE. Nothing was pushed."

  # Without the trailer nothing can trace the commit back to what it was for.
  commit=$(git -C "$WORKTREE" rev-parse --short HEAD)
  named=$(git -C "$WORKTREE" log -1 --format='%(trailers:key=Ticket,valueonly)' \
    | sed -n 1p | tr -d '[:space:]')
  named="${named#\#}"
  [ -n "$named" ] \
    || die "commit $commit carries no 'Ticket: #$TICKET' trailer, so it could never be traced back. Nothing was pushed."
  [ "$named" = "$TICKET" ] \
    || die "commit $commit names ticket #$named, and this is #$TICKET. Nothing was pushed."

  attempt=1
  while :; do
    git -C "$WORKTREE" fetch --quiet origin \
      || die "#$TICKET could not fetch from origin. Nothing was pushed."
    git -C "$WORKTREE" rev-parse --verify --quiet origin/main >/dev/null \
      || die "origin has no main branch. Nothing was pushed."

    if refusal=$(git -C "$WORKTREE" push --quiet origin HEAD:main 2>&1); then
      say "#$TICKET landed on main as $commit"
      return 0
    fi

    [ "$attempt" -lt "$ATTEMPTS" ] || die "$(printf \
      '#%s was refused %s times. Another loop keeps winning the race, or the remote turns the commit down. The last try said:\n%s' \
      "$TICKET" "$ATTEMPTS" "$refusal")"
    attempt=$(( attempt + 1 ))
  done
}

# Bash reads a script while it runs it, so an edit mid-run changes what runs next.
main "$@"; exit
