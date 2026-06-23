#!/usr/bin/env python3
"""
Claude Code statusLine cost/quota meter.

Reads the session JSON Claude Code pipes on stdin and prints ONE status line.
Pure stdin -> no transcript parsing -> fast (<60ms), safe to run every render.

Shows, left to right:
  <Model>  ≈$<cost>  ctx <ctx%>  5h <quota%>  7d <quota%>
    ≈$cost = API-EQUIVALENT cost of this session (Claude Code's own total_cost_usd;
             counterfactual — on Max the real bill is flat).
    ctx%   = how full the context window is.
    5h/7d  = how much of your Max quota this rolling window has burned (the real cap).
  Quota/context numbers go green<50% / yellow<80% / red>=80%.

For the RETROSPECTIVE per-project/client cost breakdown, see cost_attribution.py.
Always exits 0 (a non-zero exit blanks the status line).
"""
import sys, json

R = "\033[0m"; D = "\033[2m"; B = "\033[1m"
CY = "\033[36m"; GN = "\033[32m"; YL = "\033[33m"; RD = "\033[31m"

def qcol(p):
    return GN if p < 50 else (YL if p < 80 else RD)

def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return  # bad/empty stdin -> blank line, no crash

    seg = []

    m = (d.get("model") or {}).get("display_name")
    if m:
        seg.append(f"{CY}{B}{m}{R}")

    c = (d.get("cost") or {}).get("total_cost_usd")
    c = 0.0 if c is None else c
    cs = f"≈${c:.4f}" if c < 1 else f"≈${c:.2f}"
    seg.append(f"{B}{cs}{R}")

    up = (d.get("context_window") or {}).get("used_percentage")
    if up is not None:
        seg.append(f"{D}ctx{R} {qcol(up)}{int(up)}%{R}")

    rl = d.get("rate_limits") or {}
    fh = (rl.get("five_hour") or {}).get("used_percentage")
    sd = (rl.get("seven_day") or {}).get("used_percentage")
    if fh is not None:
        seg.append(f"{D}5h{R} {qcol(fh)}{fh:.0f}%{R}")
    if sd is not None:
        seg.append(f"{D}7d{R} {qcol(sd)}{sd:.0f}%{R}")

    sys.stdout.write(f" {D}·{R} ".join(seg))

if __name__ == "__main__":
    main()
