#!/usr/bin/env bash
#
# The spec loop's plan and its steps, read against a throwaway repository.

. "$(dirname "${BASH_SOURCE[0]}")/harness.sh"

SCRIPT=scripts/spec-loop.sh

ONE_OPEN_TICKET=$'168\topen\tTICKET: The dry run prints the plan'
ONE_CLOSED_TICKET=$'161\tclosed\tTICKET: Already done'

# The dry run puts its log where it is run, so it is run in the throwaway repository.
# A session is looked for under this case's own folder, so no real one can answer a check here.
run_loop() {  # <args...>
  OUTPUT=$(cd "$WORKTREE" && CLAUDE_CONFIG_DIR="$TMP/claude" bash "$ROOT/$SCRIPT" "$@" 2>&1)
  STATUS=$?
}

# Every answer the loop asks for and no others, so an unplanned call fails rather than guesses.
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
  "issue edit"*)                                        exit 0 ;;
  *blocked_by*)                                         echo 0 ;;
  *assignees*)                                          echo "" ;;
  *"--jq .state")                                       echo open ;;
  *"--jq .title")                                       echo "SPEC: A spec to plan" ;;
  *sub_issues*".[].number")                             cut -f1 "$TICKETS" ;;
  *sub_issues*'select(.state=="open")'*)                awk -F'\t' '$2=="open"{print $1}' "$TICKETS" ;;
  *sub_issues*)                                         cat "$TICKETS" ;;
  *) echo "the gh stub has no answer for: $*" >&2;      exit 1 ;;
esac
STUB
}

# The step names in the order the plan prints them, so a case reads the order and not just the set.
planned_steps() {
  printf '%s\n' "$OUTPUT" | awk '/claude -p/ { printf "%s ", $1 }'
}

planned_call() {  # <step>
  printf '%s\n' "$OUTPUT" | awk -v step="$1" '$1 == step && /claude -p/ { print; exit }'
}

# The checks sit on the line under the call they belong to, so a case reads the pair.
planned_checks() {  # <step>
  printf '%s\n' "$OUTPUT" | awk -v step="$1" '
    $1 == step && /claude -p/ { under = 1; next }
    under                     { sub(/^ *checks: /, ""); print; exit }'
}

case_the_dry_run_prints_the_worktree_and_the_branch() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_says "$WORKTREE/.claude/worktrees/spec-158/ticket-168" "$OUTPUT"
  assert_says "spec-loop/158/ticket-168" "$OUTPUT"
}

case_the_dry_run_prints_every_landing_step_with_its_checks() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  # Written out, so a step the landing script renames, drops or reorders fails here
  # rather than moving both sides of the comparison together.
  assert_says "the worktree, its tree and the trailer on its commit" "$OUTPUT"
  assert_says "checks: is-a-worktree tree-clean ticket-named" "$OUTPUT"
  assert_says "git fetch origin (up to 5 attempts)" "$OUTPUT"
  assert_says "checks: origin-has-main something-to-land" "$OUTPUT"
  assert_says "git rebase origin/main, when the base has moved" "$OUTPUT"
  assert_says "checks: commits-kept files-kept" "$OUTPUT"
  assert_says "the build session, when the rebase conflicts" "$OUTPUT"
  assert_says "checks: session-named no-refusal none-left-conflicting no-marker-staged rebase-carried-on" "$OUTPUT"
  assert_says "the whole suite, when the base has moved" "$OUTPUT"
  assert_says "checks: suite-green" "$OUTPUT"
  assert_says "git push origin HEAD:main" "$OUTPUT"
  assert_says "checks: pushed (up to 3 attempts)" "$OUTPUT"
}

case_the_dry_run_still_prints_the_sessions_it_would_start() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_says '/implement 168 --stop-after-tests' "$OUTPUT"
  assert_says '/implement 168 --fix' "$OUTPUT"
  assert_says '/comment-sweep' "$OUTPUT"
  assert_says '/implement 168 --finish' "$OUTPUT"
  assert_says 'checks: no-error command-loaded ticket-open tree-changed' "$OUTPUT"
  assert_says 'checks: no-error command-loaded new-commit tree-clean ticket-closed' "$OUTPUT"
}

case_the_dry_run_prints_all_seven_steps_in_order() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_says '/review-standards 168' "$OUTPUT"
  assert_says '/review-spec 168' "$OUTPUT"
  assert_says '/review-architecture 168' "$OUTPUT"
  assert_eq "the order of the steps" \
    "build standards spec architecture fix sweep finish " "$(planned_steps)"
}

