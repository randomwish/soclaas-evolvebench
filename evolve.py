"""SoCLaaS EvolveBench — an AlphaEvolve/FunSearch-style generate-evaluate-evolve loop.

Tasks: (1) cache eviction policies, (2) bin-packing heuristics.
Models: every model on the soclaas provider.
Each model evolves a population of candidate programs; candidates are executed
in subprocess sandboxes and scored. Feedback (score, errors, baselines,
survivor code) is fed back to the model to generate the next candidate.
"""

import json, hashlib, math, os, random, re, subprocess, sys, time, urllib.request, urllib.error
from collections import Counter, OrderedDict

API = "https://soclaas-api.comp.nus.edu.sg/v1/chat/completions"
KEY = [l.split("=", 1)[1].strip() for l in open(os.path.expanduser("~/.config/opencode/opencode.env")) if l.startswith("SOCLAAS_API_KEY")][0]
OUT = os.path.dirname(os.path.abspath(__file__))
EVO_TEMP = 0.9

# ---------------------------------------------------------------- LLM client
# per-model max output tokens (from opencode.jsonc limits; reasoning models need headroom)
MAXTOK = {"soclaas/llama3.1:8b": 3500, "soclaas/qwen3.5:9b": 3500, "soclaas/gemma4:26b": 7000,
          "soclaas/qwen3-vl:32b": 4500, "soclaas/coding": 8000, "soclaas/x-test-1": 30000,
          "soclaas/x-test-2": 30000}
def llm(model, prompt, max_tokens=4096, temperature=0.9, retries=4):
    max_tokens = MAXTOK.get(model, 14000)
    retries = int(os.environ.get("EVOLVE_RETRIES", retries))
    body = json.dumps({"model": model.split("/")[-1], "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": temperature}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API, data=body, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            msg = d["choices"][0]["message"]
            txt = msg.get("content") or ""
            if not txt.strip():  # reasoning models that hit token limit mid-thought
                txt = msg.get("reasoning") or ""
            usage = d.get("usage", {})
            return txt, usage.get("completion_tokens", 0), usage.get("prompt_tokens", 0)
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"LLM call failed after {retries} tries: {last}")

def extract_code(txt):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", txt, re.S)
    if blocks:
        return max(blocks, key=len).strip()
    m = re.search(r"^(def |import |from |class )", txt, re.M)
    if m:  # bare code, no fence
        return txt[m.start():].strip()
    return None

# ---------------------------------------------------------------- sandboxing
def run_sandbox(code, func_name, arg, timeout=20):
    """Execute candidate code in a subprocess: result = func(arg). Returns (ok, result_or_error, seconds)."""
    runner = (
        "import json,sys\n"
        "raw=sys.stdin.read()\n"
        "src, payload_raw = raw.split('\\x00', 1)\n"
        "NS={}\n"
        "exec(src,NS)\n"
        "fn=NS[%r]\n"
        "res=fn(json.loads(payload_raw))\n"
        "sys.stdout.write('@@RESULT@@'+json.dumps(res))\n" % func_name
    )
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-c", runner], input=code + "\n\x00" + json.dumps(arg),
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s", timeout
    dt = time.time() - t0
    if p.returncode != 0:
        err = (p.stderr or "unknown error").strip().splitlines()
        return False, err[-1][:300] if err else "unknown error", dt
    out = p.stdout
    i = out.find("@@RESULT@@")
    if i < 0:
        return False, "no result emitted", dt
    try:
        return True, json.loads(out[i + 10:]), dt
    except Exception as e:
        return False, f"bad result json: {e}", dt

# ================================================================ TASK: CACHE
CAP = 50
N_REQ = 20000

def _zipf_stream(rng, n_keys, n, alpha=1.0, offset=0):
    ranks = [(1.0 / (i + 1) ** alpha) for i in range(n_keys)]
    c = sum(ranks)
    return [offset + rng.choices(range(n_keys), weights=ranks)[0] for _ in range(n)]

