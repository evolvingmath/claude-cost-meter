#!/usr/bin/env python3
# <xbar.title>Claude Cost Meter</xbar.title>
# <xbar.version>1.1.0</xbar.version>
# <xbar.author>Nihar Kohirkar</xbar.author>
# <xbar.author.github>evolvingmath</xbar.author.github>
# <xbar.desc>Live API-equivalent cost of today's Claude work (CLI + Mac app).</xbar.desc>
# <swiftbar.refreshOnOpen>true</swiftbar.refreshOnOpen>
"""
SwiftBar plugin — API-equivalent cost of today's Claude work.

Menu bar : ≈$<cost of turns since local midnight>  (adaptive color -> legible on any wallpaper)
Dropdown : one row per session with billable work today (● live / ○ idle), each showing
           today's cost AND the session's lifetime total; hover a row for its detail submenu.

"Today" is decided by each turn's own timestamp, not the file's mtime — so a week-long
session shows only what it burned since midnight, and merely *opening* an old chat in the
desktop app (which touches the file) doesn't drag it into the list.

Session names come from the desktop app's session store (the same title you see/rename in
the GUI), falling back to the first prompt for sessions the app doesn't know about.

Reads (CLAUDE_CONFIG_DIR or ~/.claude)/projects — the CLI *and* the Mac app write there. Sums
each turn's usage (deduped by requestId) for the main loop + its subagents, priced at published
API rates with correct cache tiers. Per-file cache keyed by mtime -> only re-parses a session
when it actually grows. Standalone (no third-party deps).

Author: Nihar Kohirkar. MIT.
"""
import os, json, glob, time, datetime, tempfile

def _claude_base():
    # Claude Code lets users relocate ~/.claude via CLAUDE_CONFIG_DIR. The env var is visible
    # when run from the CLI/statusline; SwiftBar's minimal env is not, so fall back to a sidecar
    # the installer writes, then to the default.
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        return os.path.expanduser(env)
    try:
        with open(os.path.expanduser("~/.config/claude-cost-meter/config")) as f:
            p = f.read().strip()
            if p:
                return os.path.expanduser(p)
    except Exception:
        pass
    return os.path.expanduser("~/.claude")

PROJ = os.path.join(_claude_base(), "projects")
# The desktop app's per-session metadata (title, cliSessionId) — where GUI names/renames live.
APP_SESS = os.path.expanduser("~/Library/Application Support/Claude/claude-code-sessions")
# per-user temp (macOS $TMPDIR is private per user) — avoids /tmp collisions on shared machines
CACHE = os.path.join(tempfile.gettempdir(), f"claude_costmeter_cache_{os.getuid()}.json")
GOLD = "#9D7E2F"; DIM = "#8A8A8A"
LIVE_WINDOW = 120  # seconds since last write to count a session as "live"

# per-token USD (input, output); cache_read=0.1x in, write5m=1.25x in, write1h=2.0x in
PRICES = {
    "claude-fable-5": (10e-6, 50e-6),
    "claude-opus-4-8": (5e-6, 25e-6), "claude-opus-4-7": (5e-6, 25e-6),
    "claude-opus-4-6": (5e-6, 25e-6), "claude-opus-4-5": (5e-6, 25e-6),
    "claude-sonnet-5": (3e-6, 15e-6),  # standard rate (intro $2/$10 through 2026-08 not modeled)
    "claude-sonnet-4-6": (3e-6, 15e-6), "claude-sonnet-4-5": (3e-6, 15e-6),
    "claude-haiku-4-5": (1e-6, 5e-6),
}
def rate(m): return PRICES.get((m or "").strip(), PRICES["claude-opus-4-8"])

def _local_day(ts):
    """ISO UTC timestamp -> local calendar date string (day buckets survive midnight in cache)."""
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date().isoformat()
    except Exception:
        return "unknown"