case_the_dry_run_gives_every_review_step_the_same_checks() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  local axis
  for axis in standards spec architecture; do
    assert_eq "the checks on the $axis step" \
      "no-error command-loaded ticket-open axis-reported" "$(planned_checks "$axis")"
  done
}

# Read off the plan rather than written out, so the two move together or this case fails.
case_the_dry_run_gives_the_reconciling_step_the_checks_the_sweep_has() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  assert_eq "the checks on the fix step" "$(planned_checks sweep)" "$(planned_checks fix)"
  assert_eq "the checks on the sweep step" \
    "no-error command-loaded ticket-open" "$(planned_checks sweep)"
}

case_the_dry_run_resumes_the_build_session_for_the_fix_and_the_finish_alone() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"

  run_loop 158 --dry-run

  assert_status 0 "$STATUS"
  local step
  for step in build standards spec architecture sweep; do
    case "$(planned_call "$step")" in
      *--resume*) fail "the $step step would resume a session" ;;
    esac
  done
  for step in fix finish; do
    assert_says '--resume <build session>' "$(planned_call "$step")"
  done
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

# One closed ticket takes the run past the loop body, so the restart is what these cases read.
leftover() { printf '%s/.claude/worktrees/spec-158/ticket-164' "$WORKTREE"; }

given_a_leftover_worktree() {  # <job>
  uv run "$ROOT/scripts/ticket_worktree.py" open "$WORKTREE" 158 "$1" >/dev/null 2>&1
}

case_a_restart_over_a_leftover_holding_work_carries_on() {
  given_the_tracker_holds "$ONE_CLOSED_TICKET"
  given_a_leftover_worktree ticket-164
  printf 'half done\n' > "$(leftover)/loose.txt"

  run_loop 158

  assert_status 0 "$STATUS"
  assert_says "END   spec #158" "$OUTPUT"
  assert_says "uncommitted work" "$OUTPUT"
  [ ! -e "$(leftover)" ] || fail "the leftover worktree is still there"
  git -C "$WORKTREE" cat-file -e spec-loop/158/ticket-164-kept-1:loose.txt 2>/dev/null \
    || fail "the uncommitted work is not on the kept branch"
}

case_a_restart_over_a_leftover_holding_nothing_carries_on() {
  given_the_tracker_holds "$ONE_CLOSED_TICKET"
  given_a_leftover_worktree ticket-164

  run_loop 158

  assert_status 0 "$STATUS"
  assert_says "END   spec #158" "$OUTPUT"
  assert_says "nothing uncommitted" "$OUTPUT"
  [ ! -e "$(leftover)" ] || fail "the leftover worktree is still there"
  git -C "$WORKTREE" rev-parse --verify --quiet refs/heads/spec-loop/158/ticket-164-kept-1 \
    >/dev/null || fail "the kept branch is not there"
}

case_the_log_names_the_job_and_the_branch_a_leftover_was_kept_on() {
  given_the_tracker_holds "$ONE_CLOSED_TICKET"
  given_a_leftover_worktree ticket-164

  run_loop 158

  assert_status 0 "$STATUS"
  local log
  log=$(cat "$WORKTREE/.spec-loop/158/loop.log")
  assert_says "ticket-164" "$log"
  assert_says "spec-loop/158/ticket-164-kept-1" "$log"
}

# An open ticket, so a run that failed to stop would start a session and say so.
case_a_keep_that_fails_part_way_still_names_the_job_it_kept() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_a_leftover_worktree ticket-164
  given_a_leftover_worktree ticket-165
  refuse_keeping 158 ticket-165

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "KEPT  ticket-164" "$OUTPUT"
  assert_says "spec-loop/158/ticket-164-kept-1" "$OUTPUT"
  assert_says "Nothing was started" "$OUTPUT"
  ! called claude || fail "a session was started"
}

case_the_log_names_a_job_kept_before_a_keep_failed() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_a_leftover_worktree ticket-164
  given_a_leftover_worktree ticket-165
  refuse_keeping 158 ticket-165

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "spec-loop/158/ticket-164-kept-1" "$(cat "$WORKTREE/.spec-loop/158/loop.log")"
}

case_the_log_holds_the_reason_a_keep_failed() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_a_leftover_worktree ticket-164
  given_a_leftover_worktree ticket-165
  refuse_keeping 158 ticket-165

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "would not rename branch spec-loop/158/ticket-165" \
    "$(cat "$WORKTREE/.spec-loop/158/loop.log")"
}

