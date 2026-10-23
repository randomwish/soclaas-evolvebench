"""Generate the final EvolveBench report (markdown) from run logs."""
import json, glob, os, sys

OUT = os.path.dirname(os.path.abspath(__file__))

def collect(task):
    """model -> dict(best, curve(best-so-far per attempt), n, fails, tok)"""
    data = {}
    for f in glob.glob(f"{OUT}/runs/{task}_*.jsonl"):
        model = os.path.basename(f)[len(task) + 1:-6].split("__")[0]
        d = data.setdefault(model, {"attempts": [], "tok": 0, "codes": {}})
        for l in open(f):
            r = json.loads(l)
            if "score" in r:
                sc = r["score"] if r["score"] else None  # 0.0 = failed/invalid candidate
                d["attempts"].append(sc)
                if sc and "code" in r:
                    d["codes"][sc] = r["code"]
            elif "error" in r:
                d["attempts"].append(None)
            elif "FINAL_BEST" in r:
                d["tok"] += r.get("tok_out", 0)
    for m, d in data.items():
        curve, best = [], None
        for a in d["attempts"]:
            if a is not None and (best is None or (task == "cache" and a > best) or (task == "binpack" and a < best)):
                best = a
            curve.append(best)
        d["curve"] = curve
        d["best"] = best
        d["n"] = len(d["attempts"])
        d["fails"] = sum(1 for a in d["attempts"] if a is None)
    return data

def spark(vals, width=24, invert=False):
    pts = [v for v in vals if v is not None]
    if not pts: return ""
    lo, hi = min(pts), max(pts)
    bars = "▁▂▃▄▅▆▇█"
    out = []
    step = max(1, len(vals) // width)
    for v in vals[::step]:
        if v is None: out.append("·")
        else:
            frac = 0 if hi == lo else ((v - lo) / (hi - lo)) if not invert else ((hi - v) / (hi - lo))
            out.append(bars[min(7, int(frac * 7.999))])
    return "".join(out)

def main():
    lines = ["# SoCLaaS EvolveBench — generate–evaluate–evolve model bake-off", ""]
    lines.append("_AlphaEvolve/FunSearch-style loop: each model writes candidate programs, they are executed in subprocess sandboxes, scored, and the score + survivor code is fed back for the next generation. 20 generations per model per task (islands for slow reasoners)._")
    lines.append("")

    bl = json.load(open(f"{OUT}/baselines.json"))
    cache = collect("cache")
    lines.append("## Task 1 — Online cache eviction policy")
    lines.append("")
    lines.append("Fitness = mean hit rate over 5 fixed 20k-request traces (Zipf / drifting-Zipf / scan+hotset / cyclic-loop / LRU-killer), capacity 50. **Higher = better.**")
    lines.append("")
    lines.append("| baseline | mean hit rate |")
    lines.append("|---|---|")
    for k in ["belady_mean", "random_mean", "lfu_mean", "lru_mean"]:
        lines.append(f"| {k.split('_')[0].capitalize()} | {bl[k]:.4f} |")
    lines.append("")
    lines.append("| model | best fitness | vs LRU | curve (best-so-far) | attempts | failed | tok out |")
    lines.append("|---|---|---|---|---|---|---|")
    rank = sorted(cache.items(), key=lambda kv: (kv[1]["best"] is None, -(kv[1]["best"] or 0)))
    for m, d in rank:
        b = d["best"]
        vs = f"{(b/bl['lru_mean']-1)*100:+.1f}%" if b else "—"
        bs = f"{b:.4f}" if b is not None else "fail"
        lines.append(f"| {m.replace('soclaas/','')} | **{bs}** | {vs} | `{spark(d['curve'])}` | {d['n']} | {d['fails']} | {d['tok']:,} |")
    lines.append("")

    lines.append("## Task 2 — Bin packing heuristic")
    lines.append("")
    lines.append("Fitness = mean (bins used / L1 lower bound) over 16 instances. **Lower = better.** First-Fit-Decreasing reference = **1.0853**. Perfect = 1.0.")
    lines.append("")
    bp = collect("binpack")
    lines.append("| model | best fitness | vs FFD | curve (best-so-far) | attempts | failed | tok out |")
    lines.append("|---|---|---|---|---|---|---|")
    rank = sorted(bp.items(), key=lambda kv: (kv[1]["best"] is None, kv[1]["best"] or 9))
    for m, d in rank:
        b = d["best"]
        vs = f"{(b/1.0853-1)*100:+.1f}%" if b else "—"
        bs = f"{b:.4f}" if b is not None else "fail"
        lines.append(f"| {m.replace('soclaas/','')} | **{bs}** | {vs} | `{spark(d['curve'], invert=True)}` | {d['n']} | {d['fails']} | {d['tok']:,} |")
    lines.append("")

    lines.append("## Composite")
    lines.append("")
    lines.append("| model | cache (↑) | binpack (↓) | verdict |")
    lines.append("|---|---|---|---|")
    models = sorted(set(cache) & set(bp), key=lambda m: -((cache[m]["best"] or 0) - (bp[m]["best"] or 1)))
    for m in models:
        c, b = cache[m]["best"], bp[m]["best"]
        cs = f"{c:.4f}" if c is not None else "fail"
        bs = f"{b:.4f}" if b is not None else "fail"
        verdict = []
        if c and c > bl["lru_mean"]: verdict.append(f"beats LRU by {(c/bl['lru_mean']-1)*100:.0f}%")
        if b and b < 1.0853: verdict.append("beats FFD")
        lines.append(f"| {m.replace('soclaas/','')} | {cs} | {bs} | {', '.join(verdict) or '—'} |")
    lines.append("")
    open(f"{OUT}/REPORT.md", "w").write("\n".join(lines))
    print("\n".join(lines))

if __name__ == "__main__":
    main()
