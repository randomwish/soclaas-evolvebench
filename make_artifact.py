"""Generate index.html — a self-contained writeup/artifact of the EvolveBench results."""
import json, glob, os, html

OUT = os.path.dirname(os.path.abspath(__file__))

def collect(task):
    data = {}
    for f in glob.glob(f"{OUT}/runs/{task}_*.jsonl"):
        model = os.path.basename(f)[len(task) + 1:-6].split("__")[0]
        d = data.setdefault(model, {"attempts": [], "tok": 0, "codes": {}, "evals": 0})
        for l in open(f):
            r = json.loads(l)
            if "score" in r:
                sc = r["score"] if r["score"] else None
                d["attempts"].append(sc)
                if sc and "code" in r:
                    d["codes"][sc] = r["code"]
                if "eval_s" in r:
                    d["evals"] += r["eval_s"]
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

cache = collect("cache")
bp = collect("binpack")
BL = json.load(open(f"{OUT}/baselines.json"))

DISPLAY = {"soclaas/x-test-2": "DeepSeek V4.1 Flash", "soclaas/x-test-1": "GLM 5.3 Flash",
           "soclaas/qwen3-coder-next": "Qwen3 Coder Next 80B", "soclaas/llama3.1:8b": "Llama 3.1 8B",
           "soclaas/qwen3-vl:32b": "Qwen3 VL 32B", "soclaas/ornith1.5:35b": "Ornith 1.5 35B A3B",
           "soclaas/qwen3.8:27b": "Qwen 3.8 27B", "soclaas/qwen3.6:35b": "Qwen 3.6 35B A3B",
           "soclaas/gemma4:26b": "Gemma 4 26B", "soclaas/coding": "Coding (SoCLaaS)",
           "soclaas/qwen3.5:9b": "Qwen 3.5 9B", "soclaas/x-test-3": "x-test-3 (down)"}
COLORS = {"soclaas/x-test-2": "#ff7ab6", "soclaas/x-test-1": "#7ad7ff", "soclaas/qwen3-coder-next": "#8affc1",
          "soclaas/llama3.1:8b": "#ffd479", "soclaas/qwen3-vl:32b": "#b69aff", "soclaas/ornith1.5:35b": "#ff9d7a",
          "soclaas/qwen3.8:27b": "#7a9dff", "soclaas/qwen3.6:35b": "#9aff7a", "soclaas/gemma4:26b": "#7affd4",
          "soclaas/coding": "#ff7a7a", "soclaas/qwen3.5:9b": "#9a9a9a", "soclaas/x-test-3": "#555"}

def esc(s): return html.escape(str(s))

# ---------------------------------------------------------------- line chart (cache curves)
W, H, PAD = 920, 420, 46
Y0, Y1 = 0.30, 0.75  # fitness range shown
def xy(i, v, nmax):
    x = PAD + (W - 2 * PAD) * (i / max(nmax - 1, 1))
    y = H - PAD - (H - 2 * PAD) * ((v - Y0) / (Y1 - Y0))
    return round(x, 1), round(y, 1)

nmax = max(len(d["curve"]) for d in cache.values())
parts = [f'<svg viewBox="0 0 {W} {H}" class="chart">']
for gy in [0.4, 0.5, 0.6, 0.7]:
    _, py = xy(0, gy, nmax)
    parts.append(f'<line x1="{PAD}" y1="{py}" x2="{W-PAD}" y2="{py}" class="grid"/>')
    parts.append(f'<text x="{PAD-8}" y="{py+4}" class="ax" text-anchor="end">{gy:.2f}</text>')
for lbl, v, c in [("Belady (optimal) 0.712", 0.7115, "#888"), ("Random 0.527", 0.5265, "#888"), ("LRU 0.434", 0.4339, "#888")]:
    _, py = xy(0, v, nmax)
    parts.append(f'<line x1="{PAD}" y1="{py}" x2="{W-PAD}" y2="{py}" stroke="{c}" stroke-dasharray="6 5" stroke-width="1.4"/>')
    parts.append(f'<text x="{W-PAD-4}" y="{py-5}" class="ax" text-anchor="end" fill="{c}">{lbl}</text>')
for m, d in sorted(cache.items(), key=lambda kv: -(kv[1]["best"] or 0)):
    pts = [xy(i, v, nmax) for i, v in enumerate(d["curve"]) if v is not None]
    if not pts: continue
    col = COLORS.get(m, "#aaa")
    parts.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="2.4" stroke-linejoin="round"/>')
    x, y = pts[-1]
    parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{col}"/>')
    parts.append(f'<text x="{x+7}" y="{y+4}" class="ax" fill="{col}">{esc(DISPLAY.get(m, m).replace("soclaas/",""))}</text>')
