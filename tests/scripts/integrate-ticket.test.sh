#!/usr/bin/env bash
#
# The integration script, run against a throwaway repository.

. "$(dirname "${BASH_SOURCE[0]}")/harness.sh"

SCRIPT=scripts/integrate-ticket.sh

case_a_finished_ticket_reaches_the_remote() {
  stub claude
  stub dotnet
  stub npm
  commit_for_ticket 163
  local head
  head=$(git -C "$WORKTREE" rev-parse HEAD)

  run_script "$SCRIPT" "$WORKTREE" 163

  assert_status 0 "$STATUS"
  assert_says "#163" "$OUTPUT"
  assert_eq "the remote's main" "$head" "$(git -C "$ORIGIN" rev-parse main)"
  assert_eq "the ticket's commit" "$head" "$(git -C "$WORKTREE" rev-parse HEAD)"
  ! called claude || fail "a session was started"
  ! called dotnet || fail "the suite ran again"
  ! called npm || fail "the suite ran again"
}

case_a_commit_that_names_no_ticket_is_refused() {
  commit_naming_nothing
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 163

  assert_status 1 "$STATUS"
  assert_says "Ticket: #163" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_commit_that_names_another_ticket_is_refused() {
  commit_for_ticket 999
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 163

  assert_status 1 "$STATUS"
  assert_says "#999" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_refused_push_is_tried_three_times_and_no_more() {
  commit_for_ticket 163
  refuse_pushes
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 163

  assert_status 1 "$STATUS"
  assert_eq "pushes the remote saw" 3 "$(push_tries)"
  assert_says "3 times" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_uncommitted_work_is_refused() {
  commit_for_ticket 163
  printf 'loose\n' > "$WORKTREE/loose.txt"
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 163

  assert_status 1 "$STATUS"
  assert_says "uncommitted" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_path_that_holds_no_repository_is_refused() {
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$TMP/nowhere" 163

  assert_status 1 "$STATUS"
  assert_says "not a git worktree" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_arguments_of_the_wrong_shape_print_the_usage() {
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE"

  assert_status 64 "$STATUS"
  assert_says "usage:" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

run_cases
