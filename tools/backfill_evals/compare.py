import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import blind_clone
import judge
import score
import shape
from context_backfill.backfill import SCRATCH
from context_backfill.context_map import MAP_FILE
from runner import NOT_FOUND, Ran, Subprocess, session_changes
from steering.target_branch import LOOP_FILE
from stop import refusal

RUNS_PER_ARM = 3
# Run 3 of the smoke runs took 110 minutes, so a run still going at three hours is wedged.
CAP_MINUTES = 180
# What coreutils' timeout answers for a program it stopped, so a capped run reads like one.
TIMED_OUT = 124
PROMPT = "/skillworks:context-backfill"
# Nobody is at the keyboard to approve a tool call, and the clone is thrown away after the run.
PERMISSION_MODE = "bypassPermissions"
CLONES = "clones"


def decoded(said):
    if said is None:
        return ""
    return said.decode("utf-8", "replace") if isinstance(said, bytes) else said


class Capped(Subprocess):
    def capped(self, args, where, env, seconds):
        args = [str(a) for a in args]
        found = shutil.which(args[0])
        if found is None:
            return Ran(NOT_FOUND, "", args[0] + ": not found\n")
        try:
            done = subprocess.run([found] + args[1:], cwd=where, env=self.environment(env), capture_output=True,
                                  encoding="utf-8", errors="replace", timeout=seconds)
        except subprocess.TimeoutExpired as stopped:
            return Ran(TIMED_OUT, decoded(stopped.stdout), decoded(stopped.stderr))
        return Ran(done.returncode, done.stdout, done.stderr)


def map_answer(said):
    claimed = shape.map_paths(said or "")
    if not claimed:
        raise refusal("{} at the pin names no context with folders, so the harness has no answer to the map "
                      "question. Nothing was run.".format(MAP_FILE))
    return "A map, with these contexts and the folders each claims. Write it into shape.md under ## Answer, " \
           "and go on.\n\n" + "".join("- {}: {}\n".format(context, ", ".join("`{}`".format(path) for path in paths))
                                      for context, paths in claimed.items())


def resolved(runner, source, ref):
    return blind_clone.must(blind_clone.git(runner, source, "rev-parse", "--verify", ref + "^{commit}"),
                            "find the arm's ref " + ref).strip()


def target_branch(runner, source):
    loop = Path(source) / LOOP_FILE
    target = blind_clone.target_of(loop.read_text(encoding="utf-8") if loop.is_file() else None)
    blind_clone.must(blind_clone.git(runner, source, "fetch", "--quiet", "origin", target),
                     "fetch {} from origin".format(target))
    return "origin/" + target


def arms_of(runner, source, refs):
    old = refs[0] if refs else target_branch(runner, source)
    new = refs[1] if len(refs) > 1 else blind_clone.WORKING_TREE
    labels = {"old": "{} at {}".format(old, resolved(runner, source, old))}
    labels["new"] = "the working tree, on {}".format(resolved(runner, source, "HEAD")) \
        if new is blind_clone.WORKING_TREE else "{} at {}".format(new, resolved(runner, source, new))
    return {"old": old, "new": new}, labels


def comparison_folder(runs, today):
    folder, count = Path(runs) / today, 1
    while folder.exists():
        count += 1
        folder = Path(runs) / "{}-{}".format(today, count)
    folder.mkdir(parents=True)
    return folder


def session(runner, clone, prompt, seconds, *rest):
    return runner.capped(["claude", "-p", prompt, *rest, "--permission-mode", PERMISSION_MODE,
                          "--output-format", "json"], clone.as_posix(), session_changes(), seconds)


def kept(folder, name, ran):
    (folder / name).write_text(ran.out + ran.err, encoding="utf-8", newline="\n")


def one_run(runner, clone, folder, answer):
    folder.mkdir(parents=True)
    cap = CAP_MINUTES * 60
    ran = session(runner, clone, PROMPT, cap)
    scratch = clone / SCRATCH
    held = judge.result_of(ran.out) or {}
    asked = ran.status != TIMED_OUT and not (scratch / score.SHEET_FILE).is_file() \
        and (scratch / shape.SHAPE_FILE).is_file() and held.get("session_id")
    if asked:
        kept(folder, score.QUESTION_FILE, ran)
        spent = (held.get("duration_ms") or 0) / 1000
        ran = session(runner, clone, answer, max(cap - spent, 0), "--resume", held["session_id"])
    kept(folder, score.OUTPUT_FILE, ran)
    if ran.status == TIMED_OUT:
        (folder / score.CAPPED_FILE).write_text(str(CAP_MINUTES) + "\n", encoding="utf-8")
    for file in sorted(scratch.iterdir()) if scratch.is_dir() else []:
        if file.is_file():
            shutil.copy2(file, folder / file.name)


def compare(runner, source, refs, runs, pin, statements_folder, today, err):
    answer = map_answer(blind_clone.shown(runner, source, pin["commit"], MAP_FILE))
    arms, labels = arms_of(runner, source, refs)
    comparison = comparison_folder(runs, today)
    (comparison / score.COMPARISON_FILE).write_text(json.dumps(dict(
        labels, **{"claude-code": runner.run(["claude", "--version"]).out.strip(), "started": today,
                   "cap-minutes": CAP_MINUTES}), indent=2) + "\n", encoding="utf-8", newline="\n")
    for arm in score.ARMS:
        clones = []
        for at in range(1, RUNS_PER_ARM + 1):
            name = "run-{}".format(at)
            folder = comparison / CLONES / "{}-{}".format(arm, name)
            made = blind_clone.build(runner, source, pin["commit"], folder, arms[arm])
            if made["tree"] != pin["tree"]:
                raise refusal("The Blind clone's tree hash is {}, and the pin stores {}, so its history is not the "
                              "one the Statements were split on. Mend the scrub rules, or move the pin. Nothing "
                              "was run.".format(made["tree"], pin["tree"]))
            clones.append((folder / "repo", comparison / arm / name))
        with ThreadPoolExecutor(max_workers=RUNS_PER_ARM) as pool:
            for started in [pool.submit(one_run, runner, clone, folder, answer) for clone, folder in clones]:
                started.result()
    err.write("The runs are kept in {}. `harness.py score {}` judges them again.\n".format(
        comparison.as_posix(), comparison.name))
    return score.score(runner, source, comparison, pin, statements_folder, today)
