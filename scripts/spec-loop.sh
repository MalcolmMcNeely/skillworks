#!/usr/bin/env bash
#
# Drive one spec's tickets to done, sequentially, one fresh Claude session each.
#
#   scripts/spec-loop.sh <spec-issue-number> [--dry-run]
#
# The script picks the next ticket. The model never picks. Control flow lives
# here so a run is inspectable, stoppable and resumable.
#
# Env:
#   SPEC_LOOP_PERMISSION_MODE   passed to `claude -p` (default: acceptEdits)
#
# Written against gh 2.92.0, which has no dependency flags. Everything goes
# through `gh api`. See docs/research/harness/ticket-state-guardrails.md.

set -euo pipefail

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
say() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG"; }
die() { say "$*"; exit 1; }

# --- preflight --------------------------------------------------------------

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

# --- branch -----------------------------------------------------------------

slug=$(printf '%s' "$spec_title" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -e 's/^spec:[[:space:]]*//' -e 's/[^a-z0-9]\+/-/g' -e 's/^-//' -e 's/-$//' \
  | cut -c1-40 | sed -e 's/-$//')
BRANCH="spec/$SPEC-$slug"

[ -z "$(git status --porcelain)" ] || die "ABORT working tree is dirty. Commit or stash first."

if [ "$DRY_RUN" = "1" ]; then
  say "DRY   repo=$REPO  me=$ME  branch=$BRANCH"
  say "DRY   spec #$SPEC: $spec_title"
  gh api --paginate "repos/$REPO/issues/$SPEC/sub_issues" \
    --jq '.[] | "  #\(.number) [\(.state)] \(.title)"' | tee -a "$LOG"
  say "DRY   no sessions were run"
  exit 0
fi

if git rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH"
fi
git push -u origin "$BRANCH" 2>/dev/null || git push origin "$BRANCH"

say "LOOP  spec #$SPEC on $BRANCH ($REPO)"

# --- the loop ---------------------------------------------------------------

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

  if ! env -u CLAUDECODE claude -p "/implement $next" \
        --permission-mode "$PERMISSION_MODE" \
        --output-format json \
        >"$LOG_DIR/ticket-$next.json" 2>"$LOG_DIR/ticket-$next.err"; then
    die "FAIL  #$next session exited non-zero. See $LOG_DIR/ticket-$next.err"
  fi

  if [ -n "$(git status --porcelain)" ]; then
    die "FAIL  #$next left uncommitted changes. See git status."
  fi

  state=$(gh api "repos/$REPO/issues/$next" --jq .state)
  if [ "$state" != "closed" ]; then
    die "FAIL  #$next still open after /implement. Tests probably failed."
  fi

  git push origin "$BRANCH"
  say "DONE  #$next"
done

# --- drift check ------------------------------------------------------------

say "DRIFT all tickets closed. Checking the result against spec #$SPEC."
env -u CLAUDECODE claude -p "/spec-drift $SPEC" \
  --permission-mode "$PERMISSION_MODE" \
  --output-format json \
  >"$LOG_DIR/drift.json" 2>"$LOG_DIR/drift.err" \
  || say "WARN  drift check exited non-zero. See $LOG_DIR/drift.err"

if [ -n "$(git status --porcelain)" ]; then
  die "FAIL  drift check left uncommitted changes. See git status."
fi
git push origin "$BRANCH"

say "END   spec #$SPEC complete on $BRANCH"
say "      gh pr create --base main --head $BRANCH --title \"$spec_title\" --body \"Closes #$SPEC\""
