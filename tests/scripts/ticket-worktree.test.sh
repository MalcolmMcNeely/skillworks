#!/usr/bin/env bash
#
# The worktree script, run against a throwaway repository.

. "$(dirname "${BASH_SOURCE[0]}")/harness.sh"

SCRIPT=scripts/ticket-worktree.sh

group() { printf '%s/.claude/worktrees/spec-%s' "$WORKTREE" "$1"; }

# The case under test is the run the assertions read, so the setup stays quiet.
given_job() { bash "$ROOT/$SCRIPT" open "$WORKTREE" "$1" "$2" >/dev/null 2>&1; }

case_a_job_is_branched_from_the_newest_origin_main() {
  advance_origin later
  local newest tree
  newest=$(git -C "$ORIGIN" rev-parse main)
  tree=$(group 158)/ticket-164

  run_script "$SCRIPT" open "$WORKTREE" 158 ticket-164

  assert_status 0 "$STATUS"
  assert_eq "the path it printed" "$tree" "$OUTPUT"
  assert_eq "the worktree's head" "$newest" "$(git -C "$tree" rev-parse HEAD)"
  assert_eq "the worktree's branch" "spec-loop/158/ticket-164" \
    "$(git -C "$tree" rev-parse --abbrev-ref HEAD)"
}

case_a_dirty_checkout_still_gives_a_job_its_worktree() {
  printf 'loose\n' > "$WORKTREE/loose.txt"

  run_script "$SCRIPT" open "$WORKTREE" 158 ticket-164

  assert_status 0 "$STATUS"
  assert_eq "the worktree's branch" "spec-loop/158/ticket-164" \
    "$(git -C "$(group 158)/ticket-164" rev-parse --abbrev-ref HEAD)"
}

case_a_plan_says_where_a_job_would_go_and_makes_nothing() {
  run_script "$SCRIPT" plan "$WORKTREE" 158 ticket-168

  assert_status 0 "$STATUS"
  assert_eq "what it printed" \
    "$(printf '%s\t%s' "$(group 158)/ticket-168" spec-loop/158/ticket-168)" "$OUTPUT"
  [ ! -e "$(group 158)" ] || fail "the plan made a worktree group"
  ! git -C "$WORKTREE" rev-parse --verify --quiet refs/heads/spec-loop/158/ticket-168 >/dev/null \
    || fail "the plan made a branch"
}

case_a_plan_for_a_spec_with_a_worktree_group_is_still_given() {
  given_job 158 ticket-164

  run_script "$SCRIPT" plan "$WORKTREE" 158 ticket-168

  assert_status 0 "$STATUS"
  assert_says "$(group 158)/ticket-168" "$OUTPUT"
}

case_a_spec_with_no_worktree_is_clear_to_start() {
  run_script "$SCRIPT" check "$WORKTREE" 158

  assert_status 0 "$STATUS"
}

case_a_second_loop_on_the_same_spec_is_refused() {
  given_job 158 ticket-164

  run_script "$SCRIPT" check "$WORKTREE" 158

  assert_status 1 "$STATUS"
  assert_says "spec #158" "$OUTPUT"
  assert_says "$(group 158)/ticket-164" "$OUTPUT"
  assert_says "cd " "$OUTPUT"
  assert_says "$ROOT/$SCRIPT' close" "$OUTPUT"
}

case_an_empty_group_still_names_the_way_out() {
  given_job 158 ticket-164
  rm -rf "$(group 158)/ticket-164"

  run_script "$SCRIPT" check "$WORKTREE" 158

  assert_status 1 "$STATUS"
  assert_says "rmdir '$(group 158)'" "$OUTPUT"
}

case_a_loop_on_another_spec_is_clear_to_start() {
  given_job 158 ticket-164

  run_script "$SCRIPT" check "$WORKTREE" 200

  assert_status 0 "$STATUS"
  assert_eq "the other spec's worktree" "spec-loop/158/ticket-164" \
    "$(git -C "$(group 158)/ticket-164" rev-parse --abbrev-ref HEAD)"
}

case_closing_leaves_no_worktree_and_no_branch() {
  given_job 158 ticket-164
  printf 'build output\n' > "$(group 158)/ticket-164/untracked.txt"

  run_script "$SCRIPT" close "$WORKTREE" 158 ticket-164

  assert_status 0 "$STATUS"
  [ ! -e "$(group 158)/ticket-164" ] || fail "the worktree is still there"
  [ ! -e "$(group 158)" ] || fail "the spec's group is still there"
  ! git -C "$WORKTREE" rev-parse --verify --quiet refs/heads/spec-loop/158/ticket-164 >/dev/null \
    || fail "the branch is still there"
}

case_a_closed_spec_is_clear_to_start_again() {
  given_job 158 ticket-164
  bash "$ROOT/$SCRIPT" close "$WORKTREE" 158 ticket-164 >/dev/null 2>&1

  run_script "$SCRIPT" check "$WORKTREE" 158

  assert_status 0 "$STATUS"
}

case_opening_a_job_twice_is_refused() {
  given_job 158 ticket-164

  run_script "$SCRIPT" open "$WORKTREE" 158 ticket-164

  assert_status 1 "$STATUS"
  assert_says "already" "$OUTPUT"
}

case_a_leftover_branch_is_refused_and_names_its_removal() {
  given_job 158 ticket-164
  bash "$ROOT/$SCRIPT" close "$WORKTREE" 158 ticket-164 >/dev/null 2>&1
  git -C "$WORKTREE" branch spec-loop/158/ticket-164 main

  run_script "$SCRIPT" open "$WORKTREE" 158 ticket-164

  assert_status 1 "$STATUS"
  assert_says "$ROOT/$SCRIPT' close" "$OUTPUT"
}

case_a_remote_with_no_main_is_refused() {
  git -C "$ORIGIN" update-ref -d refs/heads/main
  git -C "$WORKTREE" update-ref -d refs/remotes/origin/main

  run_script "$SCRIPT" open "$WORKTREE" 158 ticket-164

  assert_status 1 "$STATUS"
  assert_says "no main" "$OUTPUT"
}

case_a_path_that_holds_no_repository_is_refused() {
  run_script "$SCRIPT" open "$TMP/nowhere" 158 ticket-164

  assert_status 1 "$STATUS"
  assert_says "not a git worktree" "$OUTPUT"
}

case_arguments_of_the_wrong_shape_print_the_usage() {
  run_script "$SCRIPT" open "$WORKTREE" 158

  assert_status 64 "$STATUS"
  assert_says "usage:" "$OUTPUT"
}

case_an_unknown_command_prints_the_usage() {
  run_script "$SCRIPT" wreck "$WORKTREE" 158 ticket-164

  assert_status 64 "$STATUS"
  assert_says "usage:" "$OUTPUT"
}

run_cases
