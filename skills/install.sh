#!/usr/bin/env bash
# Symlink every skill in this repo's skills/ dir into ~/.claude/skills so Claude Code
# discovers them while the source of truth stays version-controlled here.
#
# Usage: bash skills/install.sh   (safe to re-run; refreshes existing symlinks)

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST_DIR="$HOME/.claude/skills"
mkdir -p "$DST_DIR"

for skill in "$SRC_DIR"/*/; do
  [ -f "$skill/SKILL.md" ] || continue
  name="$(basename "$skill")"
  link="$DST_DIR/$name"
  # Refresh an existing symlink; refuse to clobber a real directory.
  if [ -L "$link" ]; then rm "$link"
  elif [ -e "$link" ]; then echo "✗ $link exists and is not a symlink — skipping"; continue; fi
  ln -s "${skill%/}" "$link"
  echo "✓ linked $name -> ${skill%/}"
done

echo "Done. Run scripts/ensure-toolchain.sh if LaTeX tooling isn't installed yet."
