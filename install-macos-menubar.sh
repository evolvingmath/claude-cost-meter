#!/usr/bin/env bash
# Install the Claude Cost Meter SwiftBar plugin (macOS menu bar) — end to end.
# - installs SwiftBar if missing (detected anywhere, not just /Applications)
# - pins the plugin to a real python3 (SwiftBar runs plugins under a minimal PATH)
# - records the Claude config dir (honors $CLAUDE_CONFIG_DIR) so the plugin finds transcripts
# - sets the plugin folder BEFORE launch (avoids SwiftBar's first-run folder picker)
# - (re)launches SwiftBar
# Idempotent; respects an existing SwiftBar plugin folder.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

# 1. Ensure SwiftBar is installed — detect it anywhere it's registered, not just /Applications.
if ! osascript -e 'id of application "SwiftBar"' >/dev/null 2>&1; then
  BREW="$(command -v brew || true)"
  for cand in /opt/homebrew/bin/brew /usr/local/bin/brew; do          # Apple-Silicon vs Intel
    [ -z "$BREW" ] && [ -x "$cand" ] && BREW="$cand"
  done
  if [ -n "$BREW" ]; then
    echo "Installing SwiftBar via Homebrew…"
    "$BREW" install --cask swiftbar
  else
    echo "SwiftBar isn't installed and Homebrew isn't available."
    echo "Install SwiftBar (free, notarized) from https://swiftbar.app — then re-run this script."
    exit 1
  fi
fi

# 2. Find a real python3. SwiftBar launches plugins with a minimal PATH, so we can't rely on
#    `env python3` resolving — we pin the shebang to an absolute interpreter below.
PY="$(command -v python3 || true)"
for cand in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  [ -z "$PY" ] && [ -x "$cand" ] && PY="$cand"
done
if [ -z "$PY" ]; then
  echo "python3 not found. Install it (e.g. 'xcode-select --install') and re-run."
  exit 1
fi

# 3. Plugin folder: reuse SwiftBar's existing one if set, else a dedicated folder we own.
EXISTING="$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)"
DIR="${EXISTING:-$HOME/.swiftbar/plugins}"
mkdir -p "$DIR"
cp "$HERE/claudecost.5s.py" "$DIR/"
chmod +x "$DIR/claudecost.5s.py"
sed -i '' "1s|^#!.*|#!$PY|" "$DIR/claudecost.5s.py"   # pin interpreter for SwiftBar's minimal env

# 4. Record the Claude config dir so the plugin finds transcripts even if it's relocated.
#    SwiftBar's minimal env won't carry $CLAUDE_CONFIG_DIR, so capture it here (the shell has it)
#    into a sidecar the plugin reads.
CLAUDE_BASE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
mkdir -p "$HOME/.config/claude-cost-meter"
printf '%s\n' "$CLAUDE_BASE" > "$HOME/.config/claude-cost-meter/config"

# 5. Point SwiftBar at the folder BEFORE launching — skips the first-run Finder folder picker
#    that errors on many locations. (No-op when it already equals DIR.)
defaults write com.ameba.SwiftBar PluginDirectory "$DIR"

# 6. (Re)launch SwiftBar so the setting + plugin take effect.
osascript -e 'tell application "SwiftBar" to quit' >/dev/null 2>&1 || true
sleep 1
open -a SwiftBar

echo "Done — the meter should appear in your menu bar within a few seconds."
echo "Plugin:      $DIR/claudecost.5s.py   (python: $PY)"
echo "Claude data: $CLAUDE_BASE/projects"
