#!/usr/bin/env bash
# scaffold.sh — create your private JobForge workspace from the tracked examples/.
#
# JobForge's skills read/write data relative to the directory you launch Claude
# Code from: master/, applications/, interview-prep/. Those dirs are gitignored
# (your resume + applications never get published). This script seeds them from
# examples/ so a fresh clone has a working skeleton. Safe to re-run: it never
# overwrites a file that already exists.
#
# Usage: bash scaffold.sh [target-dir]   (defaults to the current directory)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/examples"
DST="${1:-$PWD}"

[ -d "$SRC" ] || { echo "✗ examples/ not found at $SRC"; exit 1; }

copied=0 skipped=0
while IFS= read -r -d '' f; do
  rel="${f#"$SRC"/}"
  # Drop the ".example" infix so resume.example.tex -> resume.tex, etc.
  out="$DST/${rel//.example/}"
  if [ -e "$out" ]; then
    echo "• skip (exists): ${out#"$DST"/}"; skipped=$((skipped+1)); continue
  fi
  mkdir -p "$(dirname "$out")"
  cp "$f" "$out"
  echo "✓ created:       ${out#"$DST"/}"; copied=$((copied+1))
done < <(find "$SRC" -type f -print0)

# Ensure the empty working dirs the skills write into exist.
mkdir -p "$DST/interview-prep/notes" "$DST/interview-prep/topics"

echo ""
echo "Done — $copied created, $skipped skipped."
echo "Next: replace master/resume.tex with your own resume, then ask Claude Code"
echo "(launched from $DST) to 'tailor my resume to <job-url>'."
