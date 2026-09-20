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

case_a_plan_names_every_step_with_its_checks_and_lands_nothing() {
  stub claude
  stub dotnet
  stub npm
  local base step
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" --plan

  assert_status 0 "$STATUS"
  for step in verify fetch rebase resolve suite push; do
    assert_says "$step" "$OUTPUT"
  done
  # The driver reads a name, what runs and the checks, so a line short of one says nothing.
  assert_eq "lines short of all three fields" 0 \
    "$(printf '%s\n' "$OUTPUT" \
       | awk -F'\t' 'NF != 3 || $1 == "" || $2 == "" || $3 == ""' | wc -l | tr -d ' ')"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  ! called claude || fail "a session was started"
  ! called dotnet || fail "the suite ran"
  ! called npm || fail "the suite ran"
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

given_the_other_side_changed() {  # <the other side's ticket>
  write_commit "$WORKTREE" shared.txt "start" "A file both sides will change"
  git -C "$WORKTREE" push --quiet origin main
  push_from_elsewhere shared.txt "their line" \
    "$(printf 'Somebody else got there first\n\nTicket: #%s' "$1")"
}

given_a_conflict() {  # <this ticket> <the other side's ticket>
  given_the_other_side_changed "$2"
  write_commit "$WORKTREE" shared.txt "my line" \
    "$(printf 'Do the work\n\nTicket: #%s' "$1")"
}

# Two files in one commit, so dropping one still leaves a commit to replay.
given_a_conflict_beside_other_work() {  # <this ticket> <the other side's ticket>
  given_the_other_side_changed "$2"
  printf 'my line\n' >> "$WORKTREE/shared.txt"
  printf 'work\n' >> "$WORKTREE/work.txt"
  git -C "$WORKTREE" add -A
  git -C "$WORKTREE" commit --quiet -m "$(printf 'Do the work\n\nTicket: #%s' "$1")"
}

# Two files, so a count of one cannot pass for a measurement.
given_two_conflicting_files() {  # <this ticket> <the other side's ticket>
  local other
  write_commit "$WORKTREE" shared.txt "start" "A file both sides will change"
  write_commit "$WORKTREE" also.txt "start" "Another file both sides will change"
  git -C "$WORKTREE" push --quiet origin main

  other=$(other_checkout)
  printf 'their line\n' >> "$other/shared.txt"
  printf 'their line\n' >> "$other/also.txt"
  git -C "$other" add -A
  git -C "$other" commit --quiet -m \
    "$(printf 'Somebody else got there first\n\nTicket: #%s' "$2")"
  git -C "$other" push --quiet origin main

  printf 'my line\n' >> "$WORKTREE/shared.txt"
  printf 'my line\n' >> "$WORKTREE/also.txt"
  git -C "$WORKTREE" add -A
  git -C "$WORKTREE" commit --quiet -m "$(printf 'Do the work\n\nTicket: #%s' "$1")"
}

# Deleted on one side and changed on the other, so the file is unmerged with no marker in it.
given_a_conflict_with_no_marker() {  # <this ticket> <the other side's ticket>
  local other
  write_commit "$WORKTREE" shared.txt "start" "A file one side will delete"
  git -C "$WORKTREE" push --quiet origin main

  other=$(other_checkout)
  git -C "$other" rm --quiet shared.txt
  git -C "$other" commit --quiet -m \
    "$(printf 'Somebody else deleted it\n\nTicket: #%s' "$2")"
  git -C "$other" push --quiet origin main

  write_commit "$WORKTREE" shared.txt "my line" \
    "$(printf 'Do the work\n\nTicket: #%s' "$1")"
}

stub_session() {  # <shell line, reading each conflicting file as "$f">
  stub claude
  {
    printf 'cd "%s" || exit 1\n' "$WORKTREE"
    printf 'git diff --name-only --diff-filter=U | while IFS= read -r f; do\n'
    printf '  %s\n' "$1"
    printf 'done\n'
  } >> "$STUBS/claude"
}

case_a_conflict_is_handed_back_to_the_ticket_s_own_session() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  stub_session 'printf "start\ntheir line\nmy line\n" > "$f"; git add "$f"'
  given_a_project
  given_a_conflict 166 164
  local theirs handed
  theirs=$(git -C "$ORIGIN" rev-parse --short main)

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 0 "$STATUS"
  handed=$(calls)
  assert_says "/resolve-conflict" "$handed"
  assert_says "--resume session-abc" "$handed"
  assert_says "$theirs" "$handed"
  assert_says "Somebody else got there first" "$handed"
  # No answer gh gave holds the number, so only the commit message can have carried it.
  assert_says "#164" "$handed"
  assert_says "What that ticket set out to do." "$handed"
  # Both sides of a hunk count, because the size is what has to be read to settle it.
  assert_says "conflict #166 files=1 hunks=1 lines=2 outcome=resolved" "$OUTPUT"
  assert_eq "the remote's main" \
    "$(git -C "$WORKTREE" rev-parse HEAD)" "$(git -C "$ORIGIN" rev-parse main)"
  assert_eq "the resolved file on main" \
    "$(printf 'start\ntheir line\nmy line')" "$(git -C "$ORIGIN" show main:shared.txt)"
  ran "dotnet test Skillworks.slnx" || fail "the suite did not run on the resolution"
}

