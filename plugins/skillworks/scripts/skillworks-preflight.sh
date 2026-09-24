#!/usr/bin/env bash
#
# Check this repo can run the Skillworks loop, then create the label it needs.
#
#   skillworks-preflight [--check-only]
#
# Idempotent. Run it again any time to repair.
#
# Stays bash: it checks the machine for the languages the rest of the loop runs on.

set -euo pipefail

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1 ;;
    *) printf "usage: skillworks-preflight [--check-only]\n" >&2; exit 64 ;;
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
command -v uv >/dev/null || die "uv is not on PATH. The loop's scripts are Python and run under it. https://docs.astral.sh/uv"

gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"
login=$(gh api user --jq .login)
ok "gh authenticated as $login"

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

default=$(gh api "repos/$REPO" --jq .default_branch)
[ "$default" = "main" ] || die "the default branch of $REPO is $default, not main. The loop lands every ticket on main."
ok "default branch main"

[ "$(gh api "repos/$REPO" --jq .permissions.push)" = "true" ] \
  || die "$login may not push to $REPO, so the loop cannot land a ticket on main."
# A ruleset can refuse a login that may push, and its rule list is readable without admin rights.
refusing=$(gh api "repos/$REPO/rules/branches/main" --jq '.[].type' \
  | grep -xE 'pull_request|update|required_status_checks|required_deployments|merge_queue' \
  | paste -sd, - || true)
[ -z "$refusing" ] \
  || die "a rule on main in $REPO refuses a direct push ($refusing). The loop lands every ticket by pushing to main."
ok "$login may push to main"

# --- labels -----------------------------------------------------------------
#
# Nothing in the loop READS a label. The driver finds work by sub-issue
# parentage, blocked_by and assignee. One label exists only because /skillworks:to-spec
# and /skillworks:to-tickets APPLY it, and `gh issue create` fails on a label that is
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

if [ "$CHECK_ONLY" = "1" ]; then
  ok "check-only: no labels were written"
else
  label ready-for-agent 0e8a16 "Fully specified. An agent can take it."
fi

# --- configuration ----------------------------------------------------------
#
# A check here warns and never fails: a team may have chosen otherwise on purpose.

# The file is piped in, so node never has to read a path that bash spelled.
settings="$(git rev-parse --show-toplevel)/.claude/settings.json"
# node is not required, so without it the setting is unknown rather than wrong.
if ! command -v node >/dev/null; then
  warn "could not check autoMemoryEnabled in .claude/settings.json, because node is not on PATH."
elif [ -f "$settings" ] && node -e '
  let text = "";
  process.stdin.on("data", chunk => text += chunk);
  process.stdin.on("end", () => {
    try { process.exit(JSON.parse(text).autoMemoryEnabled === false ? 0 : 1); }
    catch { process.exit(1); }
  });
' < "$settings" 2>/dev/null; then
  ok "auto-memory off"
else
  warn "autoMemoryEnabled is not false in .claude/settings.json, so each session loads memory files only this machine holds. Add \"autoMemoryEnabled\": false to that file."
fi

if ! command -v node >/dev/null; then
  warn "could not check which plugins force an output style, because node is not on PATH."
elif ! plugins=$(claude plugin list --json 2>/dev/null) || ! forcing=$(printf '%s' "$plugins" | node -e '
  const fs = require("fs");
  const path = require("path");
  const key = p => process.platform === "win32" ? path.resolve(p).toLowerCase() : path.resolve(p);
  const top = key(process.argv[1]);
  const forces = file => {
    const front = /^---\r?\n([\s\S]*?)\r?\n---/.exec(fs.readFileSync(file, "utf8"));
    return front !== null && /^force-for-plugin:\s*true\s*$/m.test(front[1]);
  };
  const styles = where => {
    if (!fs.existsSync(where)) return [];
    if (!fs.statSync(where).isDirectory()) return [where];
    return fs.readdirSync(where).filter(name => name.endsWith(".md")).map(name => path.join(where, name));
  };
  let text = "";
  process.stdin.on("data", chunk => text += chunk);
  process.stdin.on("end", () => {
    for (const plugin of JSON.parse(text)) {
      if (!plugin.enabled || plugin.id.startsWith("skillworks@")) continue;
      if (plugin.projectPath && key(plugin.projectPath) !== top) continue;
      const places = ["output-styles"];
      try {
        const manifest = JSON.parse(fs.readFileSync(path.join(plugin.installPath, ".claude-plugin", "plugin.json"), "utf8"));
        places.push(...[].concat(manifest.outputStyles ?? []));
      } catch {}
      const files = places.flatMap(place => styles(path.resolve(plugin.installPath, place)));
      if (files.some(forces)) console.log(plugin.id);
    }
  });
' "$(git rev-parse --show-toplevel)"); then
  warn "could not check which plugins force an output style, because claude plugin list --json gave nothing node could read."
elif [ -n "$forcing" ]; then
  while IFS= read -r id; do
    warn "$id also forces an output style. When two plugins force one the first loaded wins, so the loop's reports may not come in the skillworks style."
  done <<< "$forcing"
else
  ok "no other plugin forces an output style"
fi

if [ "$CHECK_ONLY" = "0" ]; then
  printf '\nReady. Next: the rest of /skillworks:skillworks-setup.\n'
fi
