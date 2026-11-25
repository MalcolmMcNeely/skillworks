# The Skillworks repo is a local bare repo, and git's own insteadOf sends the GitHub URL to it.

import json
import os

import pytest

from conftest import PLUGIN, Repo, git, launch, sidecar_steering, write_loop

SEEDED = PLUGIN / "skills" / "skillworks-setup" / "settings.json"

SKILLWORKS_URL = "https://github.com/MalcolmMcNeely/skillworks.git"

OLD = "1" * 40


@pytest.fixture
def repo(repo):
    write_loop(repo.work, "main")
    return repo


@pytest.fixture
def skillworks(tmp_path):
    return Repo(tmp_path / "skillworks")


def tip(skillworks):
    return git(skillworks.work, "rev-parse", "HEAD").strip()


def team_settings(root, ref=OLD, source=None):
    held = json.loads(SEEDED.read_text(encoding="utf-8"))
    marketplace = held["extraKnownMarketplaces"]["skillworks"]
    marketplace["source"] = source or dict(marketplace["source"], ref=ref)
    path = root / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def without_marketplace(root):
    path = team_settings(root)
    held = json.loads(path.read_text(encoding="utf-8"))
    del held["extraKnownMarketplaces"]
    path.write_text(json.dumps(held, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def ref_in(path):
    return json.loads(path.read_text(encoding="utf-8"))["extraKnownMarketplaces"]["skillworks"]["source"].get("ref")


def set_plugin_commit(repo, skillworks, *args):
    env = dict(os.environ, GIT_CONFIG_COUNT="1",
               GIT_CONFIG_KEY_0="url.{}.insteadOf".format(skillworks.origin.as_posix()),
               GIT_CONFIG_VALUE_0=SKILLWORKS_URL)
    return launch("set-plugin-commit", *args, where=repo.work, env=env)


def test_with_no_sha_the_pin_moves_to_the_tip_of_skillworks_main(repo, skillworks):
    path = team_settings(repo.work)
    skillworks.advance_origin("newer")
    git(skillworks.work, "pull", "--quiet", "origin", "main")

    ran = set_plugin_commit(repo, skillworks)

    assert (ran.status, ref_in(path)) == (0, tip(skillworks)), ran.err


def test_the_output_names_the_old_and_the_new_commit(repo, skillworks):
    team_settings(repo.work)

    ran = set_plugin_commit(repo, skillworks)

    assert ("old commit: " + OLD, "new commit: " + tip(skillworks)) == tuple(ran.out.splitlines()[:2]), ran.err


def test_a_full_sha_pins_that_commit(repo, skillworks):
    path = team_settings(repo.work)
    named = "2" * 40

    ran = set_plugin_commit(repo, skillworks, named)

    assert (ran.status, ref_in(path)) == (0, named), ran.err


@pytest.mark.parametrize("sha", ["2" * 7, "2" * 39, "g" * 40, "main"])
def test_a_short_or_malformed_sha_refuses_and_writes_nothing(repo, skillworks, sha):
    path = team_settings(repo.work)
    before = path.read_bytes()

    ran = set_plugin_commit(repo, skillworks, sha)

    assert (ran.status != 0, path.read_bytes(), "Nothing was written" in ran.err) == (True, before, True)


def test_a_folder_source_refuses_and_writes_nothing(repo, skillworks):
    path = team_settings(repo.work, source={"source": "directory", "path": "./plugins"})
    before = path.read_bytes()

    ran = set_plugin_commit(repo, skillworks)

    assert (ran.status != 0, path.read_bytes(), "folder source" in ran.err) == (True, before, True)


def test_a_source_that_is_not_github_refuses_and_names_its_own_kind(repo, skillworks):
    path = team_settings(repo.work, source={"source": "url", "url": "https://example.invalid/marketplace.json"})
    before = path.read_bytes()

    ran = set_plugin_commit(repo, skillworks)

    assert (ran.status != 0, path.read_bytes(), "a url source" in ran.err, "folder" in ran.err) == (
        True, before, True, False)


def test_settings_with_no_marketplace_refuse_and_write_nothing(repo, skillworks):
    path = without_marketplace(repo.work)
    before = path.read_bytes()

    ran = set_plugin_commit(repo, skillworks)

    assert (ran.status != 0, path.read_bytes(), "no Marketplace" in ran.err) == (True, before, True)


def test_no_settings_file_refuses_and_writes_nothing(repo, skillworks):
    ran = set_plugin_commit(repo, skillworks)

    assert (ran.status != 0, (repo.work / ".claude").exists(), "no Marketplace" in ran.err) == (True, False, True)


def test_under_sidecar_steering_the_sidecar_s_settings_take_the_pin(repo, skillworks):
    sidecar = sidecar_steering(repo)
    shared = team_settings(sidecar)
    own = team_settings(repo.work)

    ran = set_plugin_commit(repo, skillworks)

    assert (ran.status, ref_in(shared), ref_in(own)) == (0, tip(skillworks), OLD), ran.err


def test_nothing_is_committed(repo, skillworks):
    team_settings(repo.work)
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "--quiet", "-m", "Settings")
    head = git(repo.work, "rev-parse", "HEAD")

    set_plugin_commit(repo, skillworks)

    assert (git(repo.work, "rev-parse", "HEAD"), git(repo.work, "status", "--porcelain")) == (
        head, " M .claude/settings.json\n")


def test_only_the_ref_changes_and_the_layout_stays(repo, skillworks):
    path = team_settings(repo.work)
    before = path.read_text(encoding="utf-8")

    set_plugin_commit(repo, skillworks)

    assert path.read_text(encoding="utf-8") == before.replace(OLD, tip(skillworks))