parts.append(f'<line x1="{PAD}" y1="{H-PAD}" x2="{W-PAD}" y2="{H-PAD}" class="axis"/>')
parts.append(f'<text x="{W/2}" y="{H-8}" class="ax" text-anchor="middle">candidates generated & evaluated (best-so-far)</text>')
parts.append("</svg>")
CURVE_SVG = "\n".join(parts)

# ---------------------------------------------------------------- bar chart (cache best)
def bars(rows, w=920, bh=34, gap=13, lo=0.0, hi=0.75, fmt=lambda v: f"{v:.4f}"):
    Wd = w; Ht = PAD + len(rows) * (bh + gap) + 10
    out = [f'<svg viewBox="0 0 {Wd} {Ht}" class="chart">']
    for i, (m, v, extra) in enumerate(rows):
        y = PAD + i * (bh + gap)
        frac = 0 if v is None else (v - lo) / (hi - lo)
        col = COLORS.get(m, "#888")
        vw = (Wd - 2 * PAD - 150) * min(frac, 1.0)
        out.append(f'<text x="{PAD}" y="{y+bh/2+5}" class="lbl">{esc(DISPLAY.get(m, m))}</text>')
        out.append(f'<rect x="{PAD+170}" y="{y}" width="{max(vw,2)}" height="{bh}" rx="6" fill="{col}" opacity="0.92"/>')
        t = fmt(v) if v is not None else "fail"
        out.append(f'<text x="{PAD+170+max(vw,2)+10}" y="{y+bh/2+5}" class="lbl" fill="{"#eee" if v is not None else "#f66"}">{t}{extra}</text>')
    out.append("</svg>")
    return "\n".join(out)

cache_rows = [(m, d["best"], f"  ·  {d['tok']:,} tok · {d['n']} candidates") for m, d in
              sorted(cache.items(), key=lambda kv: -(kv[1]["best"] or 0))]

# token efficiency scatter-ish bars: fitness per 100k tokens
eff_rows = [(m, (d["best"] or 0) / max(d["tok"], 1) * 100000, "") for m, d in cache.items() if d["best"]]
eff_rows.sort(key=lambda r: -r[1])

code_cache, code_glm = "", ""
def snippet(path, n=34):
    src = open(path).read().splitlines()
    body = [l for l in src if not l.startswith("# fitness")][:n]
    return esc("\n".join(body))
try: code_cache = snippet(f"{OUT}/winners/cache_soclaas_x-test-2.py")
except: pass
try: code_glm = snippet(f"{OUT}/winners/cache_soclaas_x-test-1.py")
except: pass

def tbl_cache():
    rows = sorted(cache.items(), key=lambda kv: -(kv[1]["best"] or 0))
    out = ["<tr><th>model</th><th>best</th><th>vs LRU</th><th>candidates</th><th>failed</th><th>output tokens</th></tr>"]
    for m, d in rows:
        b = d["best"]
        vs = f"{(b/BL['lru_mean']-1)*100:+.0f}%" if b else "—"
        cls = ' class="hl"' if m == "soclaas/x-test-2" else ""
        out.append(f"<tr{cls}><td>{esc(DISPLAY.get(m,m))}</td><td><b>{f'{b:.4f}' if b is not None else '—'}</b></td><td>{vs}</td><td>{d['n']}</td><td>{d['fails']}</td><td>{d['tok']:,}</td></tr>")
    return "\n".join(out)

def tbl_bp():
    rows = sorted(bp.items(), key=lambda kv: (kv[1]["best"] is None, kv[1]["best"] or 9))
    out = ["<tr><th>model</th><th>best</th><th>vs FFD (1.0853)</th><th>candidates</th><th>failed</th><th>output tokens</th></tr>"]
    for m, d in rows:
        b = d["best"]
        vs = f"{(b/1.0853-1)*100:+.1f}%" if b else "—"
        out.append(f"<tr><td>{esc(DISPLAY.get(m,m))}</td><td><b>{f'{b:.4f}' if b is not None else '—'}</b></td><td>{vs}</td><td>{d['n']}</td><td>{d['fails']}</td><td>{d['tok']:,}</td></tr>")
    return "\n".join(out)

total_cands = sum(d["n"] for d in cache.values()) + sum(d["n"] for d in bp.values())
total_tok = sum(d["tok"] for d in cache.values()) + sum(d["tok"] for d in bp.values())
valid_cache = sum(1 for d in cache.values() for a in d["attempts"] if a)
reqs = valid_cache * 5 * 20000

