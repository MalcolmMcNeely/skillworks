#!/usr/bin/env bash
#
# Drive one spec's tickets to done, sequentially, one fresh Claude session each.
# Commits per ticket, pushes once at the end.
#
#   scripts/spec-loop.sh <spec-issue-number> [--dry-run]
#
# The script picks the next ticket. The model never picks. Control flow lives
# here so a run is inspectable, stoppable and resumable.
#
# A model can skip a step a skill asks for, so each step is its own call here.
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

  # Git Bash would pass "/comment-sweep" to claude as "C:/Program Files/Git/comment-sweep".
  claude_p() {
    MSYS_NO_PATHCONV=1 env -u CLAUDECODE claude -p "$@" \
      --permission-mode "$PERMISSION_MODE" \
      --output-format json
  }

  run_step() {
    local ticket="$1" step="$2" out
    shift 2
    out=$(step_log "$ticket" "$step")
    say "STEP  #$ticket $step"
    claude_p "$(step_prompt "$ticket" "$step")" "$@" >"$out.json" 2>"$out.err" \
      || die "FAIL  #$ticket step $step exited non-zero. See $out.err and $out.json"
  }

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
  gh auth status >/dev/null 2>&1 || die "ABORT gh is not authenticated. Run: gh auth login"

  REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
  ME=$(gh api user --jq .login)

  spec_state=$(gh api "repos/$REPO/issues/$SPEC" --jq .state) \
    || die "ABORT cannot read $REPO#$SPEC"
  spec_title=$(gh api "repos/$REPO/issues/$SPEC" --jq .title)
  [ "$spec_state" = "open" ] || die "ABORT spec #$SPEC is $spec_state. The loop needs it open."

  ticket_count=$(gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" --jq 'length' | head -1)
  [ "${ticket_count:-0}" -gt 0 ] || die "ABORT spec #$SPEC has no sub-issues. Run /to-tickets first."

  # --- working tree ---------------------------------------------------------

  # This repo commits straight to main. No branch, no PR. See CLAUDE.md.
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  [ "$BRANCH" = "main" ] || die "ABORT on branch '$BRANCH'. This repo works on main."

  [ -z "$(git status --porcelain)" ] || die "ABORT working tree is dirty. Commit or stash first."

  if [ "$DRY_RUN" = "1" ]; then
    say "DRY   repo=$REPO  me=$ME  branch=$BRANCH"
    say "DRY   spec #$SPEC: $spec_title"
    gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" \
      --jq '.[] | "\(.number)\t\(.state)\t\(.title)"' |
      while IFS=$'\t' read -r n state title; do
        printf '  #%s [%s] %s\n' "$n" "$state" "$title"
        [ "$state" = "open" ] || continue
        printf '      build   claude -p "%s"\n' "$(step_prompt "$n" build)"
        printf '      sweep   claude -p "%s" --resume <build session>\n' "$(step_prompt "$n" sweep)"
        printf '      finish  claude -p "%s" --resume <build session>\n' "$(step_prompt "$n" finish)"
      done | tee -a "$LOG"
    say "DRY   no sessions were run"
    exit 0
  fi

  # Behind the remote, the push at the end fails after the sessions spent money.
  git pull --ff-only origin main

  # The drift check needs the commit this loop started from. Written once, so a
  # resumed run still measures against the original starting point.
  BASE_FILE="$LOG_DIR/base.sha"
  [ -f "$BASE_FILE" ] || git rev-parse HEAD > "$BASE_FILE"
  BASE=$(cat "$BASE_FILE")

  say "LOOP  spec #$SPEC on $BRANCH from $BASE ($REPO)"

  # --- the loop -------------------------------------------------------------

  while :; do
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
    done < <(gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" \
               --jq '.[] | select(.state=="open") | .number')

    if [ -z "$next" ]; then
      remaining=$(gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" \
        --jq '[.[] | select(.state=="open")] | length' | head -1)
      [ "${remaining:-0}" -eq 0 ] && break
      die "STUCK $remaining ticket(s) still open but none are startable (blocked, or claimed by someone else)."
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

    say "START #$next $title"

    run_step "$next" build
    build_json=$(step_log "$next" build).json
    # Git Bash has no jq.
    session=$(grep -oE '"session_id" *: *"[0-9a-f-]+"' "$build_json" \
                | head -1 | grep -oE '[0-9a-f-]{36}') \
      || die "FAIL  #$next step build gave no session id. See $build_json"
    run_step "$next" sweep --resume "$session"
    run_step "$next" finish --resume "$session"

    if [ -n "$(git status --porcelain)" ]; then
      die "FAIL  #$next left uncommitted changes. See git status."
    fi

    state=$(gh api "repos/$REPO/issues/$next" --jq .state)
    if [ "$state" != "closed" ]; then
      die "FAIL  #$next still open after step finish. Tests probably failed."
    fi

    # No push here. The loop pushes once at the end, so a half-finished spec
    # never reaches the remote.
    say "DONE  #$next  $(git rev-parse --short HEAD)"
  done

  # --- drift check ----------------------------------------------------------

  say "DRIFT all tickets closed. Checking the result against spec #$SPEC."
  claude_p "/spec-drift $SPEC $BASE" >"$LOG_DIR/drift.json" 2>"$LOG_DIR/drift.err" \
    || say "WARN  drift check exited non-zero. See $LOG_DIR/drift.err"

  if [ -n "$(git status --porcelain)" ]; then
    die "FAIL  drift check left uncommitted changes. See git status."
  fi
  # The one push. Everything up to here stayed local, so a failed loop leaves
  # the remote untouched and a "git reset --hard $BASE" undoes the lot.
  git push origin "$BRANCH"

  say "END   spec #$SPEC complete and pushed to $BRANCH."
  say "      Review it with: git log --oneline $BASE..HEAD"
}

# Bash reads a script while it runs it, so an edit mid-run changes what runs next.
main "$@"; exit
