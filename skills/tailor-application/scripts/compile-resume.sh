#!/usr/bin/env bash
# Compile a tailored resume .tex -> .pdf, auto-installing missing LaTeX packages,
# and warn if the result exceeds one page.
#
# Usage: compile-resume.sh <path/to/resume-tailored.tex> [output-basename]
#   output-basename (optional): name the deliverable PDF/txt, e.g.
#   "RohitKumar_SSDE_resume" -> RohitKumar_SSDE_resume.pdf + .txt in the same dir.
#   Omitted -> the PDF/txt keep the .tex basename (back-compatible).
#
# Exit codes:
#   0  PDF produced (check stdout for a >1-page warning)
#   2  a missing package needs sudo tlmgr install (commands printed for the user)
#   3  contact block failed ATS extraction (junk bytes, or email/profile URLs
#      missing from the extracted text); PDF kept so the header can be inspected
#   1  compile failed for another reason (log tail printed); no PDF kept

set -uo pipefail

TEX="${1:?usage: compile-resume.sh <file.tex>}"
[ -f "$TEX" ] || { echo "✗ not found: $TEX"; exit 1; }

DIR="$(cd "$(dirname "$TEX")" && pwd)"
BASE="$(basename "$TEX" .tex)"
OUTBASE="${2:-$BASE}"      # optional deliverable name (e.g. RohitKumar_SSDE_resume)
TEXPDF="$DIR/$BASE.pdf"    # what pdflatex writes (from $BASE.tex)
PDF="$DIR/$OUTBASE.pdf"    # final deliverable path (== TEXPDF when no override)
LOG="$DIR/$BASE.log"

# Put a possible BasicTeX on PATH for this shell.
[ -x /usr/libexec/path_helper ] && eval "$(/usr/libexec/path_helper)" 2>/dev/null || true
export PATH="/Library/TeX/texbin:$PATH"

command -v pdflatex >/dev/null 2>&1 || { echo "✗ pdflatex not on PATH — run ensure-toolchain.sh first"; exit 1; }

have_tlmgr() { command -v tlmgr >/dev/null 2>&1; }

# GUI askpass so sudo works without a TTY (Claude Code's Bash tool / ! prompt have
# none). On macOS, sudo -A pops a password dialog via askpass.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASKPASS="$SCRIPT_DIR/askpass.sh"
[ "$(uname)" = "Darwin" ] && [ -x "$ASKPASS" ] && export SUDO_ASKPASS="$ASKPASS"

# Run sudo non-interactively if a credential is cached, else via the GUI askpass
# (sudo -A). Non-zero if neither works, so the caller can print manual steps.
run_sudo() {
  if sudo -n true 2>/dev/null; then sudo "$@"; return; fi
  if [ -n "${SUDO_ASKPASS:-}" ]; then SUDO_ASKPASS="$ASKPASS" sudo -A "$@"; return; fi
  return 1
}

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
    rm -f "$TEXPDF"
    exit 1
  fi

  echo "→ missing LaTeX file: $miss — resolving via tlmgr…"
  if ! have_tlmgr; then
    echo "✗ tlmgr not available; cannot auto-install $miss."; exit 1
  fi
  pkg="$(tlmgr search --global --file "/$miss" 2>/dev/null | grep -vE '^(tlmgr|search)' | head -1 | cut -d: -f1 | tr -d ' ')"
  pkg="${pkg:-${miss%.*}}"

  if run_sudo tlmgr install "$pkg" >/dev/null 2>&1; then
    echo "  ✓ installed $pkg"
  else
    cat <<EOF
✗ Installing LaTeX package '$pkg' (for $miss) needs sudo. Tried a GUI password
  prompt (sudo -A askpass) but it didn't go through. In Terminal.app / iTerm:

    sudo tlmgr install $pkg

  Then re-run the compile. (Tip: a one-time 'sudo chown -R \$(whoami) <texlive-root>'
  lets future installs skip sudo entirely.)

EOF
    exit 2
  fi
done

# Run twice more so section rules / refs settle.
run_pdflatex >/dev/null 2>&1 || true

[ -f "$TEXPDF" ] || { echo "✗ no PDF produced. Log tail:"; tail -25 "$LOG"; exit 1; }

# Rename to the requested deliverable name, if one was given.
if [ "$OUTBASE" != "$BASE" ]; then
  mv -f "$TEXPDF" "$PDF"
fi

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
if ! command -v pdftotext >/dev/null 2>&1; then
  echo "ℹ pdftotext not found — 'brew install poppler' to enable the ATS text check."
  exit 0
fi

TXT="$DIR/$OUTBASE.txt"
rm -f "$TXT"   # never leave a stale extraction backing the ATS self-check
if ! pdftotext -layout "$PDF" "$TXT" 2>/dev/null; then
  echo "✗ pdftotext failed — no ATS text produced, keyword survival cannot be verified."
  exit 1
fi
echo "✓ ATS text extraction: $TXT — verify MUST keywords survived"

# --- Contact-block extraction check --------------------------------------------
# An ATS builds the candidate profile from the header. Two shipped failure modes
# this guards against: icon glyphs that extract as junk/control bytes, and profile
# URLs that live only in \href targets (invisible to text extraction). The visible
# header text must carry the real email and full profile URLs.
HEADER="$(head -5 "$TXT")"
contact_fail=0

# Control bytes: C0 controls (minus tab/newline/CR), DEL, and UTF-8-encoded C1
# controls (\xc2\x80-\x9f — the icon-glyph residue). Accented names (\xc3+) pass.
# Range starts at \x01: bash cannot pass a NUL byte in an argument anyway.
if printf '%s' "$HEADER" | LC_ALL=C grep -q -e $'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]' -e $'\xc2[\x80-\x9f]'; then
  echo "✗ contact block: non-printable junk bytes in the extracted header (icon glyphs?)."
  contact_fail=1
fi

if ! printf '%s' "$HEADER" | grep -Eq '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'; then
  echo "✗ contact block: no email address in the extracted header."
  contact_fail=1
fi

# Require each profile URL in the extracted text only if the .tex links to it —
# otherwise the URL exists solely as an \href target an ATS never sees.
for domain in 'linkedin.com/in/' 'github.com/'; do
  if grep -q "$domain" "$TEX" && ! printf '%s' "$HEADER" | grep -q "$domain"; then
    echo "✗ contact block: $domain is linked in the .tex but absent from the extracted header — make the visible link text the full URL."
    contact_fail=1
  fi
done

if [ "$contact_fail" -ne 0 ]; then
  echo "✗ contact check FAILED — an ATS cannot reliably build the candidate profile from this header. Extracted header:"
  printf '%s\n' "$HEADER" | cat -v | sed 's/^/    /'
  exit 3
fi
echo "✓ contact block extracts cleanly (email + profile URLs present, no junk bytes)"
exit 0
