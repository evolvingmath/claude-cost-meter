# For Claude — installing this tool

You're probably reading this because someone asked you to install **Claude Cost Meter** for
them. This file is orientation + the known traps, so you can do it well and adapt to *their*
machine. `README.md` has the full picture; this is the "get it running without the usual
mistakes" brief. These are directions, not a script — understand the goal and adapt.

## What it is (so you install the right thing)
Two **independent** surfaces of the same meter. The user wants **one**, not both:
- **macOS menu bar** (`claudecost.5s.py`, runs in SwiftBar) — a cost readout in the menu bar,
  visible no matter which app is in front. **This is what someone using the Claude desktop /
  Mac app wants.**
- **CLI statusline** (`cost-meter.py`) — a line at the bottom of the **Claude Code terminal**.
  Only useful if they actually work in the terminal CLI.

## Do this FIRST: pick the surface — ask, don't assume
The most common mistake (don't repeat it): installing the **CLI** version for someone who uses
the **desktop app**. The statusline will be completely invisible to them.
- They use the **Claude Mac/desktop app** → install the **menu-bar** version. Do **not** also
  install the CLI one; it would do nothing for them.
- They work in the **terminal (Claude Code CLI)** → the **statusline** is simplest.
- **Unsure which they use? Ask them** before installing anything.

## CLI statusline — the easy one
Copy `cost-meter.py` to `~/.claude/cost-meter.py`, then merge into `~/.claude/settings.json`
(don't clobber existing keys):
```json
"statusLine": { "type": "command", "command": "python3 ~/.claude/cost-meter.py" }
```
That's it — it renders after each turn.

## Menu bar — one dependency and one trap; own both
The menu-bar version runs **inside SwiftBar**, a free macOS app. Two things bite people — handle
them, don't hand them back half-done:

1. **SwiftBar must be installed first — actually install it yourself.**
   `brew install --cask swiftbar` if Homebrew is present; otherwise download the notarized app
   from https://swiftbar.app and install it. Don't skip this step and don't just tell the user
   to do it.

2. **Avoid SwiftBar's first-run folder picker.** On first launch SwiftBar pops a Finder dialog
   asking for a "plugin folder," and it **rejects many locations with an error** — this is the
   confusing "could not be installed there" message people hit. The fix is to set the folder via
   `defaults` **before** launching SwiftBar, so the dialog never appears.

**The reliable path is to run the bundled installer**, which does all of the above (installs
SwiftBar via brew if missing, creates an owned plugin folder, copies the plugin, sets
`PluginDirectory` via `defaults`, then launches/relaunches SwiftBar):
```bash
./install-macos-menubar.sh
```
**Prefer it over launching SwiftBar by hand** — a manual launch is exactly what triggers the
folder-picker trap.

Doing it without the script? The order that avoids the trap is: install the SwiftBar app →
`mkdir -p ~/.swiftbar/plugins` → copy `claudecost.5s.py` there and `chmod +x` it →
`defaults write com.ameba.SwiftBar PluginDirectory ~/.swiftbar/plugins` → **then**
`open -a SwiftBar` (quit and reopen it if it was already running, so the setting takes effect).

## Verify before you declare success — don't assume it worked
- **Menu bar:** run `./claudecost.5s.py` directly; it should print a line starting with `≈$`.
  Then confirm SwiftBar is running, and tell the user exactly where to look — **the top-right of
  the menu bar, for a `≈$…` amount** (they may not recognize a SwiftBar item). You can't confirm
  the GUI render yourself; have them eyeball it.
- **CLI:** confirm the `statusLine` block is in `~/.claude/settings.json` and the user sees it in
  a Claude Code terminal.
- The meter reads `~/.claude/projects` (where both the CLI and the Mac app write transcripts).
  It also needs `python3` (standard-library only — `/usr/bin/python3` is fine, and that's what SwiftBar runs it with). A blank/`$0` **right after install** usually just means no Claude sessions **yet today**. A *persistent* `$0` across days means this user's Claude isn't writing transcripts to `~/.claude/projects` (or `python3` isn't resolving under SwiftBar's minimal environment) — surface that to the user; don't declare success on a `$0`.

## If something fails (these are all recoverable — adapt, don't give up)
- **"could not be installed in that location"** → you launched SwiftBar before setting
  `PluginDirectory`. Quit SwiftBar, run the installer (or `defaults write … PluginDirectory
  ~/.swiftbar/plugins`), relaunch.
- **Nothing in the menu bar** → SwiftBar not running, the plugin isn't executable, `python3`
  isn't found, or SwiftBar's plugin folder points somewhere else.
- **No Homebrew** → install SwiftBar from https://swiftbar.app by hand, then continue.
