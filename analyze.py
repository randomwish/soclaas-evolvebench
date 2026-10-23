"""Summarize EvolveBench runs: best score per model, evolution curves, errors."""
import json, glob, os, sys
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))

def load(task):
    rows = defaultdict(list)
    for f in glob.glob(f"{OUT}/runs/{task}_*.jsonl"):
        name = os.path.basename(f)[len(task) + 1:-6]
        model = name.split("__")[0].replace("_", "/", 1)
        for l in open(f):
            d = json.loads(l)
            if "FINAL_BEST" in d:
                rows[model].append({"gen": d["gen"], "final": d["FINAL_BEST"], "tok": d.get("tok_out", 0)})
            elif "error" in d:
                rows[model].append({"gen": d["gen"], "error": d["error"]})
            else:
                rows[model].append({"gen": d["gen"], "score": d["score"], "best": d.get("new_best", False)})
    return rows

def main(task):
    rows = load(task)
    higher = task == "cache"
    print(f"\n=== TASK: {task} ({'higher=better' if higher else 'lower=better'}) ===")
    summary = []
    for m, rs in sorted(rows.items()):
        scores = [r["score"] for r in rs if "score" in r]
        finals = [r for r in rs if "final" in r]
        best = max(scores) if (higher and scores) else (min(scores) if scores else None)
        final = finals[-1]["final"] if finals else None
        errs = sum(1 for r in rs if "error" in r)
        zeros = sum(1 for s in scores if s == 0)
        summary.append((final if final is not None else 9e9, m, best, len(scores), zeros, errs, finals[-1]["tok"] if finals else 0))
    inv = not higher
    summary.sort(key=lambda x: x[0] if x[0] != 9e9 else -1, reverse=inv)
    print(f"{'model':32s} {'FINAL best':>10s} {'best eval':>10s} {'cands':>6s} {'fails':>6s} {'err':>4s} {'tok_out':>8s}")
    for final, m, best, n, zeros, errs, tok in summary:
        print(f"{m:32s} {final:10.4f} {best if best is not None else float('nan'):10.4f} {n:6d} {zeros:6d} {errs:4d} {tok:8d}")

if __name__ == "__main__":
    for t in (sys.argv[1:] or ["cache", "binpack"]):
        main(t)
