# Each file is weighed against the base copy setup last wrote, so a newer Plugin's Seed replaces only what a team never edited.

import json
import sys
from pathlib import Path

from output.streams import speaking_any_character
from runner import Subprocess
from seeds import merge, old_folder
from seeds.answers import took_an_answer
from seeds.outcome import ASKS, BASES, Outcome, report, write
from sidecar.landed import LIST
from sidecar.locator import sidecar_of
from sidecar.pull import NO_PROMPT, has_remote, reason_in
from sidecar.sidecar import LOCK, Sidecar
from steering.co_authored_by import LOCAL_SETTINGS_FILE, with_member
from steering.rule_imports import RULES_FOLDER
from steering.steering_file import STEERING_FOLDER, sidecar_steering, steering_root
from steering.target_branch import PR_MODE
from stop import Stop, misuse, refusal
from tracker.files import SPECS

USAGE = ("usage: seed-steering [folder] [--sidecar-steering] [--steering-repo <url>] [--keep <file>:<overlap>=yours|seed]... "
         "[--blend <file>:<overlap>=<blend file>]... [--settled <file>]...\n")

SEEDS = Path(__file__).resolve().parents[1] / "skills" / "skillworks-setup" / "seeds"

RULES = ("comments.md", "determinism.md", "file-placement.md", "testing.md", "words.md")

FILES = ("issue-tracker.md", "domain.md", "adr-format.md", "placement-checks.md", "review-standards.md",
         "review-architecture.md", "review-spec.md", "suite.json", "loop.json", "surfaces.md", "deepening-check.md")

PLACES = {**{name: "{}/{}".format(RULES_FOLDER, name) for name in RULES},
          **{name: "{}/{}".format(STEERING_FOLDER, name) for name in FILES}}

# A copy must match its Seed byte for byte, so it cannot carry a header, and this README speaks for it.
BASES_README = """# Base copies

Setup keeps these files. Each one is the Seed exactly as setup last copied it into this repo,
under the Seed's own name. A later run of setup compares it with your file and with the Plugin's
current Seed, to tell your edits from the Plugin's.

These copies are not to be edited. Edit the Steering file in `{}/` instead.
""".format(STEERING_FOLDER)

TARGET_BRANCH_PLACEHOLDER = "<target-branch>"

HANDOFF = ".handoff/"

WORKING_FOLDERS = [".spec-loop/", HANDOFF, ".claude/worktrees/", ".context-backfill/"]

SIDECAR_STEERING = "--sidecar-steering"

STEERING_REPO = "--steering-repo"

SIDECAR_IGNORES = [SPECS + "/", LIST]

WORKING_FOLDERS_WHY = "# The Skillworks working folders. Transient, and never committed."

SIDECAR_IGNORES_WHY = "# The specs and the landed record stay on this machine, so a push sends only Steering."

LOOP_SEED = "loop.json"


# Beside PLACES, so a new Seed is checked the day it is seeded and the loop never stops in the middle of a ticket for it.
def missing_steering(top):
    root = steering_root(top)
    for place in PLACES.values():
        if not (root / place).is_file():
            return ("{} is missing, and setup seeds it. "
                    "Run /skillworks:skillworks-setup to write it again.".format(place))
    return None


def default_branch(runner, top):
    if runner.run(["git", "-C", str(top), "remote", "get-url", "origin"]).status != 0:
        current = runner.run(["git", "-C", str(top), "branch", "--show-current"]).out.strip() or "<branch>"
        raise refusal("no 'origin' remote. The loop lands every ticket by pushing to it, with either Tracker. "
                      "A bare repo on a shared drive is enough:\n"
                      "  git init --bare <shared-drive>/<repo>.git\n"
                      "  git remote add origin <shared-drive>/<repo>.git\n"
                      "  git push origin {}\n"
                      "Nothing was written.".format(current))
    found = runner.run(["git", "-C", str(top), "ls-remote", "--symref", "origin", "HEAD"])
    for line in found.out.splitlines() if found.status == 0 else []:
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            return line[len("ref: refs/heads/"):-len("\tHEAD")]
    raise refusal("origin names no default branch, so loop.json has no Target branch to start from. "
                  "Nothing was written.")


def seed_text(name, target_branch, sidecar_steering):
    wanted = (SEEDS / name).read_text(encoding="utf-8").replace(TARGET_BRANCH_PLACEHOLDER, target_branch)
    if not (sidecar_steering and name == LOOP_SEED):
        return wanted
    return with_member(wanted, json.loads(wanted), "tracker", "files")


