#!/usr/bin/env bash
#
# Land one finished ticket on main.
#
#   scripts/integrate-ticket.sh <worktree> <ticket-number> [session-id]
#
# Exits 0 once the ticket's commit is on the remote's main. Exits non-zero with
# the reason on stderr, having pushed nothing.
#
# Another loop lands its own work while a ticket is built, so a moved base is
# rebased onto, and the suite is asked again before the push.
#
# The session that built the ticket wrote one side of any conflict, so it is the
# one asked to resolve it.
#
# Env:
#   SPEC_LOOP_PERMISSION_MODE   passed to `claude -p` (default: acceptEdits)
#
# A script of its own, so the risky part can be proved against a throwaway
# repository without running a session.

main() {
  set -euo pipefail

  # Enough for a collision with another loop, few enough that this cannot spin.
  ATTEMPTS=3

  NL=$'\n'

  say() { printf 'ok    %s\n' "$*"; }
  die() { printf 'FAIL  %s\n' "$*" >&2; exit 1; }

  WORKTREE="${1:-}"
  TICKET="${2:-}"
  SESSION="${3:-}"

  usage() {
    printf 'usage: scripts/integrate-ticket.sh <worktree> <ticket-number> [session-id]\n' >&2
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

  # --- what the resolving session is given ----------------------------------

  # Read from the message, so a commit reaches its ticket with no tracker call.
  ticket_of() {  # <commit>
    git -C "$WORKTREE" log -1 "$1" --format='%(trailers:key=Ticket,valueonly)' \
      | sed -n 1p | tr -d '[:space:]' | sed 's/^#//'
  }

  # A ticket is closed with a comment, so the last one on it is that comment.
  # A session told a ticket said nothing would refuse on a reading it never got.
  closing_comment() {  # <ticket>
    local body
    # Stdin is the caller's list of commits, and gh would read it away.
    body=$( ( cd "$WORKTREE" \
      && gh issue view "$1" --json comments --jq '.comments[-1].body' </dev/null ) 2>/dev/null ) \
      || { printf '(The tracker would not answer for #%s, so its closing comment is missing.)' "$1"
           return 0; }
    [ -n "$body" ] || { printf '(#%s was closed with no comment.)' "$1"; return 0; }
    printf '%s' "$body"
  }

  # The session may only refuse for want of a ticket once it has had them all.
  other_side() {  # <base>
    local commits line sha subject ticket comment
    commits=$(git -C "$WORKTREE" log --reverse --format='%h %s' "$1..origin/main") || return 1
    while IFS= read -r line; do
      [ -n "$line" ] || continue
      sha=${line%% *}
      subject=${line#* }
      ticket=$(ticket_of "$sha")
      if [ -z "$ticket" ]; then
        printf '### %s %s\n\nThis commit names no ticket. Read it with: git show %s\n\n' \
          "$sha" "$subject" "$sha"
        continue
      fi
      comment=$(closing_comment "$ticket")
      printf '### %s %s, from ticket #%s\n\nHow #%s was closed:\n\n%s\n\n' \
        "$sha" "$subject" "$ticket" "$ticket" "$comment"
    done <<<"$commits"
  }

  resolve_prompt() {  # <base> <conflicting files>
    printf '/resolve-conflict\n\n'
    printf 'Ticket #%s was rebased onto the newest origin/main and stopped on a conflict.\n' "$TICKET"
    printf 'Its worktree is %s, and the rebase is open in it.\n\n' "$WORKTREE"
    printf '## The conflicting files\n\n%s\n\n' "$2"
    printf '## The other side\n\nThese landed on main while #%s was being built.\n\n' "$TICKET"
    other_side "$1"
  }

  # Git Bash reads a leading slash as a path, and would ask for a command nobody has.
  resolve_call() {  # <prompt>
    ( cd "$WORKTREE" \
      && MSYS_NO_PATHCONV=1 env -u CLAUDECODE claude -p "$1" \
           --resume "$SESSION" --permission-mode "$PERMISSION_MODE" )
  }

  # --- resolving, and proving the resolution --------------------------------

  resolve_conflict() {  # <base> <what the rebase said>
    local base="$1" refused="$2" conflicted prompt said left file carried

    [ -n "$SESSION" ] || die "$(printf \
      '#%s conflicts with what landed on main while it was being built, and no session was named to resolve it. The rebase is still open in %s, and nothing was pushed. Put it back with: git -C %s rebase --abort\ngit said:\n%s' \
      "$TICKET" "$WORKTREE" "$WORKTREE" "$refused")"

    conflicted=$(git -C "$WORKTREE" diff --name-only --diff-filter=U)
    [ -n "$conflicted" ] || die "$(printf \
      '#%s stopped its rebase in %s with no conflicting file in it, so there is nothing to resolve. Nothing was pushed.\ngit said:\n%s' \
      "$TICKET" "$WORKTREE" "$refused")"

    say "#$TICKET conflicts with the other side. Session $SESSION wrote its side, so it resolves it."

    # A function reached through || runs with errexit off, so each step says so itself.
    prompt=$(resolve_prompt "$base" "$conflicted") || die \
      "#$TICKET could not gather the other side to hand over. Nothing was pushed."
    said=$(resolve_call "$prompt" 2>&1) || die "$(printf \
      '#%s handed its conflict to session %s, which exited non-zero. The rebase is still open in %s, and nothing was pushed. It said:\n%s' \
      "$TICKET" "$SESSION" "$WORKTREE" "$said")"

    # The skill refuses by leaving the conflict where it stands.
    left=$(git -C "$WORKTREE" diff --name-only --diff-filter=U)
    [ -z "$left" ] || die "$(printf \
      '#%s came back from session %s with these files still conflicting:\n%s\nThe rebase is still open in %s, and nothing was pushed. The session said:\n%s' \
      "$TICKET" "$SESSION" "$left" "$WORKTREE" "$said")"

    # A commit is made of the index, so the index is what is read here.
    while IFS= read -r file; do
      [ -n "$file" ] || continue
      # A hunk can be settled by removing the file, and then there is nothing to read.
      git -C "$WORKTREE" cat-file -e ":$file" 2>/dev/null || continue
      # A blob committed with CRLF ends its marker line in a carriage return.
      if git -C "$WORKTREE" grep --cached -q -E '^(<<<<<<< |=======[[:space:]]*$|>>>>>>> )' -- "$file"; then
        die "$(printf \
          '#%s staged %s with a conflict marker still in it, so the resolution is half finished. The rebase is still open in %s, and nothing was pushed. The session said:\n%s' \
          "$TICKET" "$file" "$WORKTREE" "$said")"
      fi
    done <<<"$conflicted"

    if ! carried=$(GIT_EDITOR=true git -C "$WORKTREE" rebase --continue 2>&1); then
      # One call resolves one commit, so a ticket whose next commit conflicts stops here.
      [ -z "$(git -C "$WORKTREE" diff --name-only --diff-filter=U)" ] || die "$(printf \
        '#%s resolved its first conflict and a later commit of its own conflicted as well. Only the first is handed over, so the rebase is still open in %s, and nothing was pushed. Put it back with: git -C %s rebase --abort' \
        "$TICKET" "$WORKTREE" "$WORKTREE")"
      die "$(printf \
        '#%s resolved its conflicting files and the rebase would not carry on. The rebase is still open in %s, and nothing was pushed. git said:\n%s' \
        "$TICKET" "$WORKTREE" "$carried")"
    fi

    say "#$TICKET resolved its conflict in session $SESSION"
  }

  # A rebase that quietly dropped the work would otherwise push an empty success.
  survived() {  # <commits before> <files before>
    local mine="$1" before="$2" landed now file missing=""
    landed=$(git -C "$WORKTREE" rev-list --count "origin/main..HEAD") \
      || die "#$TICKET could not be counted against the new base. Nothing was pushed."
    [ "$landed" = "$mine" ] || die "$(printf \
      '#%s had %s commit(s) before the rebase and has %s on the new base. The rebase dropped work, and nothing was pushed. Get it back with: git -C %s reset --hard ORIG_HEAD' \
      "$TICKET" "$mine" "$landed" "$WORKTREE")"

    # A resolution that takes the other side wholesale keeps the commit and loses the file.
    now=$(git -C "$WORKTREE" diff --name-only origin/main HEAD) \
      || die "#$TICKET could not be read against the new base. Nothing was pushed."
    while IFS= read -r file; do
      [ -n "$file" ] || continue
      case "$NL$now$NL" in
        *"$NL$file$NL"*) ;;
        *) missing="$missing$NL  $file" ;;
      esac
    done <<<"$before"
    [ -z "$missing" ] || die "$(printf \
      '#%s changed these files before the rebase and no longer changes them on the new base:%s\nThe rebase dropped work, and nothing was pushed. Get it back with: git -C %s reset --hard ORIG_HEAD' \
      "$TICKET" "$missing" "$WORKTREE")"
  }

  rebase_onto_main() {
    local base="$1" mine mine_files said
    mine=$(git -C "$WORKTREE" rev-list --count "$base..HEAD") \
      || die "#$TICKET could not be counted against its base. Nothing was pushed."
    mine_files=$(git -C "$WORKTREE" diff --name-only "$base" HEAD) \
      || die "#$TICKET could not be read against its base. Nothing was pushed."

    said=$(git -C "$WORKTREE" rebase origin/main 2>&1) || resolve_conflict "$base" "$said"

    survived "$mine" "$mine_files"

    commit=$(git -C "$WORKTREE" rev-parse --short HEAD)
    say "#$TICKET rebased onto $(git -C "$WORKTREE" rev-parse --short origin/main) as $commit"

    # A merge that resolves with no conflict can still break the program.
    run_suite
    say "#$TICKET passed the suite on the new base"
  }

  [ -n "$WORKTREE" ] || usage
  case "$TICKET" in ''|*[!0-9]*) usage ;; esac

  PERMISSION_MODE="${SPEC_LOOP_PERMISSION_MODE:-acceptEdits}"

  git -C "$WORKTREE" rev-parse --git-dir >/dev/null 2>&1 \
    || die "$WORKTREE is not a git worktree. Nothing was pushed."

  # A commit does not carry unfinished work, so pushing would leave it behind.
  [ -z "$(git -C "$WORKTREE" status --porcelain)" ] \
    || die "#$TICKET has uncommitted changes in $WORKTREE. Nothing was pushed."

  # Without the trailer nothing can trace the commit back to what it was for.
  commit=$(git -C "$WORKTREE" rev-parse --short HEAD)
  named=$(ticket_of HEAD)
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
