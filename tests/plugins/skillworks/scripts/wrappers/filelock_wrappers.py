FILELOCK = '--with "filelock>=3.16"'


def runs_uv_with_filelock(text):
    lines = [line for line in text.splitlines() if "uv run" in line]
    return bool(lines) and all(FILELOCK in line for line in lines)


def wrappers_without_filelock(bin_folder):
    return sorted(path.name for path in bin_folder.iterdir()
                  if path.is_file() and not runs_uv_with_filelock(path.read_text(encoding="utf-8")))