page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SoCLaaS EvolveBench — 12 models, generate–evaluate–evolve</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #0d1117; color: #dbe2ee; font: 16px/1.65 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  .wrap {{ max-width: 1020px; margin: 0 auto; padding: 48px 28px 80px; }}
  h1 {{ font-size: 40px; line-height: 1.15; margin: 0 0 10px; letter-spacing: -0.5px; }}
  h1 .grad {{ background: linear-gradient(90deg,#ff7ab6,#7ad7ff,#8affc1); -webkit-background-clip: text; background-clip: text; color: transparent; }}
  h2 {{ font-size: 26px; margin: 54px 0 6px; letter-spacing: -0.3px; }}
  h3 {{ font-size: 18px; margin: 26px 0 8px; color: #9fb3d1; }}
  p.lead {{ font-size: 19px; color: #aab8cf; margin: 8px 0 0; }}
  p {{ margin: 12px 0; }}
  a {{ color: #7ad7ff; }}
  .card {{ background: #131b28; border: 1px solid #223049; border-radius: 14px; padding: 22px 24px; margin: 18px 0; }}
  .stats {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 22px 0; }}
  .stat {{ flex: 1 1 150px; background: #131b28; border: 1px solid #223049; border-radius: 14px; padding: 16px 18px; }}
  .stat b {{ display: block; font-size: 26px; color: #fff; }}
  .stat span {{ color: #8ba1c2; font-size: 13px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14.5px; margin: 14px 0; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #223049; }}
  th {{ color: #8ba1c2; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.4px; }}
  tr.hl td {{ background: #1a2436; }}
  .chart {{ width: 100%; height: auto; background: #0f1622; border: 1px solid #223049; border-radius: 14px; margin: 14px 0; }}
  .ax {{ font-size: 12px; fill: #8ba1c2; }}
  .lbl {{ font-size: 13.5px; fill: #dbe2ee; }}
  .grid {{ stroke: #1c2739; }}
  .axis {{ stroke: #33445f; }}
  pre {{ background: #0a0f18; border: 1px solid #223049; border-radius: 12px; padding: 16px 18px; overflow-x: auto; font: 12.5px/1.55 ui-monospace, "SF Mono", Menlo, Consolas, monospace; color: #c9d6ea; }}
  .pill {{ display: inline-block; background: #1a2436; border: 1px solid #2c3d5c; color: #9fb3d1; border-radius: 999px; padding: 3px 12px; font-size: 13px; margin: 2px 4px 2px 0; }}
  .win {{ color: #8affc1; }} .warn {{ color: #ffd479; }} .bad {{ color: #ff7a7a; }}
  footer {{ margin-top: 60px; color: #66799a; font-size: 14px; border-top: 1px solid #223049; padding-top: 20px; }}
</style></head><body><div class="wrap">

<h1>SoCLaaS <span class="grad">EvolveBench</span></h1>
<p class="lead">A FunSearch / AlphaEvolve-style experiment: <b>12 LLMs on a university GPU cluster</b> were made to write, execute, and iteratively improve real algorithms — scoring <b>correctness and performance by actually running the code</b>.</p>

<div class="stats">
  <div class="stat"><b>{total_cands}</b><span>candidate programs generated & executed</span></div>
  <div class="stat"><b>{total_tok:,}</b><span>output tokens of inference</span></div>
  <div class="stat"><b>2</b><span>tasks: cache eviction · bin packing</span></div>
  <div class="stat"><b>{reqs/1e6:.1f}M</b><span>cache requests simulated in sandboxes</span></div>
</div>

<h2>The loop</h2>
<div class="card">
<p>Each model starts from a blank prompt. Every generation it receives the task spec, the <b>surviving parent programs with their measured fitness</b>, per-trace score breakdowns, and the <b>exact errors</b> of failed children. It writes a new candidate; the candidate runs in a subprocess sandbox against fixed workloads; the score feeds the next generation. Slow reasoning models evolved parallel <b>islands</b>. No human wrote any algorithm — only the fitness function.</p>
<pre>prompt ──▶ model generates program ──▶ sandbox executes it ──▶ measured fitness
   ▲                                                            │
   └──────────── parent code + score + error feedback ◀─────────┘</pre>
<p><span class="pill">temperature 0.9</span><span class="pill">top-3 archive + random parent</span><span class="pill">duplicate rejection</span><span class="pill">timeout → fail → fed back as text</span></p>
</div>

<h2>Task 1 — Evolve an online cache eviction policy</h2>
<p>Candidates implement <code>evict(cache, meta) → index</code>, called on every miss of a 50-entry cache over five fixed 20,000-request traces: Zipf, drifting-Zipf, scan+hot-set, cyclic-loop-with-bursts, and a scan-heavy LRU-killer. Fitness = <b>mean hit rate</b>. The meta dictionary deliberately exposes raw materials (frequencies, last-access times, a 64-key recent window) but no ground truth about the future.</p>
<table>{tbl_cache()}</table>

<div class="card">
<h3>Evolution curves — every model's best-so-far, generation by generation</h3>
{CURVE_SVG}
<p style="color:#8ba1c2; font-size:14px;">Dashed lines are classical baselines computed on the same traces. Every curve that leaves the floor is a policy the model invented, tested, and kept.</p>
</div>

<div class="card">
<h3>Final scores with inference cost</h3>
{bars(cache_rows)}
<p style="color:#8ba1c2; font-size:14px;">Bar length = best mean hit rate reached. The annotation on each bar shows total output tokens burned — the reasoners spent 30–50× more than the 8B model for a fraction more fitness.</p>
</div>

<h3>What the winner actually invented</h3>
<p><b class="win">DeepSeek V4.1 Flash — 0.6443 (+48% over LRU)</b> converged on a <i>trace-shape classifier</i>: it computes a uniqueness ratio and burst statistics over the recent window, detects "scan-like" vs "cyclic-like" vs "hot-set" regimes, and switches between frequency-weighted LRU, MRU-among-cold (anti-loop-thrash), and burst-protected eviction. An Adaptive Replacement Policy, discovered by iteration.</p>
<pre>{code_cache}</pre>
<p><b class="win">GLM 5.3 Flash — 0.6206</b> took a different route: a <i>poor-man's Belady</i>. Per key it remembers the last 3 inter-arrival gaps, predicts the next access time, evicts the key predicted to return furthest away; keys seen once are treated as never-returning (scan resistance), and keys overdue vs their own prediction fall back to LRU.</p>
<pre>{code_glm}</pre>

<h2>Task 2 — Evolve a bin-packing heuristic</h2>
<p>Candidates implement <code>pack(items, capacity)</code>; score = mean bins used ÷ L1 lower bound over 16 instances (uniform, small-size sets, mid-size, mixed). Lower is better; <b>First-Fit-Decreasing scores 1.0853</b> on these instances.</p>
<table>{tbl_bp()}</table>
<div class="card">
<p><b>The plateau.</b> Every model that produced valid code — from Llama 8B to DeepSeek V4.1 — converged to <i>exactly</i> the FFD reference, with identical per-instance score vectors. Single-shot ordering heuristics saturate at FFD; breaking below it requires embedding local search inside the candidate within the time budget, which no model found in 20 generations. Meanwhile Llama 3.1 8B — the only model that never hit the attractor — finished <i>worse</i> (1.1189) but was still learning when its budget ended.</p>
<p><b>Lesson:</b> the shape of the fitness landscape decides how much room evolution has. Online caching, with its adversarial, non-stationary structure, rewards invention; classic deterministic heuristics have a hard attractor at the textbook algorithm.</p>
</div>

<h2>Who is the best at iteration?</h2>
<div class="card">
<table>
<tr><th></th><th>model</th><th>cache (↑)</th><th>cost profile</th><th>verdict</th></tr>
<tr class="hl"><td>🥇</td><td>DeepSeek V4.1 Flash</td><td>0.6443</td><td>~28k tok/candidate</td><td>best programs, huge inference appetite</td></tr>
<tr><td>🥈</td><td>GLM 5.3 Flash</td><td>0.6206</td><td>~14k tok/candidate</td><td>creative strategies, slow, some crashes</td></tr>
<tr><td>🥉</td><td>Qwen3 Coder Next 80B</td><td>0.6162</td><td>~1.5k tok/candidate</td><td>near-frontier quality at coder-model prices</td></tr>
<tr><td>💰</td><td>Llama 3.1 8B</td><td>0.5857</td><td>~0.5k tok/candidate</td><td><b>best fitness per token by ~30×</b>; steady, clean iteration</td></tr>
<tr><td>💀</td><td>Qwen 3.5 9B</td><td>0 / 50 valid</td><td>—</td><td>burns its whole output budget "thinking" in prose before writing any code</td></tr>
</table>
<p>Two failure modes mattered as much as raw ability: <b>budget discipline</b> (Qwen 3.5 never emitted a single runnable program in 50 tries, even with format remediation) and <b>reliability</b> (x-test-3 was down all day; Gemma 4's ollama backend collapsed under concurrent load). In an evolution loop, a model that can't reliably emit a complete, runnable artifact scores zero regardless of its intelligence.</p>
</div>

<footer>
SoCLaaS EvolveBench · harness, raw logs &amp; evolved programs: <a href="https://github.com/randomwish/soclaas-evolvebench">github.com/randomwish/soclaas-evolvebench</a><br>
Generate–evaluate–evolve in the style of FunSearch (DeepMind, 2023) and AlphaEvolve (2025). Models served by the SoCLaaS cluster (NUS SoC). All fitness numbers are measured, never estimated.
</footer>
</div></body></html>"""

open(f"{OUT}/index.html", "w").write(page)
print("wrote index.html", len(page), "bytes")
