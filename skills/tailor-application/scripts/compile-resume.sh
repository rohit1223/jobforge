#!/usr/bin/env bash
# Compile a tailored resume .tex -> .pdf, auto-installing missing LaTeX packages,
# and warn if the result exceeds one page.
#
# Usage: compile-resume.sh <path/to/resume-tailored.tex>
#
# Exit codes:
#   0  PDF produced (check stdout for a >1-page warning)
#   2  a missing package needs sudo tlmgr install (commands printed for the user)
#   1  compile failed for another reason (log tail printed); no PDF kept

set -uo pipefail

TEX="${1:?usage: compile-resume.sh <file.tex>}"
[ -f "$TEX" ] || { echo "✗ not found: $TEX"; exit 1; }

DIR="$(cd "$(dirname "$TEX")" && pwd)"
BASE="$(basename "$TEX" .tex)"
PDF="$DIR/$BASE.pdf"
LOG="$DIR/$BASE.log"

# Put a possible BasicTeX on PATH for this shell.
[ -x /usr/libexec/path_helper ] && eval "$(/usr/libexec/path_helper)" 2>/dev/null || true
export PATH="/Library/TeX/texbin:$PATH"

command -v pdflatex >/dev/null 2>&1 || { echo "✗ pdflatex not on PATH — run ensure-toolchain.sh first"; exit 1; }

have_tlmgr() { command -v tlmgr >/dev/null 2>&1; }
sudo_noninteractive() { sudo -n true >/dev/null 2>&1; }

run_pdflatex() {
  # -interaction=nonstopmode so a missing file fails fast instead of prompting.
  ( cd "$DIR" && pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$BASE.tex" ) >/dev/null 2>&1
}

# Pull the first missing .sty/.cls name out of the log, if any.
missing_file() {
  grep -ohE "File \`[^']+\.(sty|cls)' not found|! LaTeX Error: File \`[^']+\.(sty|cls)' not found" "$LOG" 2>/dev/null \
    | grep -oE "[A-Za-z0-9._-]+\.(sty|cls)" | head -1
}

MAX_TRIES=12
for ((i=1; i<=MAX_TRIES; i++)); do
  if run_pdflatex; then
    break
  fi
  miss="$(missing_file)"
  if [ -z "$miss" ]; then
    echo "✗ compile failed (not a missing-package error). Last log lines:"
    tail -25 "$LOG" 2>/dev/null
    rm -f "$PDF"
    exit 1
  fi

  echo "→ missing LaTeX file: $miss — resolving via tlmgr…"
  if ! have_tlmgr; then
    echo "✗ tlmgr not available; cannot auto-install $miss."; exit 1
  fi
  pkg="$(tlmgr search --global --file "/$miss" 2>/dev/null | grep -vE '^(tlmgr|search)' | head -1 | cut -d: -f1 | tr -d ' ')"
  pkg="${pkg:-${miss%.*}}"

  if sudo_noninteractive; then
    sudo tlmgr install "$pkg" >/dev/null 2>&1 || { echo "✗ tlmgr install $pkg failed"; exit 1; }
    echo "  ✓ installed $pkg"
  else
    cat <<EOF
✗ Installing LaTeX package '$pkg' (for $miss) needs sudo, which requires a real
  terminal (Claude Code's '!' prompt has no TTY for sudo). In Terminal.app / iTerm:

    sudo tlmgr install $pkg

  Then re-run the compile. (Tip: a one-time 'sudo chown -R \$(whoami) <texlive-root>'
  lets the agent install future packages without sudo.)

EOF
    exit 2
  fi
done

# Run twice more so section rules / refs settle.
run_pdflatex >/dev/null 2>&1 || true

[ -f "$PDF" ] || { echo "✗ no PDF produced. Log tail:"; tail -25 "$LOG"; exit 1; }

# --- 1-page guard ------------------------------------------------------------
pages=""
if command -v pdfinfo >/dev/null 2>&1; then
  pages="$(pdfinfo "$PDF" 2>/dev/null | awk '/^Pages:/{print $2}')"
fi
if [ -z "$pages" ] && command -v mdls >/dev/null 2>&1; then
  pages="$(mdls -name kMDItemNumberOfPages -raw "$PDF" 2>/dev/null)"
fi
# Fallback: pdflatex records the page count in its own log (no extra tools needed).
if { [ -z "$pages" ] || [ "$pages" = "(null)" ]; } && [ -f "$LOG" ]; then
  pages="$(grep -oE "Output written on [^ ]+ \(([0-9]+) page" "$LOG" 2>/dev/null | grep -oE "[0-9]+" | tail -1)"
fi

echo "✓ PDF: $PDF"
if [ -n "$pages" ] && [ "$pages" != "(null)" ]; then
  if [ "$pages" -gt 1 ] 2>/dev/null; then
    echo "⚠ PDF is $pages pages — ATS guidance favors 1 page. Consider trimming."
  else
    echo "✓ 1 page"
  fi
else
  echo "ℹ page count unavailable (no pdfinfo/mdls); verify length manually."
fi

# --- ATS text extraction -------------------------------------------------------
# Emit the text an ATS would parse so keyword survival can be verified.
if command -v pdftotext >/dev/null 2>&1; then
  TXT="$DIR/$BASE.txt"
  if pdftotext -layout "$PDF" "$TXT" 2>/dev/null; then
    echo "✓ ATS text extraction: $TXT — verify MUST keywords survived"
  else
    echo "ℹ pdftotext failed; skipping ATS text extraction."
  fi
else
  echo "ℹ pdftotext not found — 'brew install poppler' to enable the ATS text check."
fi
exit 0