def weigh(top, target_branch, name, place, choices, settled, moving, sidecar_steering=False):
    wanted = seed_text(name, target_branch, sidecar_steering)
    target = top / place
    base = top / BASES / name
    was = moving.read(top, "{}/{}".format(BASES, name))
    held = moving.read(top, place)
    chosen = {number: choice for (where, number), choice in choices.items() if where == place}
    weighed = merge.weigh(place, was, held, wanted, chosen, place in settled)
    writes = [(path, text) for path, text in ((target, weighed.text), (base, weighed.base)) if text is not None]
    used = {(place, number) for number in weighed.used} | ({place} if weighed.allows_settled else set())
    return Outcome(weighed.done, weighed.would, shown=weighed.shown, writes=writes,
                   asks=ASKS.get(weighed.asks), used=used)


def seed(runner, top, target_branch, choices, settled, sidecar_steering=False):
    moving = old_folder.planned(top, PLACES.values())
    outcomes = moving.outcomes(runner, top)
    readme = "{}/README.md".format(BASES)
    if moving.read(top, readme) is None:
        outcomes.append(Outcome("wrote {}\n".format(readme), "would write {}\n".format(readme),
                                writes=[(top / readme, BASES_README)]))
    outcomes += [weigh(top, target_branch, name, place, choices, settled, moving, sidecar_steering)
                 for name, place in PLACES.items()]
    used = set().union(*(outcome.used for outcome in outcomes))
    unused = sorted(choice for choice in choices if choice not in used)
    if unused:
        raise refusal("{}:{} names no overlap. Nothing was written.".format(*unused[0]))
    unsettled = sorted(place for place in settled if place not in used)
    if unsettled:
        raise refusal("{} is not a file that differs from its seed with no base copy. Nothing was written."
                      .format(unsettled[0]))
    return outcomes


def ignore_working_folders(top):
    return ignore(top / ".gitignore", ".gitignore", WORKING_FOLDERS)


# Every worktree shares the exclude file, and the team's tracked .gitignore may not ignore the developer's settings.
def exclude_working_folders(runner, top):
    found = runner.run(["git", "-C", str(top), "rev-parse", "--git-path", "info/exclude"])
    if found.status != 0:
        raise refusal("git names no exclude file for {}. Nothing was written.".format(top))
    path = Path(top) / found.out.strip()
    return ignore(path, path.as_posix(), WORKING_FOLDERS + [LOCAL_SETTINGS_FILE])


def ignore_in_the_sidecar(sidecar):
    return ignore(sidecar / ".gitignore", "the Sidecar's .gitignore", SIDECAR_IGNORES, SIDECAR_IGNORES_WHY)


def ignore(path, name, wanted, why=WORKING_FOLDERS_WHY):
    held = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [folder for folder in wanted if folder not in held.splitlines()]
    if not missing:
        return []
    if held and not held.endswith("\n"):
        held += "\n"
    lines = [why] + missing
    named = ", ".join(missing)
    return [Outcome("added {} to {}\n".format(named, name), "would add {} to {}\n".format(named, name),
                    writes=[(path, held + "\n".join(lines) + "\n")])]


def push_first(sidecar):
    return ("The Steering repo is empty. In the Sidecar, commit and push the Steering, so your team can "
            "clone it:\n"
            "  git -C {0} add --all\n"
            "  git -C {0} commit -m \"The team's Steering\"\n"
            "  git -C {0} push -u origin HEAD\n").format(sidecar.as_posix())


# Asked before anything is written, so a Steering repo that cannot be read stops the run with nothing changed.
def holds_a_commit(runner, url):
    listed = runner.run(["git", "ls-remote", url], env=NO_PROMPT)
    if listed.status != 0:
        raise refusal("the Steering repo {} could not be read: {} Nothing was written."
                      .format(url, reason_in(listed.out + listed.err)))
    return listed.out.strip() != ""


def clone(runner, url, sidecar):
    cloned = runner.run(["git", "clone", "--quiet", url, sidecar.as_posix()], env=NO_PROMPT)
    if cloned.status != 0:
        raise refusal("the clone of the Steering repo {} failed: {}".format(url, reason_in(cloned.out + cloned.err)))
    # The files Tracker takes this lock beside the Steering, and a push must never carry it.
    with (sidecar / ".git" / "info" / "exclude").open("a", encoding="utf-8", newline="\n") as exclude:
        exclude.write("/{}\n".format(LOCK))


def give_remote(runner, sidecar, url):
    held = Sidecar(runner, sidecar, None, None)
    if not (sidecar / ".git").exists():
        held.make()
    held.git("remote", "add", "origin", url)


