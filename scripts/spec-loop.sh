#!/usr/bin/env bash
#
# Drive one spec's tickets to done, sequentially, one fresh Claude session each.
# Each ticket is built in a throwaway worktree of its own, cut from the newest
# origin/main, and lands on the remote the moment it passes. The main checkout
# is never worked in, so it stays usable for the whole run.
#
#   scripts/spec-loop.sh <spec-issue-number> [--dry-run]
#
# The script picks the next ticket. The model never picks. Control flow lives
# here so a run is inspectable, stoppable and resumable.
#
# A model can skip a step a skill asks for, so each step is its own call here.
# A step can exit 0 and do nothing, so the script checks facts after each one.
#
# Env:
#   SPEC_LOOP_PERMISSION_MODE   passed to `claude -p` (default: acceptEdits)
#
# Written against gh 2.92.0, which has no dependency flags. Everything goes
# through `gh api`. See docs/research/harness/ticket-state-guardrails.md.

main() {
  set -euo pipefail

  say() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG"; }
  die() { say "$*"; exit 1; }

  step_log() { printf '%s/ticket-%s-%s' "$LOG_DIR" "$1" "$2"; }

  step_prompt() {
    case "$2" in
      build)  printf '/implement %s --stop-after-tests' "$1" ;;
      sweep)  printf '/comment-sweep' ;;
      finish) printf '/implement %s --finish' "$1" ;;
    esac
  }

  step_checks() {
    case "$1" in
      build)  printf 'no-error command-loaded ticket-open tree-changed' ;;
      sweep)  printf 'no-error command-loaded ticket-open' ;;
      finish) printf 'no-error command-loaded new-commit tree-clean ticket-closed' ;;
    esac
  }

  # The ticket now running counts as remaining, so the estimate never flatters the run.
  progress_suffix() {
    local position="$1" total="$2" mean="${3:-}" remaining
    printf '%s/%s' "$position" "$total"
    [ -n "$mean" ] || return 0
    remaining=$(( total - position + 1 ))
    printf '  ~%sm left' "$(( (mean * remaining + 30) / 60 ))"
  }

  # Git Bash would pass "/comment-sweep" to claude as "C:/Program Files/Git/comment-sweep".
  claude_p() {
    ( cd "$JOB_WORKTREE" \
      && MSYS_NO_PATHCONV=1 env -u CLAUDECODE claude -p "$@" \
        --permission-mode "$PERMISSION_MODE" \
        --output-format json )
  }

  # Git Bash has no jq. Path conversion would also rewrite "/implement" here.
  node_e() { MSYS_NO_PATHCONV=1 node -e "$@"; }

  json_field() {
    node_e '
      const [file, field] = process.argv.slice(1)
      console.log(JSON.parse(require("fs").readFileSync(file, "utf8"))[field] ?? "")' "$1" "$2"
  }

  # Only a user prompt counts, since a tool result can quote the command tags.
  command_loaded() {
    node_e '
      const fs = require("fs"), os = require("os"), path = require("path")
      const [session, command, args] = process.argv.slice(1)
      const projects = path.join(process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude"), "projects")
      const transcript = fs.readdirSync(projects)
        .map(folder => path.join(projects, folder, `${session}.jsonl`))
        .find(file => fs.existsSync(file))
      if (!transcript) {
        console.error(`No transcript for session "${session}" in ${projects}`)
        process.exit(1)
      }
      const loaded = fs.readFileSync(transcript, "utf8").split("\n").filter(Boolean)
        .map(line => JSON.parse(line))
        .some(entry => entry.type === "user" && typeof entry.message?.content === "string"
          && entry.message.content.includes(`<command-name>${command}</command-name>`)
          && (args === "" || entry.message.content.includes(`<command-args>${args}</command-args>`)))
      if (!loaded) console.error(`"${`${command} ${args}`.trim()}" did not load as a command in ${transcript}`)
      process.exit(loaded ? 0 : 1)' "$@"
  }

  issue_state() { gh api "repos/$REPO/issues/$1" --jq .state; }

  check_passes() {
    local ticket="$1" step="$2" check="$3" json="$4" command args
    case "$check" in
      no-error)      [ "$(json_field "$json" is_error)" = false ] ;;
      command-loaded)
        read -r command args <<<"$(step_prompt "$ticket" "$step")"
        command_loaded "$(json_field "$json" session_id)" "$command" "$args" ;;
      ticket-open)   [ "$(issue_state "$ticket")" = open ] ;;
      ticket-closed) [ "$(issue_state "$ticket")" = closed ] ;;
      tree-changed)  [ -n "$(git -C "$JOB_WORKTREE" status --porcelain)" ] ;;
      tree-clean)    [ -z "$(git -C "$JOB_WORKTREE" status --porcelain)" ] ;;
      new-commit)    [ "$(git -C "$JOB_WORKTREE" rev-parse HEAD)" != "$TICKET_BASE" ] ;;
      *)             return 1 ;;
    esac
  }

  # The loop picks only open tickets, so a rerun would skip a closed one.
  stop_step() {
    local ticket="$1" step="$2" reason="$3" log="$4"
    if [ "$(issue_state "$ticket")" = closed ]; then
      gh issue reopen "$ticket" >/dev/null \
        || say "WARN  #$ticket is closed and did not reopen. Reopen it by hand."
    fi
    die "FAIL  #$ticket step $step $reason. Its worktree is at $JOB_WORKTREE. See $log"
  }

  run_step() {
    local ticket="$1" step="$2" out check
    shift 2
    out=$(step_log "$ticket" "$step")
    say "$(printf 'STEP  #%s %-10s%s' \
      "$ticket" "$step" "$(progress_suffix "$POSITION" "$TICKET_COUNT" "$MEAN_SECONDS")")"
    claude_p "$(step_prompt "$ticket" "$step")" "$@" >"$out.json" 2>"$out.err" \
      || stop_step "$ticket" "$step" "exited non-zero" "$out.err and $out.json"
    for check in $(step_checks "$step"); do
      check_passes "$ticket" "$step" "$check" "$out.json" 2>>"$out.err" \
        || stop_step "$ticket" "$step" "failed check $check" "$out.json and $out.err"
    done
  }

  # A path comes back on stdout, so a reason has to take the other channel. It
  # goes to the log as well, because a background run has nobody at the terminal.
  worktree() {
    local err status=0
    err="$LOG_DIR/worktree.err"
    bash "$SCRIPTS/ticket-worktree.sh" "$1" "$ROOT" "$SPEC" "${2:-}" 2>"$err" || status=$?
    [ "$status" -eq 0 ] || tee -a "$LOG" <"$err" >&2
    return "$status"
  }

  # Found from this file, not from the working directory, because the working
  # directory is about to become whichever checkout the ticket is built in.
  SCRIPTS=$(cd "$(dirname "$0")" && pwd)

  SPEC="${1:-}"
  DRY_RUN=0
  [ "${2:-}" = "--dry-run" ] && DRY_RUN=1

  if [ -z "$SPEC" ]; then
    echo "usage: scripts/spec-loop.sh <spec-issue-number> [--dry-run]" >&2
    exit 64
  fi

  export GH_PROMPT_DISABLED=1
  PERMISSION_MODE="${SPEC_LOOP_PERMISSION_MODE:-acceptEdits}"

  LOG_DIR=".spec-loop/$SPEC"
  mkdir -p "$LOG_DIR"
  LOG="$LOG_DIR/loop.log"

  # --- preflight ------------------------------------------------------------

  command -v gh >/dev/null || die "ABORT gh is not installed"
  command -v claude >/dev/null || die "ABORT claude is not on PATH"
  command -v node >/dev/null || die "ABORT node is not on PATH"
  gh auth status >/dev/null 2>&1 || die "ABORT gh is not authenticated. Run: gh auth login"

  REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
  ME=$(gh api user --jq .login)

  spec_state=$(issue_state "$SPEC") \
    || die "ABORT cannot read $REPO#$SPEC"
  spec_title=$(gh api "repos/$REPO/issues/$SPEC" --jq .title)
  [ "$spec_state" = "open" ] || die "ABORT spec #$SPEC is $spec_state. The loop needs it open."

  # --paginate runs --jq once per page, so a length per page would count only
  # the first hundred. Counting the numbers themselves spans every page.
  TICKET_COUNT=$(gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" --jq '.[].number' | wc -l)
  [ "$TICKET_COUNT" -gt 0 ] || die "ABORT spec #$SPEC has no sub-issues. Run /to-tickets first."

  # --- the checkout the worktrees are cut from ------------------------------

  # No guard on the branch or on the edits: nothing is ever built in this checkout.
  ROOT=$(git rev-parse --show-toplevel)

  if [ "$DRY_RUN" = "1" ]; then
    say "DRY   repo=$REPO  me=$ME"
    say "DRY   spec #$SPEC: $spec_title"
    gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" \
      --jq '.[] | "\(.number)\t\(.state)\t\(.title)"' |
      while IFS=$'\t' read -r n state title; do
        printf '  #%s [%s] %s\n' "$n" "$state" "$title"
        [ "$state" = "open" ] || continue
        for step in build sweep finish; do
          printf '      %-7s claude -p "%s"' "$step" "$(step_prompt "$n" "$step")"
          [ "$step" = build ] || printf ' --resume <build session>'
          printf '\n              checks: %s\n' "$(step_checks "$step")"
        done
      done | tee -a "$LOG"
    say "DRY   no sessions were run"
    exit 0
  fi

  # A leftover group is work nobody has read yet, and not the driver's to throw away.
  worktree check || die "ABORT spec #$SPEC already has a worktree group. Nothing was started."

  # Every worktree is cut from origin/main, so the ref has to be current first.
  git fetch --quiet origin || die "ABORT could not fetch from origin"

  # The drift check needs the commit this loop started from. Written once, so a
  # resumed run still measures against the original starting point.
  BASE_FILE="$LOG_DIR/base.sha"
  [ -f "$BASE_FILE" ] || git rev-parse origin/main > "$BASE_FILE"
  BASE=$(cat "$BASE_FILE")

  say "LOOP  spec #$SPEC from $BASE ($REPO)"

  # --- the loop -------------------------------------------------------------

  # Nothing is read from an earlier run, so a rerun grows a mean of its own.
  TIMED_TICKETS=0
  TIMED_SECONDS=0
  MEAN_SECONDS=""

  while :; do
    open_tickets=$(gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" \
                     --jq '.[] | select(.state=="open") | .number')
    open_count=0
    [ -z "$open_tickets" ] || open_count=$(( $(printf '%s\n' "$open_tickets" | wc -l) ))

    next=""
    while read -r n; do
      [ -n "$n" ] || continue
      # blocked_by counts OPEN blockers only. See ticket-state-guardrails.md.
      blocked=$(gh api "repos/$REPO/issues/$n" \
        --jq '.issue_dependencies_summary.blocked_by // "missing"')
      case "$blocked" in
        0)          ;;
        ""|missing) die "ABORT #$n reports no issue_dependencies_summary. Refusing to guess." ;;
        *)          continue ;;
      esac
      others=$(gh api "repos/$REPO/issues/$n" \
        --jq "[.assignees[].login] | map(select(. != \"$ME\")) | join(\",\")")
      if [ -n "$others" ]; then continue; fi
      next="$n"
      break
    done <<<"$open_tickets"

    if [ -z "$next" ]; then
      [ "$open_count" -eq 0 ] && break
      die "STUCK $open_count ticket(s) still open but none are startable (blocked, or claimed by someone else)."
    fi

    title=$(gh api "repos/$REPO/issues/$next" --jq .title)

    # Claim, then read back. There is no compare-and-swap on the Issues API,
    # so this detects a race rather than preventing one.
    gh issue edit "$next" --add-assignee @me >/dev/null
    sleep 3
    others=$(gh api "repos/$REPO/issues/$next" \
      --jq "[.assignees[].login] | map(select(. != \"$ME\")) | join(\",\")")
    if [ -n "$others" ]; then
      gh issue edit "$next" --remove-assignee @me >/dev/null 2>&1 || true
      say "SKIP  #$next claimed by $others"
      continue
    fi

    # Counts closed tickets, not this run's, so a rerun starts at its real place.
    POSITION=$(( TICKET_COUNT - open_count + 1 ))

    say "START #$next $title"
    JOB_WORKTREE=$(worktree open "ticket-$next") \
      || die "FAIL  #$next got no worktree to be built in."
    TICKET_BASE=$(git -C "$JOB_WORKTREE" rev-parse HEAD)
    started=$(date -u +%s)

    run_step "$next" build
    build_json=$(step_log "$next" build).json
    session=$(json_field "$build_json" session_id) && [ -n "$session" ] \
      || die "FAIL  #$next step build gave no session id. See $build_json"
    run_step "$next" sweep --resume "$session"
    run_step "$next" finish --resume "$session"

    # Finished work on one machine only is work at the mercy of that machine.
    land_out=$(step_log "$next" land).out
    landed=0
    bash "$SCRIPTS/integrate-ticket.sh" "$JOB_WORKTREE" "$next" >"$land_out" 2>&1 || landed=$?
    say "$(cat "$land_out")"
    [ "$landed" -eq 0 ] \
      || die "FAIL  #$next did not reach main. Its worktree is at $JOB_WORKTREE. See $land_out"

    landed_at=$(git -C "$JOB_WORKTREE" rev-parse --short HEAD)

    # A ticket that failed never gets here, so a worktree left behind means a stop.
    worktree close "ticket-$next" \
      || die "FAIL  #$next landed, but its worktree at $JOB_WORKTREE would not go."

    # A skipped ticket never reaches here, so nobody else's work is in the mean.
    TIMED_SECONDS=$(( TIMED_SECONDS + $(date -u +%s) - started ))
    TIMED_TICKETS=$(( TIMED_TICKETS + 1 ))
    MEAN_SECONDS=$(( TIMED_SECONDS / TIMED_TICKETS ))

    say "DONE  #$next  $landed_at"
  done

  # --- drift check ----------------------------------------------------------

  say "DRIFT all tickets closed. Checking the result against spec #$SPEC."

  # The main checkout was never pulled, so only a fresh worktree holds the finished work.
  JOB_WORKTREE=$(worktree open drift) \
    || die "FAIL  the drift check got no worktree to run in."
  claude_p "/spec-drift $SPEC $BASE" >"$LOG_DIR/drift.json" 2>"$LOG_DIR/drift.err" \
    || say "WARN  drift check exited non-zero. See $LOG_DIR/drift.err"

  if [ -n "$(git -C "$JOB_WORKTREE" status --porcelain)" ]; then
    die "FAIL  drift check left uncommitted changes in $JOB_WORKTREE."
  fi
  worktree close drift || die "FAIL  the drift worktree at $JOB_WORKTREE would not go."

  say "END   spec #$SPEC complete. Every ticket is on main."
  say "      Review it with: git log --oneline $BASE..origin/main"
}

# Bash reads a script while it runs it, so an edit mid-run changes what runs next.
main "$@"; exit
