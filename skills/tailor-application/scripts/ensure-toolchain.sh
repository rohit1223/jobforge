#!/usr/bin/env bash
# Ensure the resume toolchain is present: pandoc + a LaTeX engine (pdflatex/tlmgr).
#
# Exit codes:
#   0  everything present (or installed without sudo)
#   2  user action required — sudo-needing install printed for the user to run via `!`
#   1  unexpected error
#
# Design note: pandoc installs without sudo. BasicTeX (a macOS .pkg) and `tlmgr install`
# need sudo, which a non-interactive agent cannot answer. When sudo isn't usable we print
# the exact `!`-prefixed commands for the user and exit 2.

set -uo pipefail

need_user_action=0

have() { command -v "$1" >/dev/null 2>&1; }

# GUI askpass so sudo works without a TTY (Claude Code's Bash tool / ! prompt have
# none). On macOS, sudo -A pops a password dialog via askpass.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASKPASS="$SCRIPT_DIR/askpass.sh"
[ "$(uname)" = "Darwin" ] && [ -x "$ASKPASS" ] && export SUDO_ASKPASS="$ASKPASS"

# Run sudo non-interactively if a credential is cached, else via the GUI askpass
# (sudo -A). Non-zero if neither works.
run_sudo() {
  if sudo -n true 2>/dev/null; then sudo "$@"; return; fi
  if [ -n "${SUDO_ASKPASS:-}" ]; then SUDO_ASKPASS="$ASKPASS" sudo -A "$@"; return; fi
  return 1
}

# --- pandoc (no sudo) --------------------------------------------------------
if have pandoc; then
  echo "✓ pandoc $(pandoc --version | head -1 | awk '{print $2}')"
else
  if have brew; then
    echo "→ installing pandoc via Homebrew…"
    if brew install pandoc >/dev/null 2>&1; then
      echo "✓ pandoc installed"
    else
      echo "✗ pandoc install failed — run: ! brew install pandoc"
      need_user_action=1
    fi
  else
    echo "✗ Homebrew not found. Install from https://brew.sh, then re-run."
    need_user_action=1
  fi
fi

# --- poppler / pdftotext (no sudo, recommended) ------------------------------
# Provides pdftotext (ATS keyword-survival check + PDF notes/import) and pdfinfo
# (page count). Optional: features degrade gracefully without it, so a failure
# here does not block the toolchain.
if have pdftotext; then
  echo "✓ pdftotext present"
elif have brew; then
  echo "→ installing poppler (pdftotext/pdfinfo) via Homebrew…"
  if brew install poppler >/dev/null 2>&1; then
    echo "✓ poppler installed"
  else
    echo "ℹ poppler install failed — run: ! brew install poppler (ATS text check will be skipped)"
  fi
else
  echo "ℹ Homebrew not found — skipping poppler (ATS text check will be skipped)."
fi

# --- LaTeX engine (sudo) -----------------------------------------------------
# Make sure a prior basictex install is on PATH for this shell.
if ! have pdflatex && [ -x /usr/libexec/path_helper ]; then
  eval "$(/usr/libexec/path_helper)" 2>/dev/null || true
  export PATH="/Library/TeX/texbin:$PATH"
fi

if have pdflatex; then
  echo "✓ pdflatex ($(pdflatex --version | head -1))"
else
  if have brew; then
    echo "→ BasicTeX needs sudo to install its .pkg."
    # Pre-authorize sudo once (GUI dialog) so brew's own internal sudo runs
    # non-interactively against the cached credential.
    if run_sudo -v 2>/dev/null && brew install --cask basictex >/dev/null 2>&1; then
      eval "$(/usr/libexec/path_helper)" 2>/dev/null || true
      export PATH="/Library/TeX/texbin:$PATH"
      echo "✓ BasicTeX installed"
    else
      cat <<'EOF'
✗ Could not install BasicTeX. Tried a GUI sudo password prompt (sudo -A askpass)
  but it didn't go through (cancelled, or no GUI session). Open a real terminal
  (Terminal.app / iTerm) and run:

    brew install --cask basictex

  Enter your Mac password when prompted, then return and re-run the compile step.
EOF
      need_user_action=1
    fi
  else
    echo "✗ Homebrew not found — cannot install BasicTeX."
    need_user_action=1
  fi
fi

# --- tlmgr self-update (best effort; only if sudo is already cached, no dialog) ---
if have tlmgr && sudo -n true 2>/dev/null; then
  sudo tlmgr update --self >/dev/null 2>&1 || true
fi

if [ "$need_user_action" -ne 0 ]; then
  exit 2
fi
echo "✓ toolchain ready"
exit 0
