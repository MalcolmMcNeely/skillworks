#!/usr/bin/env bash
#
# The integration script, run against a throwaway repository.

. "$(dirname "${BASH_SOURCE[0]}")/harness.sh"

SCRIPT=scripts/integrate-ticket.sh

case_a_finished_ticket_reaches_the_remote() {
  stub claude
  stub dotnet
  stub npm
  given_a_project
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

case_a_moved_base_is_rebased_and_the_suite_runs_again() {
  stub dotnet
  stub npm
  given_a_project
  advance_origin later
  commit_for_ticket 165
  local other_side
  other_side=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 165

  assert_status 0 "$STATUS"
  ran "dotnet test Skillworks.slnx" || fail "the .NET suite did not run again"
  ran "npm test" || fail "the front-end tests did not run again"
  assert_eq "the remote's main" \
    "$(git -C "$WORKTREE" rev-parse HEAD)" "$(git -C "$ORIGIN" rev-parse main)"
  assert_eq "what the ticket sits on" "$other_side" "$(git -C "$WORKTREE" rev-parse HEAD^)"
  ! git -C "$WORKTREE" rev-parse --verify --quiet HEAD^2 >/dev/null \
    || fail "the other side was merged in, not rebased onto"
  assert_eq "the other side's file on main" "later" "$(git -C "$ORIGIN" show main:later.txt)"
  assert_eq "the ticket's file on main" "work" "$(git -C "$ORIGIN" show main:work.txt)"
}

case_a_suite_that_fails_on_the_new_base_is_not_pushed() {
  stub_failure dotnet
  stub npm
  given_a_project
  advance_origin later
  commit_for_ticket 165
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 165

  assert_status 1 "$STATUS"
  assert_says "failed the suite" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_checkout_with_no_checks_at_all_is_refused() {
  stub dotnet
  stub npm
  advance_origin later
  commit_for_ticket 165
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 165

  assert_status 1 "$STATUS"
  assert_says "none of the checks" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_ticket_already_on_main_is_refused() {
  stub dotnet
  stub npm
  given_a_project
  commit_for_ticket 165
  git -C "$WORKTREE" push --quiet origin main
  advance_origin later
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 165

  assert_status 1 "$STATUS"
  assert_says "already on main" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  ! called dotnet || fail "the suite ran for a ticket with nothing to land"
}

case_a_rebase_that_drops_the_ticket_is_refused() {
  stub dotnet
  stub npm
  given_a_project
  # The other side made the very change this ticket makes, so nothing is left to replay.
  advance_origin work
  commit_for_ticket 165
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 165

  assert_status 1 "$STATUS"
  assert_says "dropped" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  ! called dotnet || fail "the suite ran on work that was already gone"
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
