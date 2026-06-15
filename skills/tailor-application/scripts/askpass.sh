#!/usr/bin/env bash
# SUDO_ASKPASS helper for `sudo -A`.
#
# Claude Code's Bash tool and the `!` inline prompt have no TTY, so plain `sudo`
# fails with "a terminal is required to read the password". This helper lets
# `sudo -A` obtain the password from a macOS GUI dialog instead: sudo runs this
# program as the invoking user and reads the password from its stdout.
#
# Used by ensure-toolchain.sh / compile-resume.sh via their run_sudo() helper.
# On a non-macOS or headless session osascript fails, this prints nothing, sudo
# gets an empty password and fails, and the caller falls back to printed steps.
exec osascript \
  -e 'display dialog "JobForge needs your macOS password to install LaTeX components with sudo." with title "JobForge — sudo" default answer "" with hidden answer with icon caution giving up after 120' \
  -e 'text returned of result' 2>/dev/null
