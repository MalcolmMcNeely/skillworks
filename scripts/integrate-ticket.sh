#!/usr/bin/env bash
#
# Land one finished ticket on main.
#
#   scripts/integrate-ticket.sh <worktree> <ticket-number>
#
# Exits 0 once the ticket's commit is on the remote's main. Exits non-zero with
# the reason on stderr, having pushed nothing.
#
# Another loop lands its own work while a ticket is built, so a moved base is
# rebased onto, and the suite is asked again before the push.
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

  # The README's checks, skipped where there is none, so a throwaway repository runs this.
  suite() {
    local web="$WORKTREE/src/Skillworks.Studio.Web" found=0
    if [ -f "$WORKTREE/Skillworks.slnx" ]; then
      found=1
      ( cd "$WORKTREE" && dotnet test Skillworks.slnx ) || return 1
    fi
    if [ -f "$WORKTREE/tests/scripts/run.sh" ]; then
      found=1
      ( cd "$WORKTREE" && bash tests/scripts/run.sh ) || return 1
    fi
    if [ -f "$web/package.json" ]; then
      found=1
      # A fresh worktree has nothing installed unless the ticket touched the front end.
      [ -d "$web/node_modules" ] || ( cd "$web" && npm ci ) || return 1
      ( cd "$web" && npm run typecheck && npm run lint && npm test ) || return 1
    fi
    # A checkout holding none of them is broken, and a suite that ran nothing cannot pass.
    if [ "$found" = 0 ]; then
      printf 'this checkout holds none of the checks the README names\n'
      return 1
    fi
  }

  # The suite says a great deal, and only a failure is worth reading.
  run_suite() {
    local said
    said=$(suite 2>&1) && return 0
    die "$(printf \
      '#%s passed on its own and then failed the suite on the new base. Nothing was pushed. The suite said:\n%s' \
      "$TICKET" "$said")"
  }

  rebase_onto_main() {
    local base="$1" mine landed said
    mine=$(git -C "$WORKTREE" rev-list --count "$base..HEAD") \
      || die "#$TICKET could not be counted against its base. Nothing was pushed."

    # The conflict is left standing, because whoever resolves it has to see it.
    if ! said=$(git -C "$WORKTREE" rebase origin/main 2>&1); then
      die "$(printf \
        '#%s conflicts with what landed on main while it was being built. The rebase is still open in %s, and nothing was pushed. Put it back with: git -C %s rebase --abort\ngit said:\n%s' \
        "$TICKET" "$WORKTREE" "$WORKTREE" "$said")"
    fi

    # A rebase that quietly dropped the work would otherwise push an empty success.
    landed=$(git -C "$WORKTREE" rev-list --count "origin/main..HEAD") \
      || die "#$TICKET could not be counted against the new base. Nothing was pushed."
    [ "$landed" = "$mine" ] || die "$(printf \
      '#%s had %s commit(s) before the rebase and has %s on the new base. The rebase dropped work, and nothing was pushed. Get it back with: git -C %s reset --hard ORIG_HEAD' \
      "$TICKET" "$mine" "$landed" "$WORKTREE")"

    commit=$(git -C "$WORKTREE" rev-parse --short HEAD)
    say "#$TICKET rebased onto $(git -C "$WORKTREE" rev-parse --short origin/main) as $commit"

    # A merge that resolves with no conflict can still break the program.
    run_suite
    say "#$TICKET passed the suite on the new base"
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

    # A ticket already on main has nothing to land, and a push would call that a success.
    [ -n "$(git -C "$WORKTREE" rev-list -1 "origin/main..HEAD")" ] \
      || die "#$TICKET is already on main and has nothing left to land. Nothing was pushed."

    # An unmoved base is one the finishing step's own test run still answers for.
    base=$(git -C "$WORKTREE" merge-base HEAD origin/main)
    [ "$base" = "$(git -C "$WORKTREE" rev-parse origin/main)" ] || rebase_onto_main "$base"

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