def gen_traces(seed=7):
    rng = random.Random(seed)
    traces = {}
    traces["zipf"] = _zipf_stream(rng, 1000, N_REQ)
    # zipf with churn: hot set drifts every 4000 requests
    churn, off = [], 0
    for ph in range(5):
        churn += [k % 1000 for k in _zipf_stream(rng, 200, 4000, 1.0, off)]
        off = (off + 250) % 800
    traces["churn"] = churn
    # scan + hot set
    scan = []
    for _ in range(N_REQ):
        if rng.random() < 0.6:
            scan.append(rng.choices(range(30), weights=[1 / (i + 1) for i in range(30)])[0])
        else:
            scan.append(rng.randrange(1000))
    traces["scan_hot"] = scan
    # cyclic loop with bursts (LRU struggles, frequency-aware does fine)
    loop, pos = [], 0
    while len(loop) < N_REQ:
        burst = rng.randint(1, 3)
        loop += [pos] * burst
        pos = (pos + 1) % 300
    traces["loop"] = loop
    # LRU killer: hot key + periodic scan of 60 keys
    lru_k = []
    for _ in range(N_REQ // 61):
        lru_k += [500] * rng.randint(1, 4) + list(range(60))
    traces["scan60"] = lru_k[:N_REQ]
    return traces

def simulate(trace, evict_src, capacity=CAP, timeout=25):
    """Run trace against candidate evict(). Returns (hit_rate, err, seconds)."""
    driver = f"""
{evict_src}

import json, sys
trace = json.load(sys.stdin)
CAP = {capacity}
cache, freq, last = [], {{}}, {{}}
recent = []
hits = misses = 0
t = 0
for key in trace:
    t += 1
    if key in cache:
        hits += 1
    else:
        misses += 1
        if len(cache) >= CAP:
            meta = {{"time": t, "cache_freq": {{k: freq.get(k, 0) for k in cache}},
                    "cache_last": {{k: last.get(k, 0) for k in cache}},
                    "recent": recent[-64:], "capacity": CAP}}
            idx = evict(cache, meta)
            if not isinstance(idx, int) or isinstance(idx, bool) or not (0 <= idx < len(cache)):
                sys.stderr.write(f"invalid victim index: {{idx!r}}\\n"); sys.exit(3)
            v = cache.pop(idx); freq.pop(v, None); last.pop(v, None)
        cache.append(key)
    freq[key] = freq.get(key, 0) + 1
    last[key] = t
    recent.append(key)
sys.stdout.write(json.dumps(hits / max(hits + misses, 1)))
"""
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-c", driver], input=json.dumps(trace),
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 0.0, f"TIMEOUT >{timeout}s", timeout
    dt = time.time() - t0
    if p.returncode != 0:
        err = (p.stderr or "").strip().splitlines()
        return 0.0, (err[-1][:200] if err else "crash"), dt
    return float(p.stdout.strip()), None, dt

def eval_cache(code, traces):
    per, err_all, total_t = {}, [], 0.0
    for name, tr in traces.items():
        hr, err, dt = simulate(tr, code)
        per[name] = round(hr, 4)
        total_t += dt
        if err:
            err_all.append(f"{name}: {err}")
    fit = 0.0 if err_all else sum(per.values()) / len(per)
    return fit, per, err_all, total_t

# ============================================================ TASK: BIN PACK
N_INST = 16

def gen_bin_instances(seed=11):
    rng = random.Random(seed)
    insts = []
    for i in range(N_INST):
        cap = 100
        kind = i % 4
        if kind == 0: items = [rng.randint(1, 100) for _ in range(120)]
        elif kind == 1: items = [rng.choice([3, 7, 11, 13]) for _ in range(150)]
        elif kind == 2: items = [rng.randint(40, 70) for _ in range(80)]
        else:
            items = [rng.randint(20, 50) for _ in range(60)] + [rng.randint(51, 100) for _ in range(40)]
        insts.append({"cap": cap, "items": items})
    return insts

def valid_packing(res, items, cap):
    if not isinstance(res, list): return "not a list"
    seen = []
    for b in res:
        if not isinstance(b, list): return "bin not a list"
        s = 0
        for i in b:
            if not isinstance(i, int) or isinstance(i, bool) or not (0 <= i < len(items)): return f"bad item index {i!r}"
            s += items[i]
        if s > cap: return f"overfull bin ({s} > {cap})"
        seen += b
    if sorted(seen) != list(range(len(items))): return "not every item packed exactly once"
    return None

def ffd_baseline(items, cap):
    order = sorted(range(len(items)), key=lambda i: -items[i])
    bins = []
    for i in order:
        for b in bins:
            if sum(items[j] for j in b) + items[i] <= cap:
                b.append(i); break
        else:
            bins.append([i])
    return len(bins)

def eval_binpack(code, instances, timeout=25):
    scores, errs = [], []
    for inst in instances:
        ok, res, dt = run_sandbox(code, "pack", {"items": inst["items"], "capacity": inst["cap"]}, timeout)
        if not ok:
            errs.append(str(res)[:150]); break
        err = valid_packing(res, inst["items"], inst["cap"])
        if err:
            errs.append(f"invalid packing: {err}"); break
        lb = math.ceil(sum(inst["items"]) / inst["cap"])
        n = len(res)
        scores.append(n / lb)
    if errs:
        return 0.0, None, errs, 0.0
    fit = sum(scores) / len(scores)
    return fit, [round(s, 4) for s in scores], [], 0.0

# ================================================================ EVOLUTION
CACHE_SPEC = """You are participating in an evolutionary program search (FunSearch/AlphaEvolve style) for an ONLINE cache eviction policy.

TASK: implement
    def evict(cache, meta) -> int
Called ONLY on a cache miss when the cache is full. Return the INDEX (0-based) in `cache` of the item to evict; the requested key is then inserted.

Interface:
- cache: list of keys currently in the cache (insertion order, arbitrary key types -> use as dict keys only)
- meta: dict with:
    "time": current request index (int)
    "cache_freq": {key: number of times this key was requested in the whole trace so far}
    "cache_last": {key: time of its most recent request}
    "recent": list of the last 64 requested keys (most recent LAST)
    "capacity": cache capacity (50)

Rules: pure Python (no imports beyond `random`/`math`/`collections`), must run in a few milliseconds per call. The policy is ONLINE: it cannot see the future.

EVALUATION: mean hit rate over 5 fixed 20,000-request traces (Zipf, drifting Zipf, scan+hot-set, cyclic-loop-with-bursts, and a scan-heavy LRU-killer), capacity 50.

Reference points (mean hit rate, higher = better):
{baselines}
(Belady = offline optimum with future knowledge; you cannot reach it, but beating LRU is the goal. Current best known evolutionary score: {best}).

{context}

Respond with a brief explanation of your idea, then ONE complete Python code block defining `evict` (helpers and module constants allowed). Make it genuinely DIFFERENT from the parents above where they underperform."""

BINPACK_SPEC = """You are participating in an evolutionary program search (FunSearch/AlphaEvolve style) for a BIN PACKING heuristic.

TASK: implement
    def pack(payload) -> list[list[int]]
where payload = {"items": [sizes...], "capacity": int}. Return a list of bins; each bin is a list of item INDICES. Every item must appear in exactly one bin, and no bin's total size may exceed the capacity.

Rules: pure Python (stdlib only), must finish all evaluation instances within ~20 seconds.

EVALUATION: 16 instances (uniform sizes, small-size sets {3,7,11,13}, mid-size 40-70, mixed). Score = mean over instances of (bins used / lower bound ceil(total/capacity)). LOWER IS BETTER; 1.0 is perfect. Reference: First-Fit-Decreasing typically scores ~1.02-1.10. Current best known evolutionary score: {best} (lower = better).

{context}

Respond with a brief explanation of your idea, then ONE complete Python code block defining `pack`."""

def parents_block(parents, lower_better=False):
    parts = []
    for i, (code, fit, note) in enumerate(parents):
        parts.append(f"--- PARENT {i+1} (fitness {fit:.4f}) ---\n{note}\n```python\n{code}\n```")
    return "\n\n".join(parts)

def fill(spec, **kw):
    for k, v in kw.items():
        spec = spec.replace("{" + k + "}", str(v))
    return spec

def evolve(model, task, n_gens, seed, island=None, remedy=False):
    rng = random.Random(seed)
    traces = gen_traces() if task == "cache" else None
    insts = gen_bin_instances() if task == "binpack" else None
    base_txt = ""
    if task == "cache":
        bl = json.load(open(f"{OUT}/baselines.json"))
        base_txt = "Belady(optimal)=%s  LFU=%s  LRU=%s  Random=%s" % (
            bl["belady_mean"], bl["lfu_mean"], bl["lru_mean"], bl["random_mean"])
    spec = CACHE_SPEC if task == "cache" else BINPACK_SPEC
    if remedy:
        spec += "\n\nIMPORTANT FORMAT CONSTRAINT: your ENTIRE response (thinking included) must fit in ~3500 tokens. Output the ```python code block FIRST, then at most 2 sentences of explanation. Keep any reasoning extremely brief."
    tag = model.replace("/", "_").replace(":", "_") + (f"__i{island}" if island is not None else "")
    logfile = f"{OUT}/runs/{task}_{tag}.jsonl"
    # resume: rebuild archive/best from a previous log so killed runs can continue
    start_gen, archive, best = 0, [], None
    if os.path.exists(logfile) and "--resume" in sys.argv:
        seen = set()
        for l in open(logfile):
            d = json.loads(l)
            if d.get("score", 0) and d.get("code") and "errors" in d and not d.get("errors"):
                h = hashlib.md5(d["code"].encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    archive.append((d["code"], d["score"], d.get("per"), [], h))
                    if best is None or (task == "cache" and d["score"] > best[1]) or (task == "binpack" and d["score"] < best[1]):
                        best = (d["code"], d["score"])
            start_gen = max(start_gen, d.get("gen", 0) + 1)
        start_gen = min(start_gen, n_gens)
        print(f"[resume] {model}: restarting at gen {start_gen} with {len(archive)} archived candidates", flush=True)
    log = open(logfile, "a")
    tok_out = tok_in = 0
    for gi in range(n_gens):
        gen = start_gen + gi
        if not archive:
            prompt = fill(spec, baselines=base_txt, best="none yet",
                                 context="This is generation 0: write a reasonable starting policy. A good baseline is LRU or LFU; you will improve on it in later generations.")
        else:
            ranked = sorted(archive, key=lambda c: c[1], reverse=(task == "cache"))
            mode = rng.random()
            if mode < 0.5 or len(ranked) < 2:
                parents = [ranked[0]] + rng.sample(ranked[:max(2, len(ranked))], 1)
                ctx = "IMPROVE the best parent. Identify its weakness on the traces, then write an improved version. You may build on its idea or replace it."
            elif mode < 0.8:
                a, b = rng.sample(ranked[:max(2, len(ranked))], 2)
                parents = [a, b]
                ctx = "CROSSOVER: combine the strongest ideas of both parents into one program that beats both."
            else:
                parents = [ranked[0]]
                ctx = "DIVERSITY KICK: the current family may be stuck in a local optimum. Propose a DIFFERENT strategy class (e.g. frequency/recency blend, anti-correlation with recent scans, protection of hot keys, segment-based policies, StackDistance-style ideas) — anything principled that could do better."
            notes = []
            for c in parents:
                if c[3]:
                    notes.append(f"(previous run FAILED: {'; '.join(c[3][:2])})")
                else:
                    notes.append(f"(per-trace: {c[2]})" if task == "cache" else f"(per-instance scores: {c[2]})")
            pblock = parents_block([(p[0], p[1], n) for p, n in zip(parents, notes)])
            prompt = fill(spec, baselines=base_txt, best=f"{ranked[0][1]:.4f}", context=f"Surviving parent programs:\n\n{pblock}\n\n{ctx}")
        try:
            txt, co, pi = llm(model, prompt, max_tokens=6000, temperature=EVO_TEMP)
        except RuntimeError as e:
            log.write(json.dumps({"gen": gen, "error": str(e)}) + "\n"); log.flush(); continue
        tok_out += co; tok_in += pi
        code = extract_code(txt)
        if not code:
            log.write(json.dumps({"gen": gen, "score": 0, "error": "no code block in response", "raw": txt[:200]}) + "\n"); log.flush(); continue
        h = hashlib.md5(code.encode()).hexdigest()
        if any(a[4] == h for a in archive):
            log.write(json.dumps({"gen": gen, "score": 0, "error": "duplicate of existing candidate"}) + "\n"); log.flush(); continue
        if task == "cache":
            fit, per, errs, dt = eval_cache(code, traces)
        else:
            fit, per, errs, dt = eval_binpack(code, insts)
        rec = {"gen": gen, "score": round(fit, 5), "per": per, "errors": errs[:3], "eval_s": round(dt, 2),
               "tok_out": co, "code_chars": len(code)}
        if fit > 0 and not errs:
            rec["code"] = code
            archive.append((code, fit, per, errs, h))
            if best is None or (task == "cache" and fit > best[1]) or (task == "binpack" and fit < best[1]):
                best = (code, fit)
                rec["new_best"] = True
                open(f"{OUT}/runs/best_{task}_{model.replace('/', '_').replace(':', '_')}.py", "w").write(f"# fitness {fit}\n" + code)
        else:
            rec["code"] = code[:1500]
        log.write(json.dumps(rec) + "\n"); log.flush()
    log.write(json.dumps({"gen": start_gen + n_gens, "FINAL_BEST": best[1] if best else None, "tok_out": tok_out, "tok_in": tok_in}) + "\n")
    log.close()
    return best

# ================================================================ MAIN
if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "cache"
    n_gens = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    models = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    os.makedirs(f"{OUT}/runs", exist_ok=True)
    if task == "cache":
        # compute baselines once
        traces = gen_traces()
        bl = {}
        def lru(tr):
            c, last, h, m, t = [], {}, 0, 0, 0
            for k in tr:
                t += 1
                if k in c: h += 1
                else:
                    m += 1
                    if len(c) >= CAP: c.remove(min(c, key=lambda x: last.get(x, 0)))
                    c.append(k)
                last[k] = t
            return h / (h + m)
        def lfu(tr):
            c, f, h, m = [], Counter(), 0, 0
            for k in tr:
                if k in c: h += 1
                else:
                    m += 1
                    if len(c) >= CAP: c.remove(min(c, key=lambda x: f[x]))
                    c.append(k)
                f[k] += 1
            return h / (h + m)
        def rnd(tr):
            r = random.Random(0); c = []; h = m = 0
            for k in tr:
                if k in c: h += 1
                else:
                    m += 1
                    if len(c) >= CAP: c.remove(r.choice(c))
                    c.append(k)
            return h / (h + m)
        def belady(tr):
            nxt = [math.inf] * len(tr); seen = {}
            for i in range(len(tr) - 1, -1, -1):
                nxt[i] = seen.get(tr[i], math.inf); seen[tr[i]] = i
            c, inc_n, h, m = [], {}, 0, 0
            for i, k in enumerate(tr):
                if k in c: h += 1; inc_n[k] = nxt[i]
                else:
                    m += 1
                    if len(c) >= CAP:
                        v = max(c, key=lambda x: inc_n[x]); c.remove(v); del inc_n[v]
                    c.append(k); inc_n[k] = nxt[i]
            return h / (h + m)
        for name, f in [("lru", lru), ("lfu", lfu), ("random", rnd), ("belady", belady)]:
            vals = [f(tr) for tr in traces.values()]
            bl[name + "_mean"] = round(sum(vals) / len(vals), 4)
            bl[name + "_per"] = {n: round(v, 4) for n, v in zip(traces.keys(), vals)}
        json.dump(bl, open(f"{OUT}/baselines.json", "w"), indent=1)
        print("baselines:", json.dumps(bl["belady_per"]), bl)
    import threading
    results = {}
    lock = threading.Lock()
    def run_island(m, island, gens, remedy=False):
        try:
            b = evolve(m, task, gens, seed=(hash(m) % 10000) + (island or 0) * 977, island=island, remedy=remedy)
        except Exception as e:
            b = ("ERR", str(e))
        with lock:
            key = m if island is None else f"{m}#i{island}"
            results[key] = b
        print(f"[done] {key}: {b[1] if b else None}", flush=True)
    def worker(spec_):
        # spec_: "model:count" (count = parallel islands) or "model" or "model REMEDY"
        remedy = spec_.endswith("REMEDY")
        s = spec_.replace(" REMEDY", "")
        if "*" in s:
            m, cnt = s.rsplit("*", 1); cnt = int(cnt)
        else:
            m, cnt = s, 1
        if cnt <= 1:
            done = _gens_done(m, task)
            run_island(m, None, max(0, n_gens - done), remedy)
        else:  # islands split the remaining budget; island 0 resumes the main log
            threads_ = []
            base = n_gens // cnt
            for k in range(cnt):
                g = base + (n_gens - base * cnt if k == 0 else 0)
                threads_.append(threading.Thread(target=run_island, args=(m, None if k == 0 else k, g, remedy)))
            for t in threads_: t.start()
            for t in threads_: t.join()
    def _gens_done(m, task_):
        f = f"{OUT}/runs/{task_}_{m.replace('/', '_').replace(':', '_')}.jsonl"
        if not os.path.exists(f): return 0
        gens = [json.loads(l)["gen"] for l in open(f)]
        return (max([g for g in gens if g < n_gens], default=-1) + 1) if gens else 0
    if models is None:
        models = ["soclaas/llama3.1:8b", "soclaas/qwen3.5:9b", "soclaas/gemma4:26b", "soclaas/qwen3.8:27b",
                  "soclaas/ornith1.5:35b", "soclaas/qwen3.6:35b", "soclaas/qwen3-coder-next",
                  "soclaas/coding", "soclaas/x-test-1", "soclaas/x-test-2", "soclaas/x-test-3", "soclaas/qwen3-vl:32b"]
    threads = [threading.Thread(target=worker, args=(m,)) for m in models]
    for t in threads: t.start()
    for t in threads: t.join()
    print(json.dumps({k: (v[1] if isinstance(v, tuple) else v) for k, v in results.items()}, indent=1))
