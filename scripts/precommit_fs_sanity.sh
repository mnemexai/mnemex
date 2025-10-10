#!/usr/bin/env bash
set -euo pipefail

# Detect duplicate-like filenames with trailing numbers (e.g., "file 2.md")
# Scans tracked files to catch OS/copy artifacts before commit.

dupes=$(git ls-files | grep -E ' [0-9]+(\.|$)' || true)

if [ -n "${dupes}" ]; then
  echo "Filesystem sanity check failed: found suspicious duplicate filenames:" >&2
  echo "${dupes}" >&2
  echo >&2
  echo "Rename or remove these files before committing." >&2
  exit 1
fi

exit 0