# Two Steerings are never merged by guess, so a local Sidecar meets only an empty Steering repo.
def join_steering_repo(runner, sidecar, url):
    if (sidecar / ".git").exists() and has_remote(runner, sidecar):
        return Outcome("kept the Sidecar's remote, and used the Sidecar as it is\n"), False
    holds = holds_a_commit(runner, url)
    if sidecar.exists():
        if holds:
            raise refusal("the Steering repo already holds Steering, and the Sidecar at {0} holds its own. "
                          "Move the local Sidecar away first, such as to {0}-old, and run setup again to clone "
                          "the team's. Nothing was written.".format(sidecar.as_posix()))
        return Outcome("added the Steering repo as the Sidecar's origin\n",
                       "would add the Steering repo as the Sidecar's origin\n",
                       shown=[push_first(sidecar)], does=[lambda: give_remote(runner, sidecar, url)]), False
    named = "the Steering repo into {}".format(sidecar.as_posix())
    if holds:
        return Outcome("cloned {}, and wrote none of its Steering\n".format(named),
                       "would clone {}\n".format(named), does=[lambda: clone(runner, url, sidecar)]), True
    return Outcome("cloned {}\n".format(named), "would clone {}\n".format(named), shown=[push_first(sidecar)],
                   does=[lambda: clone(runner, url, sidecar)]), False


def make_handoff_folder(top):
    if (top / HANDOFF).is_dir():
        return []
    return [Outcome("created {}\n".format(HANDOFF), "would create {}\n".format(HANDOFF), makes=[top / HANDOFF])]


# Setup's own files are left out, so a team that committed what setup wrote is not sent to read a history it does not have.
def has_history(runner, top):
    setups_own = list(PLACES.values()) + [BASES, ".gitignore", "CLAUDE.md", "AGENTS.md", ".claude/settings.json"]
    found = runner.run(["git", "-C", str(top), "rev-list", "-n", "1", "HEAD", "--", "."]
                       + [":(exclude){}".format(place) for place in setups_own])
    return found.status == 0 and bool(found.out.strip())


# architecture-tests refuses under Sidecar Steering, so the step after setup there is the first grill.
def next_step(runner, top, sidecar_steering):
    then = "/skillworks:grill" if sidecar_steering else "/skillworks:architecture-tests"
    has_glossary = (top / "CONTEXT.md").exists() or (top / "CONTEXT-MAP.md").exists()
    if has_history(runner, top) and not has_glossary:
        return "next step: /skillworks:context-backfill, then {}\n".format(then)
    return "next step: {}\n".format(then)


def parsed(argv):
    where, choices, settled, sidecar, url = None, {}, set(), False, None
    rest = iter(argv)
    for arg in rest:
        if took_an_answer(arg, rest, choices, settled, USAGE):
            continue
        if arg == SIDECAR_STEERING and not sidecar:
            sidecar = True
        elif arg == STEERING_REPO and url is None:
            url = next(rest, None)
            if url is None or url.startswith("--"):
                raise misuse(USAGE)
        elif where is None and not arg.startswith("--"):
            where = arg
        else:
            raise misuse(USAGE)
    return where or ".", choices, settled, sidecar, url


def main(argv, runner, out, err):
    try:
        where, choices, settled, asked_for_sidecar, url = parsed(argv)
        found = runner.run(["git", "-C", where, "rev-parse", "--show-toplevel"])
        if found.status != 0:
            raise refusal("{} is not in a git repository. Nothing was written.".format(where))
        top = Path(found.out.strip())
        default = default_branch(runner, top)
        # Once the Sidecar holds the loop file the mode is on, so a later run with no answer still seeds the Sidecar.
        sidecar = sidecar_of(runner, top) if asked_for_sidecar else sidecar_steering(top)
        if url and sidecar is None:
            raise refusal("a Steering repo serves Sidecar Steering only, so run with {} to name one. "
                          "Nothing was written.".format(SIDECAR_STEERING))
        if sidecar is None:
            outcomes = seed(runner, top, default, choices, settled) + ignore_working_folders(top)
        else:
            joined, took_the_teams = join_steering_repo(runner, sidecar, url) if url else (None, False)
            # A clone of the team's Steering takes only what belongs to this machine.
            steering = [] if took_the_teams else (seed(runner, sidecar, PR_MODE, choices, settled, sidecar_steering=True)
                                          + ignore_in_the_sidecar(sidecar))
            outcomes = ([joined] if joined else []) + steering + exclude_working_folders(runner, top)
        report(outcomes + make_handoff_folder(top), next_step(runner, top, sidecar is not None), out)
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    speaking_any_character(sys.stdout)
    speaking_any_character(sys.stderr)
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr))
