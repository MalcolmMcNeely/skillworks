#!/usr/bin/env bash
#
# Check this repo can run the Skillworks loop, then create the label it needs.
#
#   bash scripts/skillworks-preflight.sh [--check-only]
#
# Idempotent. Run it again any time to repair.

set -euo pipefail

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1 ;;
    *) printf "usage: skillworks-preflight.sh [--check-only]\n" >&2; exit 64 ;;
  esac
done

export GH_PROMPT_DISABLED=1
ok() { printf 'ok    %s\n' "$*"; }
warn() { printf 'warn  %s\n' "$*"; }
die() { printf 'FAIL  %s\n' "$*" >&2; exit 1; }

# --- checks -----------------------------------------------------------------

command -v git >/dev/null || die "git is not installed"
command -v gh >/dev/null || die "gh is not installed. https://cli.github.com"
command -v claude >/dev/null || die "claude is not on PATH. The loop shells out to it."

gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"
ok "gh authenticated as $(gh api user --jq .login)"

git rev-parse --git-dir >/dev/null 2>&1 || die "not inside a git repository"

origin=$(git remote get-url origin 2>/dev/null || true)
[ -n "$origin" ] || die "no 'origin' remote. Skillworks tracks work on GitHub."
case "$origin" in
  *github.com*) ;;
  *) die "origin is not GitHub: $origin. Skillworks is GitHub only." ;;
esac

REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
ok "repo $REPO"

# Dependency reads work on any gh, because everything goes through `gh api`.
# The convenience flags landed in 2.94.0; say so, but do not block.
ghver=$(gh --version | head -1 | awk '{print $3}')
lowest=$(printf '%s\n2.94.0\n' "$ghver" | sort -V | head -1)
if [ "$lowest" != "2.94.0" ]; then
  warn "gh $ghver has no --add-blocked-by / --add-sub-issue flags (2.94.0+). Everything here uses 'gh api', so this is fine."
else
  ok "gh $ghver"
fi

claudever=$(claude --version | awk '{print $1}')
lowest=$(printf '%s\n2.1.242\n' "$claudever" | sort -V | head -1)
if [ "$lowest" != "2.1.242" ]; then
  warn "claude $claudever predates 2.1.242, so promptCacheTtl in .claude/settings.json is ignored. Each ticket will pay a cold prompt cache."
else
  ok "claude $claudever"
fi

# Native issue dependencies must be readable, or the loop cannot tell what is blocked.
probe=$(gh api "repos/$REPO" --jq .has_issues)
[ "$probe" = "true" ] || die "Issues are disabled on $REPO. Enable them in repo settings."
ok "issues enabled"

if [ "$CHECK_ONLY" = "1" ]; then
  ok "check-only: no labels were written"
  exit 0
fi

# --- labels -----------------------------------------------------------------
#
# Nothing in the loop READS a label. The driver finds work by sub-issue
# parentage, blocked_by and assignee. One label exists only because /to-spec
# and /to-tickets APPLY it, and `gh issue create` fails on a label that is
# not there.

# Create if missing. Never overwrite one that exists - the colour or wording
# may be deliberate. To repair a label, delete it and run this again.
label() {
  if gh label list --limit 200 --json name --jq ".[].name" | grep -qx "$1"; then
    ok "label $1 (already there, left alone)"
  else
    gh label create "$1" --color "$2" --description "$3" >/dev/null
    ok "label $1 created"
  fi
}

label ready-for-agent 0e8a16 "Fully specified. An agent can take it."

printf '\nReady. Next: the rest of /skillworks-setup.\n'
