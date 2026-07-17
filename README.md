# Claude Cost Meter

A live, at-a-glance meter for what your **Claude Code** session is costing — in API-equivalent dollars — without leaving your workflow. Two surfaces of the same idea:

- **CLI statusline** — a line at the bottom of the Claude Code terminal (any OS).
- **macOS menu bar** — a [SwiftBar](https://swiftbar.app) plugin showing the **cost of today's work** (turns since local midnight) in the menu bar (visible over any app), with a per-session breakdown on click — each session shows both its today cost and its lifetime total, so a week-long session doesn't drown the day's number. Works whether you drive Claude from the **Claude Code CLI** or the **Claude desktop app** (both write their transcripts to the same place).

> **"API-equivalent"** = tokens × published Anthropic API prices, with correct prompt-cache tiers. On an API key it's your real spend; on a Pro/Max subscription it's the counterfactual ("what this *would* have cost") — a useful gauge of how hard you're leaning on the model.

> 🤖 **Installing with an AI assistant (Claude)?** Point it at this repo — it reads [`CLAUDE.md`](CLAUDE.md) automatically, which tells it to pick the right surface for you and handle the SwiftBar setup (including the dependency and the first-run folder gotcha).

## What it looks like

```
Opus · ≈$0.42 · ctx 18% · 5h 23% · 7d 41%        ← CLI statusline

≈$78.67                                           ← menu bar = today's work (click ↓)
  Today (since 00:00) · ≈$78.67 · 7 sessions
  Lifetime of those sessions · ≈$278.67
  ● Dark-mode dashboard toggle  ≈$28.61 today · ≈$28.61 total   ← hover a row ↓
       Model: opus-4-8 · Lifetime Main ≈$26.37 · Subagents ≈$2.24
       Tokens in 19.2K · out 201K · cache rd 12.2M · wr 1.4M
       Reveal transcript in Finder
  ○ CSV export refactor  ≈$23.69 today · ≈$183.69 total
  …                                                  (● live · ○ idle)
```

Session rows are named with the **same title the Claude desktop app shows** (including your renames), falling back to the first prompt for sessions the app doesn't know about (e.g. headless `claude -p` runs).

## Who can run it

- **CLI statusline (`cost-meter.py`)** — anyone using the **Claude Code CLI**, on macOS, Linux, or Windows. Python 3 standard library only; it just formats the JSON Claude Code already hands a statusline on stdin.
- **macOS menu bar (`claudecost.5s.py`)** — anyone on a **Mac** whose Claude sessions land under `~/.claude/projects/` (the Claude Code CLI *and* the Claude desktop app both do). Needs [SwiftBar](https://swiftbar.app) (free) + Python 3.

No accounts, no network calls, no secrets — both read only your local transcript files.

## Install

> **Pick one surface — most people want just one.** Using the **Claude Mac/desktop app**? Install the **macOS menu bar** version (below). Working in the **terminal**? The **CLI statusline** is simplest. Don't install the CLI one for a desktop-app user — its statusline won't appear anywhere they can see it.

### CLI statusline (any OS)

1. Copy `cost-meter.py` to `~/.claude/cost-meter.py` (or into `$CLAUDE_CONFIG_DIR/` if you've relocated your Claude config dir).
2. Add to that dir's `settings.json`:
   ```json
   {
     "statusLine": { "type": "command", "command": "python3 ~/.claude/cost-meter.py" }
   }
   ```

Claude Code pipes a JSON blob to the script on stdin (cost, context %, model, and — on Pro/Max — rolling-window quota). It renders after each turn in <60 ms.

### macOS menu bar

```bash
cd claude-cost-meter            # the cloned repo
./install-macos-menubar.sh      # installs SwiftBar if needed, sets it up, and launches it
```

The meter appears in your menu bar within a few seconds, showing the day's total across all your sessions.

## How it works

- The **statusline** version is *handed* the numbers on stdin by Claude Code — it just formats them. Fast, no parsing.
- The **menu-bar** version has no stdin, so it scans `~/.claude/projects/`, sums each turn's `usage` block (deduped by `requestId`) for the main loop **and** its subagents, and prices it with the table below — bucketing cost **per local calendar day using each turn's own timestamp**, not the file's mtime. The menu bar shows the cost of work since midnight; the dropdown lists each session with billable work today (● live / ○ idle) showing today + lifetime cost, with a hover submenu of details. Because "today" is decided by turn timestamps, merely *opening* an old chat in the desktop app (which touches the transcript file) doesn't drag it into the list. Session titles come from the desktop app's session store (`~/Library/Application Support/Claude/claude-code-sessions/`), matched by `cliSessionId`. It caches per file by mtime, so it only re-parses a session when it actually grows.

## Pricing table (keep this current)

Per million tokens. Cache read = 0.1× input · 5-min cache write = 1.25× · 1-hour cache write = 2×.

| Model      | Input | Output |
| ---------- | ----- | ------ |
| Fable 5    | $10   | $50    |
| Opus 4.x   | $5    | $25    |
| Sonnet 5   | $3    | $15    |
| Sonnet 4.x | $3    | $15    |
| Haiku 4.5  | $1    | $5     |

Edit `PRICES` in either script when Anthropic changes prices or ships new models.

## Caveats

- **API-equivalent**, not your literal bill on a subscription (see top).
- Depends on the current Claude Code transcript shape (`~/.claude/projects/**/*.jsonl` with per-turn `usage` + `requestId`). If that format changes, the menu-bar parser needs a tweak.
- Updates **per turn** (each completed reply), not token-by-token — only the process making the API call sees the live stream.
- The menu-bar version can't show the Pro/Max quota gauge (`5h`/`7d`) — that's only in the CLI's stdin payload, not in the transcript on disk.
- **Where it reads:** `$CLAUDE_CONFIG_DIR/projects` if you've set that variable, else `~/.claude/projects` — the plugin and installer both honor it, so a relocated config dir won't silently read empty.
- A model not in the pricing table is estimated at **Opus rates** and labelled *(unknown — est. at Opus)* in the dropdown — a brand-new model shows a flagged guess, not a silent wrong number.

## Customize

- **Colors:** `GOLD` / `DIM` near the top of `claudecost.5s.py` (menu bar); the CLI statusline `cost-meter.py` uses ANSI variables (`CY`/`GN`/`YL`/`RD`) just below its imports.
- **Refresh rate:** rename the SwiftBar plugin file — `claudecost.5s.py` → `claudecost.10s.py` for a 10-second poll, etc.

## License

MIT — see [LICENSE](LICENSE). © 2026 Nihar Kohirkar.