def parse(path):
    """Dedupe by requestId; return (days{local_date: cost}, tin, tout, tcr, tcw, top_model)."""
    turns = {}
    try:
        with open(path) as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("type") != "assistant":
                    continue
                msg = o.get("message", {}) or {}
                u = msg.get("usage") or {}
                rid = o.get("requestId")
                if not u or not rid:
                    continue
                cc = u.get("cache_creation") or {}
                inp = u.get("input_tokens", 0) or 0
                out = u.get("output_tokens", 0) or 0
                cr = u.get("cache_read_input_tokens", 0) or 0
                if cc:
                    c5 = cc.get("ephemeral_5m_input_tokens", 0) or 0
                    c1 = cc.get("ephemeral_1h_input_tokens", 0) or 0
                else:
                    c5 = u.get("cache_creation_input_tokens", 0) or 0; c1 = 0
                tot = inp + out + cr + c5 + c1
                prev = turns.get(rid)
                if prev is None or tot > prev[6]:
                    turns[rid] = (msg.get("model"), inp, out, cr, c5, c1, tot, o.get("timestamp") or "")
    except Exception:
        return ({}, 0, 0, 0, 0, None)
    days = {}
    tin = tout = tcr = tcw = 0
    bym = {}
    for m, inp, out, cr, c5, c1, _, ts in turns.values():
        bi, bo = rate(m)
        d = _local_day(ts)
        days[d] = days.get(d, 0.0) + inp*bi + out*bo + cr*0.1*bi + c5*1.25*bi + c1*2.0*bi
        tin += inp; tout += out; tcr += cr; tcw += c5 + c1
        bym[m] = bym.get(m, 0) + 1
    return (days, tin, tout, tcr, tcw, (max(bym, key=bym.get) if bym else None))

def first_prompt(path):
    try:
        with open(path) as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("type") == "user":
                    c = (o.get("message", {}) or {}).get("content")
                    if isinstance(c, str) and c.strip():
                        return c.strip().splitlines()[0][:42]
                    if isinstance(c, list):
                        for b in c:
                            if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                                return b["text"].strip().splitlines()[0][:42]
    except Exception:
        pass
    return ""

def session_cost(path):
    """Main loop + its subagents for one session file, cost bucketed per local day."""
    days, tin, tout, tcr, tcw, top = parse(path)
    main_cost = sum(days.values())
    sid = os.path.splitext(os.path.basename(path))[0]
    sub = 0.0
    subdir = os.path.join(os.path.dirname(path), sid, "subagents")
    for af in glob.glob(os.path.join(subdir, "**", "agent-*.jsonl"), recursive=True):
        sd = parse(af)[0]
        for d, c in sd.items():
            days[d] = days.get(d, 0.0) + c
        sub += sum(sd.values())
    return {"days": days, "main": main_cost, "sub": sub, "tin": tin, "tout": tout,
            "tcr": tcr, "tcw": tcw, "top": top, "prompt": first_prompt(path)}

def gui_titles(prev):
    """cliSessionId -> the title shown in the desktop app (incl. renames).
    Incrementally cached by metadata-file mtime; returns (map, fresh_cache)."""
    prev = prev if isinstance(prev, dict) else {}
    fresh = {}
    for p in glob.glob(os.path.join(APP_SESS, "*", "*", "local_*.json")):
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        c = prev.get(p)
        if c and c.get("mtime") == mt:
            fresh[p] = c
            continue
        rec = {"mtime": mt, "sid": None, "title": "", "act": 0}
        try:
            with open(p) as f:
                o = json.load(f)
            rec.update(sid=o.get("cliSessionId"), title=(o.get("title") or "").strip(),
                       act=o.get("lastActivityAt", 0) or 0)
        except Exception:
            pass
        fresh[p] = rec
    best = {}
    for c in fresh.values():
        sid, t = c.get("sid"), c.get("title")
        if sid and t and c.get("act", 0) >= best.get(sid, (-1, ""))[0]:
            best[sid] = (c.get("act", 0), t)
    return ({sid: t for sid, (_, t) in best.items()}, fresh)

