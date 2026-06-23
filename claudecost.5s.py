#!/usr/bin/env python3
# <xbar.title>Claude Cost Meter</xbar.title>
# <xbar.version>v2</xbar.version>
# <xbar.author>Nihar Kohirkar</xbar.author>
# <xbar.author.github>evolvingmath</xbar.author.github>
# <xbar.desc>Live API-equivalent cost of today's Claude sessions (CLI + Mac app).</xbar.desc>
# <swiftbar.refreshOnOpen>true</swiftbar.refreshOnOpen>
"""
SwiftBar plugin — total API-equivalent cost of today's Claude sessions.

Menu bar : ≈$<sum of every session active today>  (adaptive color -> legible on any wallpaper)
Dropdown : one row per today's session (● live / ○ idle); hover a row for its detail submenu
           (model, main vs subagent split, tokens, reveal-transcript-in-Finder).

Reads ~/.claude/projects (the Claude Code CLI *and* the Mac app write there). Sums each
turn's usage (deduped by requestId) for the main loop + its subagents, priced at published
API rates with correct cache tiers. Per-file cache keyed by mtime -> only re-parses a session
when it actually grows. Standalone (no third-party deps).

Author: Nihar Kohirkar. MIT.
"""
import os, json, glob, time, datetime

PROJ = os.path.expanduser("~/.claude/projects")
CACHE = "/tmp/claude_costmeter_cache_v2.json"
GOLD = "#9D7E2F"; DIM = "#8A8A8A"
LIVE_WINDOW = 120  # seconds since last write to count a session as "live"

# per-token USD (input, output); cache_read=0.1x in, write5m=1.25x in, write1h=2.0x in
PRICES = {
    "claude-fable-5": (10e-6, 50e-6),
    "claude-opus-4-8": (5e-6, 25e-6), "claude-opus-4-7": (5e-6, 25e-6),
    "claude-opus-4-6": (5e-6, 25e-6), "claude-opus-4-5": (5e-6, 25e-6),
    "claude-sonnet-4-6": (3e-6, 15e-6), "claude-sonnet-4-5": (3e-6, 15e-6),
    "claude-haiku-4-5": (1e-6, 5e-6),
}
def rate(m): return PRICES.get((m or "").strip(), PRICES["claude-opus-4-8"])

def parse(path):
    """Dedupe by requestId; return (cost, tin, tout, tcr, tcw, top_model)."""
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
                    turns[rid] = (msg.get("model"), inp, out, cr, c5, c1, tot)
    except Exception:
        return (0.0, 0, 0, 0, 0, None)
    cost = tin = tout = tcr = tcw = 0
    bym = {}
    for m, inp, out, cr, c5, c1, _ in turns.values():
        bi, bo = rate(m)
        cost += inp*bi + out*bo + cr*0.1*bi + c5*1.25*bi + c1*2.0*bi
        tin += inp; tout += out; tcr += cr; tcw += c5 + c1
        bym[m] = bym.get(m, 0) + 1
    return (cost, tin, tout, tcr, tcw, (max(bym, key=bym.get) if bym else None))

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
    """Main loop + its subagents for one session file."""
    main_cost, tin, tout, tcr, tcw, top = parse(path)
    sid = os.path.splitext(os.path.basename(path))[0]
    sub = 0.0
    subdir = os.path.join(os.path.dirname(path), sid, "subagents")
    for af in glob.glob(os.path.join(subdir, "**", "agent-*.jsonl"), recursive=True):
        sub += parse(af)[0]
    return {"main": main_cost, "sub": sub, "tin": tin, "tout": tout, "tcr": tcr,
            "tcw": tcw, "top": top, "prompt": first_prompt(path)}

def usd(x): return f"≈${x:.4f}" if x < 1 else f"≈${x:.2f}"
def kf(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else (f"{n/1e3:.1f}K" if n >= 1e3 else str(n))

def main():
    today0 = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    files = [f for f in glob.glob(os.path.join(PROJ, "*", "*.jsonl"))
             if os.path.getmtime(f) >= today0]

    cache = {}
    try:
        with open(CACHE) as f:
            c = json.load(f)
        if isinstance(c, dict):
            cache = c
    except Exception:
        pass

    sessions, fresh = [], {}
    for f in sorted(files, key=os.path.getmtime, reverse=True):
        mt = os.path.getmtime(f)
        c = cache.get(f)
        if c and c.get("mtime") == mt:
            agg = c
        else:
            agg = session_cost(f); agg["mtime"] = mt
        fresh[f] = agg                       # prune cache to today's files only
        sessions.append((f, mt, agg))
    try:
        with open(CACHE, "w") as f:
            json.dump(fresh, f)
    except Exception:
        pass

    total = sum(a["main"] + a["sub"] for _, _, a in sessions)
    shown = [s for s in sessions if (s[2]["main"] + s[2]["sub"]) > 0]  # hide $0 / stray sessions
    now = datetime.datetime.now().strftime("%H:%M:%S")

    # ---- menu bar (no color -> system adaptive, legible on any wallpaper) ----
    print(f"{usd(total)} | font=Menlo")
    print("---")
    n = len(shown)
    print(f"{n} session{'s' if n != 1 else ''} today · {usd(total)} | color={GOLD} font=Menlo")
    print(f"Updated {now} | color={DIM} font=Menlo size=11")
    print("---")
    if not shown:
        print("No billable sessions yet today | color=#8A8A8A font=Menlo")
    for f, mt, a in shown:
        sid = os.path.splitext(os.path.basename(f))[0]
        live = (time.time() - mt) < LIVE_WINDOW
        tot = a["main"] + a["sub"]
        label = a.get("prompt") or sid[:8]
        dot = "●" if live else "○"
        print(f"{dot} {label}  {usd(tot)} | color={GOLD if live else DIM} font=Menlo")
        print(f"-- Model: {(a.get('top') or '?').replace('claude-','')} | font=Menlo")
        print(f"-- Main {usd(a['main'])}  ·  Subagents {usd(a['sub'])} | font=Menlo")
        print(f"-- Tokens  in {kf(a['tin'])} · out {kf(a['tout'])} | font=Menlo")
        print(f"-- Cache  rd {kf(a['tcr'])} · wr {kf(a['tcw'])} | font=Menlo")
        print(f"-- Session {sid[:8]} · {'live' if live else 'idle'} | color={DIM} font=Menlo")
        print(f"-- Reveal transcript in Finder | shell=/usr/bin/open param1=-R param2={f} terminal=false")
    print("---")
    print("Refresh now | refresh=true")

if __name__ == "__main__":
    main()
