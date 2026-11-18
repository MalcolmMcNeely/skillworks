import json
from dataclasses import dataclass
from pathlib import Path

from stop import refusal

# The developer's own files, outside every repo, so the client repo and its Sidecar never name the remote.
USER_FOLDER = ".skillworks"

SETTINGS = "remote-steering.json"

CLONE = "remote-steering.git"

HELD = "remote-steering-held"

BRANCH = "main"


@dataclass(frozen=True)
class Remote:
    clone: Path
    commit: str
    warning: str | None

    def file(self, runner, path):
        shown = git(runner, self.clone, "cat-file", "-p", self.at(path))
        return shown.out if shown.status == 0 and self.kind(runner, path) == "blob" else None

    def folder(self, runner, path):
        if self.kind(runner, path) != "tree":
            return None
        listed = git(runner, self.clone, "ls-tree", self.at(path))
        return [line.split("\t", 1)[1] for line in listed.out.splitlines() if " blob " in line]

    def kind(self, runner, path):
        found = git(runner, self.clone, "cat-file", "-t", self.at(path))
        return found.out.strip() if found.status == 0 else None

    def at(self, path):
        return "{}:{}".format(self.commit, path.strip("/"))


def git(runner, clone, *args):
    return runner.run(["git", "--git-dir", Path(clone).as_posix()] + list(args))


def settings_of(home):
    try:
        held = json.loads(Path(home, USER_FOLDER, SETTINGS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return held if isinstance(held, dict) else None


def origin_of(runner, top):
    found = runner.run(["git", "-C", Path(top).as_posix(), "remote", "get-url", "origin"])
    return found.out.strip() if found.status == 0 else None


def named_url(runner, top, home):
    settings = settings_of(home)
    if settings is None or not isinstance(settings.get("url"), str) or not settings["url"]:
        return None
    repos = settings.get("repos")
    origin = origin_of(runner, top)
    return settings["url"] if origin and isinstance(repos, list) and origin in repos else None


def tip(runner, clone):
    found = git(runner, clone, "rev-parse", "--verify", "--quiet", "refs/heads/{}^{{commit}}".format(BRANCH))
    return found.out.strip() if found.status == 0 else None


# Every repo on the machine reads one clone, so a fetch made in one repo serves them all.
def fetch_error(runner, url, clone):
    if not clone.is_dir():
        made = runner.run(["git", "init", "--quiet", "--bare", clone.as_posix()])
        if made.status != 0:
            return made.err.strip() or "the clone at {} could not be made".format(clone.as_posix())
    got = git(runner, clone, "fetch", "--quiet", "--no-tags", url,
              "+refs/heads/{0}:refs/heads/{0}".format(BRANCH))
    return None if got.status == 0 else got.err.strip() or "git fetch exited {}".format(got.status)


def fetched_or_last_copy(runner, url, clone):
    error = fetch_error(runner, url, clone)
    commit = tip(runner, clone)
    if commit is None:
        raise refusal("remote Steering at {} could not be fetched, and this machine holds no copy of it: {}".format(
            url, error or "its {} branch is empty".format(BRANCH)))
    if error is None:
        return commit, None
    return commit, ("remote Steering at {} could not be fetched, so the copy last fetched, {}, is read, "
                    "and its text may be old: {}".format(url, commit[:7], error))


def held_file(home, session):
    return Path(home, USER_FOLDER, HELD, session + ".json")


def held(home, session):
    try:
        found = json.loads(held_file(home, session).read_text(encoding="utf-8"))
        return found["commit"], found.get("warning")
    except (OSError, ValueError, KeyError, TypeError):
        return None


# A Session holds the first commit it reads, so a push to the remote mid-Session never changes a later read.
def hold(home, session, commit, warning):
    path = held_file(home, session)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"commit": commit, "warning": warning}), encoding="utf-8")


def remote_of(runner, top, home, session):
    url = named_url(runner, top, home)
    if url is None:
        return None
    clone = Path(home, USER_FOLDER, CLONE)
    kept = held(home, session) if session else None
    if kept is not None:
        return Remote(clone, *kept)
    commit, warning = fetched_or_last_copy(runner, url, clone)
    if session:
        hold(home, session, commit, warning)
    return Remote(clone, commit, warning)
