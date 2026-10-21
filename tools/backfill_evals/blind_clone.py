# The arm is served after the tree is hashed and is left uncommitted, so one pin holds for every arm.

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# The harness reaches programs the way the Plugin's scripts do, so it borrows their Runner.
sys.path.insert(0, str(ROOT / "plugins" / "skillworks" / "scripts"))

import scrub_rules
from context_backfill.backfill import SCRATCH
from runner import Subprocess
from seed_steering import PLACES, SEEDS
from steering.target_branch import LOOP_FILE
from stop import Stop, misuse, refusal

USAGE = ("usage: blind_clone.py build <folder> [--arm <ref>]\n"
         "       blind_clone.py pin <commit> <folder> [--arm <ref>]\n")

PIN_FILE = HERE / "pin.json"

FILTER_REPO = "git-filter-repo"
# Named, so every build rewrites with the same code and the tree hash cannot move under it.
FILTER_REPO_VERSION = FILTER_REPO + "==2.47.0"

TOOLS = ("claude", "uv", "git")
TOOL_NAMES = {"claude": "Claude Code"}

SEEDS_FOLDER = SEEDS.relative_to(ROOT).as_posix()
ARM_PATHS = ("plugins/skillworks/skills/context-backfill", "plugins/skillworks/scripts", "plugins/skillworks/bin")
DEFAULT_TARGET = "main"

# Fixed, with the pin's own date, so a second build makes the same reset commit.
RESET_NAME = "Blind clone"
RESET_EMAIL = "blind-clone@example.invalid"
RESET_MESSAGE = "Set up the Blind clone"

LOOP_SEED = "loop.json"


def git(runner, where, *args, env=None):
    return runner.run(["git", "-C", Path(where).as_posix()] + list(args), env=env)


def said_by(ran):
    return (ran.out + ran.err).rstrip("\n")


def must(ran, doing):
    if ran.status != 0:
        raise refusal("The build could not {}. It said:\n{}".format(doing, said_by(ran)))
    return ran.out


def lack(name):
    return refusal("The build needs Claude Code, uv, git and git-filter-repo, and {} is missing. Install it, "
                   "then run this again. Nothing was built.".format(name))


def need_tools(runner):
    for tool in TOOLS:
        if not runner.found(tool):
            raise lack(TOOL_NAMES.get(tool, tool))
    if runner.run(["uvx", FILTER_REPO_VERSION, "--version"]).status != 0:
        raise lack(FILTER_REPO)


def shown(runner, source, ref, path):
    ran = git(runner, source, "show", "{}:{}".format(ref, path))
    return ran.out if ran.status == 0 else None


def banned_words(said):
    if said is None:
        return []
    words, inside = [], False
    for line in said.splitlines():
        if line.startswith("banned-words:"):
            inside = True
        elif inside and line and not line[0].isspace():
            inside = False
        elif inside and line.strip().startswith("- "):
            words.append(line.strip()[2:].strip())
    return words


def target_of(said):
    named = json.loads(said).get("target-branch", DEFAULT_TARGET) if said else DEFAULT_TARGET
    # A repo whose specs name their own branches grew its history on the default one.
    return named if named != "spec" else DEFAULT_TARGET


def entries(runner, source, ref, *paths):
    listed = must(git(runner, source, "ls-tree", "-r", "-z", ref, "--", *paths), "list the files of " + ref)
    for entry in filter(None, listed.split("\0")):
        mode, _, rest = entry.partition(" ")
        blob, _, path = rest.partition("\t")
        yield mode, blob.split()[-1], path


def records_hash(runner, source, pin):
    held = sorted((path, blob) for _, blob, path in entries(runner, source, pin) if scrub_rules.is_record(path))
    return hashlib.sha256("".join("{} {}\n".format(blob, path) for path, blob in held).encode("utf-8")).hexdigest()


def callback(call):
    return "import sys; sys.path.insert(0, r'{}'); import scrub_rules; return scrub_rules.{}".format(
        HERE.as_posix(), call)


def scrub(runner, clone, banned):
    paths = [arg for path in scrub_rules.PATHS for arg in ("--path", path)]
    globs = [arg for glob in scrub_rules.PATH_GLOBS for arg in ("--path-glob", glob)]
    ran = runner.run(
        ["uvx", FILTER_REPO_VERSION, "--force", "--quiet", "--prune-empty", "never", "--prune-degenerate", "never",
         "--invert-paths", *paths, *globs,
         "--message-callback", callback("message(message)"),
         "--file-info-callback", callback("file_info(filename, mode, blob_id, value)")],
        clone.as_posix(), {scrub_rules.BANNED_VARIABLE: json.dumps(banned)})
    must(ran, "rewrite the history with git-filter-repo")


def write(path, said):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(said, encoding="utf-8", newline="\n")


