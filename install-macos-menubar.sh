#!/usr/bin/env bash
# Install the Claude Cost Meter SwiftBar plugin (macOS menu bar).
# Idempotent; respects an existing SwiftBar plugin folder if you already have one.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

# Use SwiftBar's existing plugin dir if configured, else default to ~/.swiftbar/plugins
EXISTING="$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)"
DIR="${EXISTING:-$HOME/.swiftbar/plugins}"

mkdir -p "$DIR"
cp "$HERE/claudecost.5s.py" "$DIR/"
chmod +x "$DIR/claudecost.5s.py"

# Only set the plugin dir if SwiftBar didn't already have one (don't clobber a user's choice)
if [ -z "$EXISTING" ]; then
  defaults write com.ameba.SwiftBar PluginDirectory "$DIR"
fi

echo "Installed claudecost.5s.py -> $DIR"
if ! ls -d /Applications/SwiftBar.app >/dev/null 2>&1; then
  echo "SwiftBar isn't installed yet. Install it with:"
  echo "    brew install --cask swiftbar"
fi
echo "Then launch/relaunch SwiftBar:  open -a SwiftBar"