case_a_keep_that_succeeded_says_what_it_left_alone() {
  given_the_tracker_holds "$ONE_CLOSED_TICKET"
  local stray
  stray="$WORKTREE/.claude/worktrees/spec-158/stray"
  mkdir -p "$stray"
  printf 'notes\n' > "$stray/notes.txt"

  run_loop 158

  assert_status 0 "$STATUS"
  assert_says "$stray is no worktree of its own, so it was left where it is" \
    "$(cat "$WORKTREE/.spec-loop/158/loop.log")"
}

# --- the review steps, run for real -----------------------------------------

# given_the_tracker_holds stubs the node the checks need, so the real one goes back on PATH here.
given_sessions_that_report() {
  rm -f "$STUBS/node"
  mkdir -p "$TMP/said" "$TMP/refused" "$TMP/lost" "$TMP/claude/projects/one"
  stub claude
  printf 'SAID="%s"\nREFUSED="%s"\nLOST="%s"\nSESSIONS="%s"\n' \
    "$TMP/said" "$TMP/refused" "$TMP/lost" "$TMP/claude/projects/one" >> "$STUBS/claude"
  cat >> "$STUBS/claude" <<'STUB'
for arg in "$@"; do
  case "$arg" in /*) prompt=$arg; break ;; esac
done
name=${prompt%% *}
args=${prompt#"$name"}
step=${name#/}
[ ! -f "$REFUSED/$step" ] || { echo "the $step session was turned down" >&2; exit 1; }
[ ! -f "$LOST/$step" ] || rm -f "$(cat "$LOST/$step")"
count=$(( $(cat "$SESSIONS/count" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$SESSIONS/count"
session="session-$count"
MSYS_NO_PATHCONV=1 node -e '
  const fs = require("fs")
  const [file, name, args] = process.argv.slice(1)
  fs.writeFileSync(file, JSON.stringify({ type: "user", message: {
    content: `<command-name>${name}</command-name><command-args>${args}</command-args>`,
  } }) + "\n")' "$SESSIONS/$session.jsonl" "$name" "${args# }"
case "$step" in
  review-standards)    said="## Standards. Nothing found." ;;
  review-spec)         said="## Spec. Nothing found." ;;
  review-architecture) said="## Architecture. Nothing found." ;;
  *)                   said="did the $step" ;;
esac
[ ! -f "$SAID/$step" ] || said=$(cat "$SAID/$step")
case "$prompt" in *--stop-after-tests) printf 'built\n' >> built.txt ;; esac
printf '{"is_error":false,"session_id":"%s","result":"%s"}\n' "$session" "$said"
STUB
}

given_an_axis_that_says() {  # <axis> <what its turn ends with>
  printf '%s' "$2" > "$TMP/said/review-$1"
}

given_an_axis_that_errors() {  # <axis>
  : > "$TMP/refused/review-$1"
}

# The step's own check reads the report as well, so only the axis after it can take it away.
given_a_report_lost_after_the_last_axis() {  # <axis>
  printf '%s/.spec-loop/158/ticket-168-%s.json\n' "$WORKTREE" "$1" \
    > "$TMP/lost/review-architecture"
}

session_call() {  # <prompt>
  calls | grep -F -- "$1" | head -1
}

# A prompt carrying the reports runs over many lines, so the next session's call is what ends it.
step_call() {  # <the first line of the call>
  calls | awk -v marker="$1" '
    index($0, marker) == 1        { found = 1 }
    found && shown && index($0, "claude -p ") == 1 { exit }
    found                         { shown = 1; print }'
}

fix_prompt() { step_call "claude -p /implement 168 --fix"; }

finish_prompt() { step_call "claude -p /implement 168 --finish"; }

ticket_worktree() { printf '%s/.claude/worktrees/spec-158/ticket-168' "$WORKTREE"; }

# The finish step cannot pass its checks here, so the loop stops with all three axes on record.
# All four read the change cold: no axis reads another's mind, and the sweep sees the whole ticket.
case_the_review_steps_and_the_sweep_are_given_sessions_that_resume_nothing() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report

  run_loop 158

  assert_status 1 "$STATUS"
  local prompt
  for prompt in "/review-standards 168" "/review-spec 168" "/review-architecture 168" \
    "/comment-sweep"; do
    assert_says "$prompt" "$(calls)"
    case "$(session_call "$prompt")" in
      *--resume*) fail "$prompt resumed a session" ;;
    esac
  done
}

implement_flags() {
  calls | sed -n 's|^claude -p /implement 168 \(--[a-z-]*\).*|\1|p'
}

case_the_reconciling_step_and_the_finishing_step_each_run_under_their_own_flag() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report

  run_loop 158

  assert_status 1 "$STATUS"
  assert_eq "the flags the /implement steps ran under" \
    "$(printf -- '--stop-after-tests\n--fix\n--finish')" "$(implement_flags)"
}

case_a_review_step_that_reported_nothing_stops_the_loop() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_an_axis_that_says standards "I have finished looking."

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "step standards failed check axis-reported" "$OUTPUT"
  case "$(calls)" in
    *"/review-spec"*) fail "the loop carried on past an axis that reported nothing" ;;
  esac
}

case_a_review_step_that_reported_no_findings_passes_its_check() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_an_axis_that_says standards "## Standards. No findings on this change."

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "/review-spec 168" "$(calls)"
  case "$OUTPUT" in
    *"step standards failed"*) fail "an axis that said it found nothing was failed" ;;
  esac
}

case_a_review_step_that_errored_stops_the_loop_and_keeps_the_worktree() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_an_axis_that_errors spec

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "step spec exited non-zero" "$OUTPUT"
  assert_says "$(ticket_worktree)" "$OUTPUT"
  [ -d "$(ticket_worktree)" ] || fail "the worktree of the stopped ticket was thrown away"
  case "$(calls)" in
    *"/implement 168 --fix"*) fail "the loop went on to reconcile the ticket" ;;
  esac
  case "$(calls)" in
    *"/implement 168 --finish"*) fail "the loop went on to finish the ticket" ;;
  esac
}

# --- the reports reaching the reconciling step ------------------------------

given_three_axes_with_something_to_say() {
  given_an_axis_that_says standards "## Standards. The name box says nothing."
  given_an_axis_that_says spec "## Spec. The third criterion is unmet."
  given_an_axis_that_says architecture "## Architecture. The arrow points the wrong way."
}

case_the_reconciling_step_is_given_what_all_three_axes_found() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_three_axes_with_something_to_say

  run_loop 158

  assert_status 1 "$STATUS"
  local prompt
  prompt=$(fix_prompt)
  assert_says "The name box says nothing." "$prompt"
  assert_says "The third criterion is unmet." "$prompt"
  assert_says "The arrow points the wrong way." "$prompt"
}

case_the_reconciling_step_is_told_which_axis_each_report_came_from() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_three_axes_with_something_to_say

  run_loop 158

  assert_status 1 "$STATUS"
  local axis
  for axis in standards spec architecture; do
    assert_says "## The $axis axis reported" "$(fix_prompt)"
  done
}

# The reports stop at the step that reconciles, so carrying them on would be the same work twice.
case_the_finishing_step_is_given_no_axis_report() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_three_axes_with_something_to_say

  run_loop 158

  assert_status 1 "$STATUS"
  case "$(finish_prompt)" in
    *"axis reported"*) fail "the finishing step was given the reports again" ;;
  esac
}

case_the_reconciling_step_and_the_finishing_step_both_resume_the_build_session() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "--resume session-1" "$(fix_prompt)"
  assert_says "--resume session-1" "$(finish_prompt)"
}

case_a_missing_axis_report_stops_the_loop_before_the_reconciling_step() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_a_report_lost_after_the_last_axis standards

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "step fix was short of a review axis report" "$OUTPUT"
  case "$(calls)" in
    *"/implement 168 --fix"*) fail "the reconciling step ran on two axes out of three" ;;
  esac
}

case_a_missing_axis_report_names_the_axis_it_came_from() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report
  given_a_report_lost_after_the_last_axis standards

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "the standards axis left no report" \
    "$(cat "$WORKTREE/.spec-loop/158/ticket-168-fix.err")"
}

# --- the way past a refused write -------------------------------------------

# A session that met the wall leaves the ticket open, so any stop the loop makes may be that wall.
case_a_ticket_left_open_is_told_the_way_past_the_wall() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "SPEC_LOOP_PERMISSION_MODE=bypassPermissions" "$OUTPUT"
  assert_says "$(ticket_worktree)" "$OUTPUT"
}

case_the_way_past_the_wall_reaches_the_log_as_well() {
  given_the_tracker_holds "$ONE_OPEN_TICKET"
  given_sessions_that_report

  run_loop 158

  assert_status 1 "$STATUS"
  assert_says "SPEC_LOOP_PERMISSION_MODE=bypassPermissions" \
    "$(cat "$WORKTREE/.spec-loop/158/loop.log")"
}

case_a_keep_that_left_nothing_alone_says_nothing() {
  given_the_tracker_holds "$ONE_CLOSED_TICKET"
  given_a_leftover_worktree ticket-164

  run_loop 158

  assert_status 0 "$STATUS"
  case "$OUTPUT" in
    *WARN*|*"left where it is"*) fail "a keep with nothing to leave alone still warned" ;;
  esac
}

run_cases
