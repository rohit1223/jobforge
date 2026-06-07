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

# Can we run sudo without an interactive password prompt?
sudo_noninteractive() { sudo -n true >/dev/null 2>&1; }

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
    if sudo_noninteractive && brew install --cask basictex >/dev/null 2>&1; then
      eval "$(/usr/libexec/path_helper)" 2>/dev/null || true
      export PATH="/Library/TeX/texbin:$PATH"
      echo "✓ BasicTeX installed"
    else
      cat <<'EOF'
✗ Cannot install BasicTeX without an interactive sudo password.
  sudo needs a real TTY — Claude Code's `!` prompt does NOT provide one.
  Open a real terminal window (Terminal.app / iTerm) and run:

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

# --- tlmgr self-update (best effort, sudo) -----------------------------------
if have tlmgr && sudo_noninteractive; then
  sudo tlmgr update --self >/dev/null 2>&1 || true
fi

if [ "$need_user_action" -ne 0 ]; then
  exit 2
fi
echo "✓ toolchain ready"
exit 0