case_a_refusal_stops_the_run_and_names_the_rule_that_fired() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  # A refusal leaves the conflict where it stands, so this stub touches no file.
  stub_saying claude "$(printf 'REFUSED 1: neither side says which count the tile shows.\n\nMine wanted a count per skill. Theirs wanted a count per session.')"
  given_a_project
  given_two_conflicting_files 167 164
  local base mine
  base=$(git -C "$ORIGIN" rev-parse main)
  mine=$(git -C "$WORKTREE" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 167 session-abc

  assert_status 1 "$STATUS"
  assert_says "refused under rule 1" "$OUTPUT"
  # The developer fixes the cause from the log, so both intentions have to reach it.
  assert_says "Mine wanted a count per skill." "$OUTPUT"
  assert_says "Theirs wanted a count per session." "$OUTPUT"
  assert_says "conflict #167 files=2 hunks=2 lines=4 outcome=refused" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  [ -d "$WORKTREE" ] || fail "the worktree was removed"
  assert_eq "the ticket's branch" "$mine" "$(git -C "$WORKTREE" rev-parse main)"
  [ -n "$(git -C "$WORKTREE" diff --name-only --diff-filter=U)" ] \
    || fail "the conflict was not left standing to be read"
}

case_a_refusal_that_staged_everything_still_stops_the_run() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  # Rule 2 fires after the checks fail, by which time the files can already be staged.
  stub_session 'printf "resolved\n" > "$f"; git add "$f"'
  printf 'echo "REFUSED 2: the typecheck still fails and I cannot see why."\n' >> "$STUBS/claude"
  given_a_project
  given_a_conflict 167 164
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 167 session-abc

  assert_status 1 "$STATUS"
  assert_says "refused under rule 2" "$OUTPUT"
  assert_says "outcome=refused" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  ! called dotnet || fail "the suite ran on a resolution the session had refused"
}

case_a_conflict_with_no_marker_in_it_is_still_measured() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  stub_session 'git add "$f"'
  given_a_project
  given_a_conflict_with_no_marker 167 164

  run_script "$SCRIPT" "$WORKTREE" 167 session-abc

  assert_status 0 "$STATUS"
  # A file with no marker in it counts none, rather than summing an empty field.
  assert_says "conflict #167 files=1 hunks=0 lines=0 outcome=resolved" "$OUTPUT"
  case "$OUTPUT" in
    *arithmetic*) fail "counting a marker-free conflict broke the arithmetic" ;;
  esac
}

case_a_leftover_conflict_marker_is_caught() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  stub_session 'printf "<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> them\n" > "$f"; git add "$f"'
  given_a_project
  given_a_conflict 166 164
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 1 "$STATUS"
  assert_says "conflict marker" "$OUTPUT"
  assert_says "shared.txt" "$OUTPUT"
  assert_says "conflict #166 files=1 hunks=1 lines=2 outcome=caught" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  ! called dotnet || fail "the suite ran on a half-finished resolution"
}

