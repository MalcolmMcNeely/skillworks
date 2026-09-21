#!/usr/bin/env bash
#
# Run every test of the scripts, in both languages.
#
#   bash tests/scripts/run.sh

set -uo pipefail

# A native form, because whether the shell converts one on the way out to uv is not set here.
here=$(cd "$(dirname "$0")" && { pwd -W 2>/dev/null || pwd; })
status=0

# First, because these finish in seconds and the shell tests take the best part of an hour.
#
# pytest is asked for on the command line, because the scripts carry no project file.
printf 'python tests\n'
uv run --with pytest pytest "$here" || status=1

for file in "$here"/*.test.sh; do
  printf '%s\n' "$(basename "$file")"
  bash "$file" || status=1
done

exit "$status"
