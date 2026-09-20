#!/usr/bin/env bash
#
# Run every shell test.
#
#   bash tests/scripts/run.sh

set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
status=0

for file in "$here"/*.test.sh; do
  printf '%s\n' "$(basename "$file")"
  bash "$file" || status=1
done

exit "$status"
