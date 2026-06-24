#!/usr/bin/env bash
# Install the Claude Cost Meter SwiftBar plugin (macOS menu bar) — end to end.
# Installs SwiftBar if missing, sets the plugin folder BEFORE launch (this is what avoids
# SwiftBar's confusing first-run folder picker), copies the plugin, then (re)launches SwiftBar.
# Idempotent; respects an existing SwiftBar plugin folder if you already have one.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

# 1. Ensure SwiftBar is installed (do it — don't just suggest it).
if ! ls -d /Applications/SwiftBar.app >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installing SwiftBar via Homebrew…"
    brew install --cask swiftbar
  else
    echo "SwiftBar isn't installed and Homebrew isn't available."
    echo "Install SwiftBar (free, notarized) from https://swiftbar.app — then re-run this script."
    exit 1
  fi
fi

# 2. Plugin folder: reuse SwiftBar's existing one if set, else a dedicated folder we own.
EXISTING="$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)"
DIR="${EXISTING:-$HOME/.swiftbar/plugins}"
mkdir -p "$DIR"
cp "$HERE/claudecost.5s.py" "$DIR/"
chmod +x "$DIR/claudecost.5s.py"

# 3. Point SwiftBar at the folder BEFORE launching — this is what skips the first-run Finder
#    folder-picker that errors on many locations. (No-op when it already equals DIR.)
defaults write com.ameba.SwiftBar PluginDirectory "$DIR"

# 4. (Re)launch SwiftBar so the setting + plugin take effect.
osascript -e 'tell application "SwiftBar" to quit' >/dev/null 2>&1 || true
sleep 1
open -a SwiftBar

echo "Done — the meter should appear in your menu bar within a few seconds."
echo "Plugin: $DIR/claudecost.5s.py"
