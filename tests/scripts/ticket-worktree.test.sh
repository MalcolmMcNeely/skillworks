#!/usr/bin/env bash
#
# The worktree script, run against a throwaway repository.

. "$(dirname "${BASH_SOURCE[0]}")/harness.sh"

SCRIPT=scripts/ticket-worktree.sh

group() { printf '%s/.claude/worktrees/spec-%s' "$WORKTREE" "$1"; }

# The case under test is the run the assertions read, so the setup stays quiet.
given_job() { bash "$ROOT/$SCRIPT" open "$WORKTREE" "$1" "$2" >/dev/null 2>&1; }

given_kept() { bash "$ROOT/$SCRIPT" keep "$WORKTREE" "$1" >/dev/null 2>&1; }

has_branch() {  # <spec> <branch leaf>
  git -C "$WORKTREE" rev-parse --verify --quiet "refs/heads/spec-loop/$1/$2" >/dev/null
}

head_of() {  # <spec> <branch leaf>
  git -C "$WORKTREE" rev-parse --verify --quiet "spec-loop/$1/$2"
}

# The records are what the driver reads, so they are read apart from anything git says.
run_keep() {  # <spec>
  OUTPUT=$(bash "$ROOT/$SCRIPT" keep "$WORKTREE" "$1" 2>"$TMP/keep.err")
  STATUS=$?
}

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

case_a_spec_with_no_worktree_has_nothing_to_keep() {
  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the records" "" "$OUTPUT"
}

case_a_leftover_holding_uncommitted_work_is_committed_to_a_branch() {
  given_job 158 ticket-164
  local tree before
  tree=$(group 158)/ticket-164
  before=$(head_of 158 ticket-164)
  printf 'half done\n' >> "$tree/base.txt"
  printf 'new\n' > "$tree/added.txt"

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the record" \
    "$(printf 'ticket-164\tspec-loop/158/ticket-164-kept-1\theld')" "$OUTPUT"
  [ ! -e "$tree" ] || fail "the worktree is still there"
  has_branch 158 ticket-164-kept-1 || fail "the kept branch is not there"
  [ "$(head_of 158 ticket-164-kept-1)" != "$before" ] \
    || fail "the uncommitted work was not committed"
  git -C "$WORKTREE" cat-file -e spec-loop/158/ticket-164-kept-1:added.txt 2>/dev/null \
    || fail "the untracked file is not on the kept branch"
  assert_says "half done" "$(git -C "$WORKTREE" show spec-loop/158/ticket-164-kept-1:base.txt)"
}

case_a_leftover_holding_nothing_uncommitted_is_still_kept() {
  given_job 158 ticket-164
  local before
  before=$(head_of 158 ticket-164)

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the record" \
    "$(printf 'ticket-164\tspec-loop/158/ticket-164-kept-1\tclean')" "$OUTPUT"
  [ ! -e "$(group 158)/ticket-164" ] || fail "the worktree is still there"
  assert_eq "the kept branch's head" "$before" "$(head_of 158 ticket-164-kept-1)"
}

case_a_leftover_changed_only_in_its_line_endings_is_kept() {
  given_job 158 ticket-164
  local tree before
  tree=$(group 158)/ticket-164
  before=$(head_of 158 ticket-164)

  # Git holds the file with one line ending and the worktree now has the other, so the file reads
  # as changed and stages to nothing. Committing that refuses, and the restart would stop.
  git -C "$tree" config core.autocrlf true
  printf 'base\r\n' > "$tree/base.txt"

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the record" \
    "$(printf 'ticket-164\tspec-loop/158/ticket-164-kept-1\tclean')" "$OUTPUT"
  [ ! -e "$tree" ] || fail "the worktree is still there"
  assert_eq "the kept branch's head" "$before" "$(head_of 158 ticket-164-kept-1)"
}

case_keeping_takes_the_spec_group_down() {
  given_job 158 ticket-164

  run_keep 158

  assert_status 0 "$STATUS"
  [ ! -e "$(group 158)" ] || fail "the spec's group is still there"
}

case_a_kept_job_is_free_to_be_opened_again() {
  given_job 158 ticket-164
  printf 'half done\n' > "$(group 158)/ticket-164/loose.txt"
  given_kept 158

  run_script "$SCRIPT" open "$WORKTREE" 158 ticket-164

  assert_status 0 "$STATUS"
  assert_eq "the new worktree's branch" "spec-loop/158/ticket-164" \
    "$(git -C "$(group 158)/ticket-164" rev-parse --abbrev-ref HEAD)"
  has_branch 158 ticket-164-kept-1 || fail "the kept branch went with the restart"
}

case_a_second_attempt_is_kept_beside_the_first() {
  given_job 158 ticket-164
  given_kept 158
  given_job 158 ticket-164

  run_keep 158

  assert_status 0 "$STATUS"
  assert_says "ticket-164-kept-2" "$OUTPUT"
  has_branch 158 ticket-164-kept-1 || fail "the first attempt is gone"
  has_branch 158 ticket-164-kept-2 || fail "the second attempt is not there"
}