def usd(x): return f"≈${x:.4f}" if x < 1 else f"≈${x:.2f}"
def kf(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else (f"{n/1e3:.1f}K" if n >= 1e3 else str(n))

def main():
    today = datetime.date.today().isoformat()
    today0 = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    # mtime is only a cheap pre-filter (no turns today is possible without a write today);
    # what actually decides "today" is each turn's own timestamp.
    files = [f for f in glob.glob(os.path.join(PROJ, "*", "*.jsonl"))
             if os.path.getmtime(f) >= today0]

    scache, tcache = {}, {}
    try:
        with open(CACHE) as f:
            c = json.load(f)
        if isinstance(c, dict) and c.get("v") == 2:
            scache = c.get("sessions") or {}
            tcache = c.get("titles") or {}
    except Exception:
        pass

    titles, tfresh = gui_titles(tcache)

    sessions, sfresh = [], {}
    for f in sorted(files, key=os.path.getmtime, reverse=True):
        mt = os.path.getmtime(f)
        c = scache.get(f)
        if c and c.get("mtime") == mt:
            agg = c
        else:
            agg = session_cost(f); agg["mtime"] = mt
        sfresh[f] = agg                      # prune cache to today's files only
        sessions.append((f, mt, agg))
    try:
        with open(CACHE, "w") as f:
            json.dump({"v": 2, "sessions": sfresh, "titles": tfresh}, f)
    except Exception:
        pass

    # only sessions that actually burned tokens today (a GUI click on an old chat adds none)
    shown = [(f, mt, a, a["days"].get(today, 0.0)) for f, mt, a in sessions
             if a["days"].get(today, 0.0) > 0]
    today_total = sum(t for _, _, _, t in shown)
    life_total = sum(a["main"] + a["sub"] for _, _, a, _ in shown)
    now = datetime.datetime.now().strftime("%H:%M:%S")

    # ---- menu bar (no color -> system adaptive, legible on any wallpaper) ----
    print(f"{usd(today_total)} | font=Menlo")
    print("---")
    n = len(shown)
    print(f"Today (since 00:00) · {usd(today_total)} · {n} session{'s' if n != 1 else ''} | color={GOLD} font=Menlo")
    print(f"Lifetime of those sessions · {usd(life_total)} | color={DIM} font=Menlo size=11")
    print(f"Updated {now} | color={DIM} font=Menlo size=11")
    print("---")
    if not shown:
        print("No billable work yet today | color=#8A8A8A font=Menlo")
    for f, mt, a, tcost in shown:
        sid = os.path.splitext(os.path.basename(f))[0]
        live = (time.time() - mt) < LIVE_WINDOW
        tot = a["main"] + a["sub"]
        # collapse whitespace/newlines and escape SwiftBar's | separator — one row must stay one line
        label = " ".join((titles.get(sid) or a.get("prompt") or sid[:8]).split())[:42].replace("|", "¦")
        dot = "●" if live else "○"
        print(f"{dot} {label}  {usd(tcost)} today · {usd(tot)} total | color={GOLD if live else DIM} font=Menlo")
        print(f"-- Model: {(a.get('top') or '?').replace('claude-','')}{'  (unknown — est. at Opus)' if (a.get('top') and a.get('top') not in PRICES) else ''} | font=Menlo")
        print(f"-- Lifetime  Main {usd(a['main'])}  ·  Subagents {usd(a['sub'])} | font=Menlo")
        print(f"-- Tokens  in {kf(a['tin'])} · out {kf(a['tout'])} | font=Menlo")
        print(f"-- Cache  rd {kf(a['tcr'])} · wr {kf(a['tcw'])} | font=Menlo")
        print(f"-- Session {sid[:8]} · {'live' if live else 'idle'} | color={DIM} font=Menlo")
        print(f"-- Reveal transcript in Finder | shell=/usr/bin/open param1=-R param2={f} terminal=false")
    print("---")
    print("Refresh now | refresh=true")

if __name__ == "__main__":
    main()