def reset(runner, clone, pin_date):
    seeds = clone / SEEDS_FOLDER
    for name, place in PLACES.items():
        if place in scrub_rules.FILLED_STEERING:
            write(clone / place, (seeds / name).read_text(encoding="utf-8"))
    loop_path = clone / LOOP_FILE
    loop = json.loads((loop_path if loop_path.is_file() else seeds / LOOP_SEED).read_text(encoding="utf-8"))
    loop["tracker"] = "files"
    write(loop_path, json.dumps(loop, indent=2) + "\n")
    ignore = clone / ".gitignore"
    held = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    if SCRATCH + "/" not in held.splitlines():
        write(ignore, held + ("" if held.endswith("\n") or not held else "\n") + SCRATCH + "/\n")
    must(git(runner, clone, "add", "-A"), "stage the reset")
    who = {"GIT_AUTHOR_NAME": RESET_NAME, "GIT_AUTHOR_EMAIL": RESET_EMAIL, "GIT_AUTHOR_DATE": pin_date,
           "GIT_COMMITTER_NAME": RESET_NAME, "GIT_COMMITTER_EMAIL": RESET_EMAIL, "GIT_COMMITTER_DATE": pin_date}
    must(git(runner, clone, "-c", "commit.gpgsign=false", "commit", "--quiet", "--no-verify", "-m", RESET_MESSAGE,
             env=who), "make the reset commit")


def serve_the_arm(runner, source, clone, arm):
    for path in ARM_PATHS:
        shutil.rmtree(clone / path, ignore_errors=True)
    for mode, blob, path in entries(runner, source, arm, *ARM_PATHS):
        file = clone / path
        write(file, must(git(runner, source, "cat-file", "blob", blob), "read {} at {}".format(path, arm)))
        if mode == "100755":
            file.chmod(0o755)


def build(runner, source, commit, folder, arm):
    if folder.exists() and any(folder.iterdir()):
        raise refusal("{} already holds files, and a Blind clone is built in an empty folder. Name another, "
                      "then run this again. Nothing was built.".format(folder.as_posix()))
    pin = must(git(runner, source, "rev-parse", "--verify", commit + "^{commit}"), "find the commit " + commit).strip()
    arm = must(git(runner, source, "rev-parse", "--verify", arm + "^{commit}"), "find the arm's ref " + arm).strip()
    target = target_of(shown(runner, source, pin, LOOP_FILE))
    banned = banned_words(shown(runner, source, pin, scrub_rules.FILLED_STEERING[0]))
    pin_date = must(git(runner, source, "show", "-s", "--format=%cI", pin), "read the pin's date").strip()

    clone, origin = folder / "repo", folder / "origin.git"
    folder.mkdir(parents=True, exist_ok=True)
    must(runner.run(["git", "clone", "--quiet", "--no-local", "--no-checkout", "--no-tags", "-c", "core.autocrlf=false",
                     Path(source).as_posix(), clone.as_posix()]), "clone " + Path(source).as_posix())
    must(git(runner, clone, "checkout", "--quiet", "-B", target, pin), "check out the pin")
    must(git(runner, clone, "remote", "remove", "origin"), "forget the source")
    for branch in must(git(runner, clone, "for-each-ref", "--format=%(refname:short)", "refs/heads"),
                       "list the branches").split():
        if branch != target:
            must(git(runner, clone, "branch", "--quiet", "-D", branch), "drop the branch " + branch)
    scrub(runner, clone, banned)
    reset(runner, clone, pin_date)
    tree = must(git(runner, clone, "rev-parse", "HEAD^{tree}"), "read the tree").strip()

    must(runner.run(["git", "init", "--quiet", "--bare", "--initial-branch=" + target, origin.as_posix()]),
         "make the origin")
    must(git(runner, clone, "remote", "add", "origin", origin.as_posix()), "name the origin")
    must(git(runner, clone, "push", "--quiet", "-u", "origin", target), "push to the origin")
    must(git(runner, clone, "remote", "set-head", "origin", target), "name the origin's default branch")
    serve_the_arm(runner, source, clone, arm)
    return {"commit": pin, "tree": tree, "records": records_hash(runner, source, pin)}


def parsed(argv):
    verb, rest = (argv[0], argv[1:]) if argv else (None, [])
    arm = "HEAD"
    if "--arm" in rest:
        at = rest.index("--arm")
        if at + 1 >= len(rest):
            raise misuse(USAGE)
        arm = rest[at + 1]
        rest = rest[:at] + rest[at + 2:]
    if (verb, len(rest)) not in (("build", 1), ("pin", 2)):
        raise misuse(USAGE)
    return verb, rest, arm


def told(made, folder):
    return ("Built a Blind clone of {} in {}\n  tree     {}\n  records  {}\n".format(
        made["commit"], folder.as_posix(), made["tree"], made["records"]))


def main(argv, runner, out, err, where, pin_file=PIN_FILE):
    try:
        verb, rest, arm = parsed([str(a) for a in argv])
        need_tools(runner)
        source = must(git(runner, where, "rev-parse", "--show-toplevel"), "find the repo").strip()
        if verb == "pin":
            folder = Path(where, rest[1])
            made = build(runner, source, rest[0], folder, arm)
            Path(pin_file).write_text(json.dumps(made, indent=2) + "\n", encoding="utf-8", newline="\n")
        else:
            folder = Path(where, rest[0])
            stored = json.loads(Path(pin_file).read_text(encoding="utf-8"))
            made = build(runner, source, stored["commit"], folder, arm)
            if made["tree"] != stored["tree"]:
                raise refusal("The Blind clone's tree hash is {}, and the pin stores {}, so this clone is not the "
                              "one the Statements were split on. Mend the scrub rules, or move the pin with "
                              "`pin`. The clone in {} is not to be used.".format(
                                  made["tree"], stored["tree"], folder.as_posix()))
        out.write(told(made, folder))
        return 0
    except Stop as stop:
        err.write(stop.said)
        return stop.status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], Subprocess(), sys.stdout, sys.stderr, os.getcwd()))