case_every_leftover_in_the_group_is_kept() {
  given_job 158 ticket-164
  given_job 158 ticket-165

  run_keep 158

  assert_status 0 "$STATUS"
  assert_says "ticket-164" "$OUTPUT"
  assert_says "ticket-165" "$OUTPUT"
  has_branch 158 ticket-164-kept-1 || fail "ticket-164 was not kept"
  has_branch 158 ticket-165-kept-1 || fail "ticket-165 was not kept"
}

case_a_keep_that_fails_on_a_later_job_still_records_the_one_it_kept() {
  given_job 158 ticket-164
  given_job 158 ticket-165
  refuse_keeping ticket-165

  run_keep 158

  assert_status 1 "$STATUS"
  assert_eq "the record" \
    "$(printf 'ticket-164\tspec-loop/158/ticket-164-kept-1\tclean')" "$OUTPUT"
  has_branch 158 ticket-164-kept-1 || fail "the job it kept is not on a kept branch"
  assert_says "would not rename branch spec-loop/158/ticket-165" "$(cat "$TMP/keep.err")"
}

case_an_empty_group_is_taken_down() {
  given_job 158 ticket-164
  rm -rf "$(group 158)/ticket-164"

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the records" "" "$OUTPUT"
  [ ! -e "$(group 158)" ] || fail "the spec's group is still there"
}

case_a_folder_that_is_no_worktree_is_left_where_it_is() {
  local stray
  stray=$(group 158)/stray
  mkdir -p "$stray"
  printf 'notes\n' > "$stray/notes.txt"

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the records" "" "$OUTPUT"
  [ -e "$stray/notes.txt" ] || fail "the folder was thrown away"
  assert_says "$stray is no worktree of its own, so it was left where it is" "$(cat "$TMP/keep.err")"
}

case_a_worktree_on_no_branch_is_left_where_it_is() {
  local tree
  tree=$(group 158)/ticket-164
  given_job 158 ticket-164
  git -C "$tree" checkout --quiet --detach

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the records" "" "$OUTPUT"
  [ -e "$tree" ] || fail "the worktree was removed"
  assert_says "$tree is on no branch, so it was left where it is" "$(cat "$TMP/keep.err")"
}

case_keeping_one_spec_leaves_another_alone() {
  given_job 158 ticket-164
  given_job 200 ticket-201

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the other spec's worktree" "spec-loop/200/ticket-201" \
    "$(git -C "$(group 200)/ticket-201" rev-parse --abbrev-ref HEAD)"
}

case_keeping_with_a_job_prints_the_usage() {
  run_script "$SCRIPT" keep "$WORKTREE" 158 ticket-164

  assert_status 64 "$STATUS"
  assert_says "usage:" "$OUTPUT"
}

case_closing_leaves_no_worktree_and_no_branch() {
  given_job 158 ticket-164
  printf 'build output\n' > "$(group 158)/ticket-164/untracked.txt"

  run_script "$SCRIPT" close "$WORKTREE" 158 ticket-164

  assert_status 0 "$STATUS"
  assert_says "ticket-164 left nothing behind" "$OUTPUT"
  [ ! -e "$(group 158)/ticket-164" ] || fail "the worktree is still there"
  [ ! -e "$(group 158)" ] || fail "the spec's group is still there"
  ! git -C "$WORKTREE" rev-parse --verify --quiet refs/heads/spec-loop/158/ticket-164 >/dev/null \
    || fail "the branch is still there"
}

case_closing_a_job_left_with_only_its_branch_still_removes_it() {
  given_job 158 ticket-164
  git -C "$WORKTREE" worktree remove --force "$(group 158)/ticket-164"

  run_script "$SCRIPT" close "$WORKTREE" 158 ticket-164

  assert_status 0 "$STATUS"
  assert_says "ticket-164 left nothing behind" "$OUTPUT"
  ! has_branch 158 ticket-164 || fail "the branch is still there"
  [ ! -e "$(group 158)" ] || fail "the spec's group is still there"
}

case_closing_a_job_of_a_spec_that_has_none_is_refused() {
  run_script "$SCRIPT" close "$WORKTREE" 158 ticket-164

  assert_status 1 "$STATUS"
  assert_says "ticket-164" "$OUTPUT"
  assert_says "no worktree and no branch" "$OUTPUT"
}

case_closing_a_job_under_a_name_the_spec_does_not_know_is_refused() {
  given_job 158 ticket-164

  run_script "$SCRIPT" close "$WORKTREE" 158 164

  assert_status 1 "$STATUS"
  assert_says "no worktree and no branch" "$OUTPUT"
  [ -e "$(group 158)/ticket-164" ] || fail "the job that was there was removed"
  has_branch 158 ticket-164 || fail "the branch of the job that was there is gone"
}

case_a_closed_job_leaves_nothing_to_keep() {
  given_job 158 ticket-164
  bash "$ROOT/$SCRIPT" close "$WORKTREE" 158 ticket-164 >/dev/null 2>&1

  run_keep 158

  assert_status 0 "$STATUS"
  assert_eq "the records" "" "$OUTPUT"
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
