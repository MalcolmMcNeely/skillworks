# The short command has already checked uv, since without uv this script cannot start.

import json
import os
import re
import sys
from pathlib import Path

from configuration.checks import check_configuration
from runner import Subprocess
from steering.rule_imports import RULES_FOLDER, missing_import
from steering.target_branch import SPEC_MODE, target_setting, tracker_setting
from stop import Stop, misuse, refusal

USAGE = "usage: skillworks-preflight [--check-only]\n"

GH_QUIET = {"GH_PROMPT_DISABLED": "1"}

CACHING_CLAUDE = (2, 1, 242)

RULES_THAT_REFUSE = ("pull_request", "update", "required_status_checks", "required_deployments", "merge_queue")

LABEL = ("ready-for-agent", "0e8a16", "Fully specified. An agent can take it.")


def ok(out, said):
    out.write("ok    " + said + "\n")


def warn(out, said):
    out.write("warn  " + said + "\n")


def check_only(argv):
    if any(arg != "--check-only" for arg in argv):
        raise misuse(USAGE)
    return bool(argv)


# Compared as numbers, so 2.1.1000 is newer than 2.1.242.
def version_numbers(version):
    return tuple(int(number) for number in re.findall(r"[0-9]+", version))


class Preflight:
    def __init__(self, runner, out, where):
        self.runner = runner
        self.out = out
        self.where = where

    def git(self, *args):
        return self.runner.run(["git", "-C", self.top] + list(args))

    def gh(self, *args):
        ran = self.runner.run(["gh"] + list(args), self.top, GH_QUIET)
        if ran.status != 0:
            raise refusal("gh {} failed: {}".format(" ".join(args), (ran.err or ran.out).strip()))
        return ran.out.strip()

    def run(self, only_checking):
        if not self.runner.found("git"):
            raise refusal("git is not installed")
        if not self.runner.found("claude"):
            raise refusal("claude is not on PATH. The loop shells out to it.")
        found = self.runner.run(["git", "-C", self.where, "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("not inside a git repository")
        self.top = found.out.strip()

        self.check_rule_imports()
        self.tracker = tracker_setting(self.top)
        self.target = target_setting(self.top)
        self.check_claude()
        self.origin = self.check_origin()

        # The files Tracker is committed files on any remote, so it needs no gh and no label.
        if self.tracker == "files":
            ok(self.out, "tracker files, on " + self.origin)
            self.check_files_remote()
        else:
            self.check_github()
            if only_checking:
                ok(self.out, "check-only: no labels were written")
            else:
                self.label(*LABEL)

        check_configuration(self.runner, self.top, self.out)
        if not only_checking:
            self.out.write("\nReady. Next: the rest of /skillworks:skillworks-setup.\n")

    def check_rule_imports(self):
        if not (Path(self.top) / RULES_FOLDER).is_dir():
            return
        missing = missing_import(self.top)
        if missing:
            raise refusal(missing)
        ok(self.out, "CLAUDE.md imports every rule in " + RULES_FOLDER)

    def check_claude(self):
        said = self.runner.run(["claude", "--version"]).out.split()
        version = said[0] if said else ""
        if version_numbers(version) < CACHING_CLAUDE:
            warn(self.out, "claude {} predates 2.1.242, so promptCacheTtl in .claude/settings.json is ignored. "
                           "Each ticket will pay a cold prompt cache.".format(version))
        else:
            ok(self.out, "claude " + version)

    def check_origin(self):
        origin = self.git("remote", "get-url", "origin")
        if origin.status == 0 and origin.out.strip():
            return origin.out.strip()
        first = self.git("branch", "--show-current").out.strip() if self.target == SPEC_MODE else self.target
        raise refusal("no 'origin' remote. The loop lands every ticket by pushing to it. "
                      "A bare repo on a shared drive is enough:\n"
                      "  git init --bare <shared-drive>/<repo>.git\n"
                      "  git remote add origin <shared-drive>/<repo>.git\n"
                      "  git push origin " + first)

    # Git alone reads the remote, so GitLab, Bitbucket and a bare repo on a shared drive all pass.
    def check_files_remote(self):
        listed = self.git("ls-remote", "--symref", "origin")
        if listed.status != 0:
            raise refusal("could not read origin ({}): {}".format(self.origin, (listed.err + listed.out).strip()))
        rows = [line.split() for line in listed.out.splitlines()]
        heads = {row[1] for row in rows if len(row) >= 2 and row[0] != "ref:"}
        if self.target == SPEC_MODE:
            named = [row[1] for row in rows if len(row) >= 3 and row[0] == "ref:" and row[2] == "HEAD"]
            default = named[0].removeprefix("refs/heads/") if named else ""
            if not default or "refs/heads/" + default not in heads:
                raise refusal("origin names no default branch, and each spec's pull request merges into it.")
            ok(self.out, "target-branch spec, each reviewed into " + default)
        else:
            if "refs/heads/" + self.target not in heads:
                raise refusal("the Target branch {} in docs/agents/loop.json is not on origin.".format(self.target))
            ok(self.out, "target-branch " + self.target)

    def check_github(self):
        if not self.runner.found("gh"):
            raise refusal("gh is not installed. https://cli.github.com")
        if self.runner.run(["gh", "auth", "status"], self.top, GH_QUIET).status != 0:
            raise refusal("gh is not authenticated. Run: gh auth login")
        self.login = self.gh("api", "user", "--jq", ".login")
        ok(self.out, "gh authenticated as " + self.login)

        if "github.com" not in self.origin:
            raise refusal("origin is not GitHub: {}. The github Tracker needs a GitHub remote. With any other "
                          "remote, set \"tracker\": \"files\" in docs/agents/loop.json.".format(self.origin))

        self.repo = self.gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
        ok(self.out, "repo " + self.repo)

        # Native issue dependencies must be readable, or the loop cannot tell what is blocked.
        held = json.loads(self.gh("api", "repos/" + self.repo))
        if held.get("has_issues") is not True:
            raise refusal("Issues are disabled on {}. Enable them in repo settings.".format(self.repo))
        ok(self.out, "issues enabled")

        if self.target == SPEC_MODE:
            default = held.get("default_branch", "")
            if not self.on_remote(default):
                raise refusal("the default branch {} is not on {}, and each spec's pull request merges into it.".format(
                    default, self.repo))
            ok(self.out, "target-branch spec, each reviewed into " + default)
            landing = "a spec's branch"
        else:
            if not self.on_remote(self.target):
                raise refusal("the Target branch {} in docs/agents/loop.json is not on {}.".format(
                    self.target, self.repo))
            ok(self.out, "target-branch " + self.target)
            landing = self.target

        if (held.get("permissions") or {}).get("push") is not True:
            raise refusal("{} may not push to {}, so the loop cannot land a ticket on {}.".format(
                self.login, self.repo, landing))

        # In spec mode a pull request, not a push, reaches the default branch, so its protection stops nothing the loop does.
        if self.target != SPEC_MODE:
            self.takes_direct_push(self.target)

    def on_remote(self, branch):
        ran = self.runner.run(["gh", "api", "repos/{}/branches/{}".format(self.repo, branch), "--jq", ".name"],
                              self.top, GH_QUIET)
        return ran.status == 0

    def takes_direct_push(self, branch):
        # A ruleset can refuse a login that may push, and its rule list is readable without admin rights.
        rules = self.runner.run(["gh", "api", "repos/{}/rules/branches/{}".format(self.repo, branch)],
                                self.top, GH_QUIET)
        types = [rule.get("type") for rule in json.loads(rules.out)] if rules.status == 0 else []
        refusing = [kind for kind in types if kind in RULES_THAT_REFUSE]
        if refusing:
            raise refusal("a rule on {} in {} refuses a direct push ({}). The loop lands every ticket by pushing "
                          "to {}.".format(branch, self.repo, ",".join(refusing), branch))

        # Classic protection is readable with admin rights only, and an admin passes it unless it holds admins too.
        read = self.runner.run(["gh", "api", "repos/{}/branches/{}/protection".format(self.repo, branch)],
                               self.top, GH_QUIET)
        if read.status != 0:
            if "Branch not protected" in read.out + read.err:
                ok(self.out, "{} may push to {}".format(self.login, branch))
            else:
                warn(self.out, "could not read the classic branch protection on {} in {}, so a rule there that "
                               "refuses a direct push was not checked. Reading it needs admin rights on {}.".format(
                                   branch, self.repo, self.repo))
            return
        protection = json.loads(read.out)
        if (protection.get("enforce_admins") or {}).get("enabled"):
            self.check_enforced(branch, protection)
        ok(self.out, "{} may push to {}".format(self.login, branch))

    def check_enforced(self, branch, protection):
        refusing = [name for name, held in (
            ("pull_request", protection.get("required_pull_request_reviews")),
            ("required_status_checks", protection.get("required_status_checks")),
            ("lock_branch", (protection.get("lock_branch") or {}).get("enabled")),
        ) if held]
        if refusing:
            raise refusal("classic branch protection on {} in {} refuses a direct push ({}). The loop lands every "
                          "ticket by pushing to {}.".format(branch, self.repo, ",".join(refusing), branch))
        restrictions = protection.get("restrictions")
        if not restrictions:
            return
        if self.login in [user.get("login") for user in restrictions.get("users") or []]:
            return
        teams = ",".join(team.get("slug") for team in restrictions.get("teams") or [])
        if not teams:
            raise refusal("classic branch protection on {} in {} restricts who may push, and {} is not one of "
                          "them. The loop lands every ticket by pushing to {}.".format(
                              branch, self.repo, self.login, branch))
        warn(self.out, "classic branch protection on {} in {} lets teams push ({}), and {} is not named. If {} is "
                       "on none of those teams, the loop cannot land a ticket on {}.".format(
                           branch, self.repo, teams, self.login, self.login, branch))

    # to-spec and to-tickets fail on a missing label, and one already there is kept, since its colour may be deliberate.
    def label(self, name, colour, description):
        held = self.gh("label", "list", "--limit", "200", "--json", "name", "--jq", ".[].name").splitlines()
        if name in held:
            ok(self.out, "label {} (already there, left alone)".format(name))
        else:
            self.gh("label", "create", name, "--color", colour, "--description", description)
            ok(self.out, "label {} created".format(name))


def main(argv, runner, out, err, where=None):
    try:
        only_checking = check_only(argv)
        Preflight(runner, out, where or os.getcwd()).run(only_checking)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    # Windows adds a carriage return, which the output would carry to the screen.
    sys.stdout.reconfigure(newline="\n")
    sys.stderr.reconfigure(newline="\n")
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
