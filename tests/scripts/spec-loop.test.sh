#!/usr/bin/env bash
#
# The spec loop's dry run, read against a throwaway repository.

. "$(dirname "${BASH_SOURCE[0]}")/harness.sh"

SCRIPT=scripts/spec-loop.sh

ONE_OPEN_TICKET=$'168\topen\tTICKET: The dry run prints the plan'

# The dry run puts its log where it is run, so it is run in the throwaway repository.
run_loop() {  # <args...>
  OUTPUT=$(cd "$WORKTREE" && bash "$ROOT/$SCRIPT" "$@" 2>&1)
  STATUS=$?
}

# Every answer the dry run asks for and no others, so an unplanned call fails rather than guesses.
given_the_tracker_holds() {  # <number, state and title per ticket, tab separated>
  printf '%s\n' "$1" > "$TMP/tickets"
  stub claude
  stub node
  stub gh
  printf 'TICKETS="%s"\n' "$TMP/tickets" >> "$STUBS/gh"
  cat >> "$STUBS/gh" <<'STUB'
case "$*" in
  "auth status")                                        exit 0 ;;
  "repo view --json nameWithOwner --jq .nameWithOwner")  echo owner/repo ;;
  "api user --jq .login")                               echo me ;;
  *"--jq .state")                                       echo open ;;
  *"--jq .title")                                       echo "SPEC: A spec to plan" ;;
  *sub_issues*".[].number")                             cut -f1 "$TICKETS" ;;
  *sub_issues*)                                         cat "$TICKETS" ;;
  *) echo "the gh stub has no answer for: $*" >&2;      exit 1 ;;
esac
STUB
}

case_the_dry_run_prints_the_worktree_and_the_branch() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_says "$WORKTREE/.claude/worktrees/spec-158/ticket-168" "$OUTPUT"
  assert_says "spec-loop/158/ticket-168" "$OUTPUT"
}

case_the_dry_run_prints_every_integration_step_with_its_checks() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  local step what checks found=0
  while IFS=$'\t' read -r step what checks; do
    [ -n "$step" ] || continue
    found=$(( found + 1 ))
    assert_says "$what" "$OUTPUT"
    assert_says "checks: $checks" "$OUTPUT"
  done < <(bash "$ROOT/scripts/integrate-ticket.sh" --plan)
  # A plan that named no step would otherwise let this case pass having read nothing.
  [ "$found" -gt 0 ] || fail "the integration script named no step to look for"
}

case_the_dry_run_still_prints_the_sessions_it_would_start() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_says '/implement 168 --stop-after-tests' "$OUTPUT"
  assert_says '/comment-sweep' "$OUTPUT"
  assert_says '/implement 168 --finish' "$OUTPUT"
  assert_says 'checks: no-error command-loaded ticket-open tree-changed' "$OUTPUT"
  assert_says 'checks: no-error command-loaded new-commit tree-clean ticket-closed' "$OUTPUT"
}

case_a_closed_ticket_is_listed_and_given_no_plan() {
  given_the_tracker_holds "$(printf '161\tclosed\tTICKET: Already done\n168\topen\tTICKET: Still to do')"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_says "#161 [closed]" "$OUTPUT"
  case "$OUTPUT" in
    *ticket-161*) fail "a closed ticket was given a worktree" ;;
  esac
}

case_the_dry_run_starts_no_session_and_reaches_no_remote() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  ! called claude || fail "a session was started"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  [ ! -e "$WORKTREE/.claude/worktrees" ] || fail "a worktree was made"
  assert_eq "branches in the checkout" "main" \
    "$(git -C "$WORKTREE" for-each-ref --format='%(refname:short)' refs/heads)"
}

case_the_plan_is_written_to_the_log_as_well() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_says "spec-loop/158/ticket-168" "$(cat "$WORKTREE/.spec-loop/158/loop.log")"
}

run_cases