case_a_session_that_resolves_nothing_leaves_the_conflict_standing() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  stub_session ':'
  given_a_project
  given_a_conflict 166 164
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 1 "$STATUS"
  assert_says "still conflicting" "$OUTPUT"
  assert_says "named no rule" "$OUTPUT"
  assert_says "outcome=refused" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  [ -n "$(git -C "$WORKTREE" diff --name-only --diff-filter=U)" ] \
    || fail "the conflict was not left standing to be read"
}

case_a_resolution_that_drops_the_ticket_s_change_is_caught() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  # During a rebase "ours" is the new base, so this takes the other side wholesale.
  stub_session 'git checkout --ours -- "$f"; git add "$f"'
  given_a_project
  given_a_conflict_beside_other_work 166 164
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 1 "$STATUS"
  assert_says "dropped" "$OUTPUT"
  assert_says "shared.txt" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_conflict_with_no_session_named_is_left_standing() {
  stub dotnet
  stub npm
  stub claude
  given_a_project
  given_a_conflict 166 164
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 166

  assert_status 1 "$STATUS"
  assert_says "rebase --abort" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
  ! called claude || fail "a session was started with no id to resume"
}

case_a_ticket_whose_closing_comment_cannot_be_read_is_still_named() {
  stub dotnet
  stub npm
  stub_failure gh
  stub_session 'printf "start\ntheir line\nmy line\n" > "$f"; git add "$f"'
  given_a_project
  given_a_conflict 166 164

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 0 "$STATUS"
  assert_says "#164" "$(calls)"
  # A silent tracker is not a ticket with nothing to say, and a refusal turns on which it was.
  assert_says "would not answer for #164" "$(calls)"
}

case_a_ticket_closed_with_no_comment_is_still_named() {
  stub dotnet
  stub npm
  stub gh
  stub_session 'printf "start\ntheir line\nmy line\n" > "$f"; git add "$f"'
  given_a_project
  given_a_conflict 166 164

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 0 "$STATUS"
  assert_says "#164" "$(calls)"
  assert_says "closed with no comment" "$(calls)"
}

case_a_marker_staged_behind_a_clean_working_file_is_caught() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  # The marker reaches the index and never the working tree, so only the index shows it.
  stub_session 'printf "<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> them\n" > "$f"; git add "$f"; printf "clean\n" > "$f"'
  given_a_project
  given_a_conflict 166 164
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 1 "$STATUS"
  assert_says "conflict marker" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_later_commit_that_conflicts_too_stops_with_its_own_reason() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  # A resolution that keeps neither side leaves the next commit nothing to apply to.
  stub_session 'printf "resolved\n" > "$f"; git add "$f"'
  given_a_project
  given_the_other_side_changed 164
  write_commit "$WORKTREE" shared.txt "my line" \
    "$(printf 'Do the first half\n\nTicket: #166')"
  write_commit "$WORKTREE" shared.txt "my second line" \
    "$(printf 'Do the second half\n\nTicket: #166')"
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 1 "$STATUS"
  assert_says "a later commit of its own conflicted" "$OUTPUT"
  # Two conflicts were met, so two are recorded, and neither was proved good.
  assert_eq "conflicts recorded" 2 "$(printf '%s\n' "$OUTPUT" | grep -c 'conflict #166')"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

case_a_conflict_marker_in_a_crlf_file_is_caught() {
  stub dotnet
  stub npm
  stub_saying gh "What that ticket set out to do."
  # Only the middle marker is left, so the carriage return is what the check must see past.
  stub_session 'printf "mine\r\n=======\r\ntheirs\r\n" > "$f"; git add "$f"'
  given_a_project
  given_a_conflict 166 164
  local base
  base=$(git -C "$ORIGIN" rev-parse main)

  run_script "$SCRIPT" "$WORKTREE" 166 session-abc

  assert_status 1 "$STATUS"
  assert_says "conflict marker" "$OUTPUT"
  assert_eq "the remote's main" "$base" "$(git -C "$ORIGIN" rev-parse main)"
}

run_cases
