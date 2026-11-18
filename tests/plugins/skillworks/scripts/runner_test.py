# Linux will not start a file with no execute bit, so there it stands in for a bash file Windows cannot.

import os

import pytest

from runner import NOT_FOUND, Subprocess

COMMAND = "made-command"


@pytest.fixture
def on_path(tmp_path, monkeypatch):
    folder = tmp_path / "bin"
    folder.mkdir()
    monkeypatch.setenv("PATH", str(folder) + os.pathsep + os.environ.get("PATH", ""))
    return folder


def bash_file(folder, name=COMMAND):
    (folder / name).write_bytes(b"echo started through bash\n")


def test_on_windows_a_command_with_no_extension_on_path_is_found(on_path):
    bash_file(on_path)

    assert Subprocess(windows=True).found(COMMAND)


def test_on_windows_a_command_with_no_extension_on_path_starts_through_bash(on_path, tmp_path):
    bash_file(on_path)

    ran = Subprocess(windows=True).run([COMMAND], tmp_path)

    assert (ran.status, ran.out) == (0, "started through bash\n")


@pytest.mark.parametrize("windows", [True, False], ids=["windows", "elsewhere"])
def test_a_command_on_path_nowhere_is_not_found(on_path, tmp_path, windows):
    ran = Subprocess(windows=windows).run([COMMAND], tmp_path)

    assert ran.status == NOT_FOUND


# Only a start without bash runs Python, and Windows would read the file as batch, not by its shebang.
@pytest.mark.skipif(os.name == "nt", reason="Windows does not read a shebang")
def test_on_windows_a_command_with_an_extension_starts_by_itself(on_path, tmp_path):
    started = on_path / "made-command.cmd"
    started.write_text("#!/usr/bin/env python3\nprint('started by itself')\n", encoding="utf-8")
    started.chmod(0o755)

    ran = Subprocess(windows=True).run([started.name], tmp_path)

    assert (ran.status, ran.out) == (0, "started by itself\n")


@pytest.mark.skipif(os.name == "nt", reason="the case is what Linux and macOS do")
def test_elsewhere_a_file_with_no_execute_bit_is_not_found(on_path):
    bash_file(on_path)

    assert not Subprocess(windows=False).found(COMMAND)
