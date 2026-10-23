# SoCLaaS EvolveBench — generate–evaluate–evolve model bake-off

Final report: `REPORT.md`. Winning programs: `winners/`. Raw per-candidate logs: `runs/*.jsonl`. Harness: `evolve.py`.

_AlphaEvolve/FunSearch-style loop: each model writes candidate programs, they are executed in subprocess sandboxes, scored, and the score + survivor code is fed back for the next generation. 20 generations per model per task (islands for slow reasoners)._

## Task 1 — Online cache eviction policy

Fitness = mean hit rate over 5 fixed 20k-request traces (Zipf / drifting-Zipf / scan+hotset / cyclic-loop / LRU-killer), capacity 50. **Higher = better.**

| baseline | mean hit rate |
|---|---|
| Belady | 0.7115 |
| Random | 0.5265 |
| Lfu | 0.4583 |
| Lru | 0.4339 |

| model | best fitness | vs LRU | curve (best-so-far) | attempts | failed | tok out |
|---|---|---|---|---|---|---|
| soclaas_x-test-2 | **0.6443** | +48.5% | `···▁▅▆▆▇▇▇▇████████████████████` | 31 | 13 | 565,804 |
| soclaas_x-test-1 | **0.6206** | +43.0% | `▁▁▁▁▁▁▁▁▁▁▁▁█████████` | 21 | 18 | 300,000 |
| soclaas_qwen3-coder-next | **0.6162** | +42.0% | `▁▁▁▄▄▄▄█████████████` | 20 | 1 | 30,422 |
| soclaas_llama3.1_8b | **0.5857** | +35.0% | `····▁▁▁▁▁▁▁█████████` | 20 | 12 | 10,157 |
| soclaas_qwen3-vl_32b | **0.5653** | +30.3% | `▁▄▆▆▆▆▆▆████████████` | 20 | 2 | 25,385 |
| soclaas_ornith1.5_35b | **0.5534** | +27.5% | `▁▁▁▁▁▁▁▁▁███████████` | 20 | 14 | 42,000 |
| soclaas_qwen3.8_27b | **0.4829** | +11.3% | `·▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 29 | 27 | 280,000 |
| soclaas_gemma4_26b | **0.4759** | +9.7% | `···········▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 25 | 24 | 0 |
| soclaas_qwen3.6_35b | **0.4703** | +8.4% | `▁▁██████████████████` | 20 | 0 | 50,231 |
| soclaas_coding | **0.4527** | +4.3% | `·▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 20 | 19 | 72,000 |
| soclaas_x-test-3 | **fail** | — | `` | 30 | 30 | 0 |
| soclaas_qwen3.5_9b | **fail** | — | `` | 32 | 32 | 107,938 |

## Task 2 — Bin packing heuristic

Fitness = mean (bins used / L1 lower bound) over 16 instances. **Lower = better.** First-Fit-Decreasing reference = **1.0853**. Perfect = 1.0.

| model | best fitness | vs FFD | curve (best-so-far) | attempts | failed | tok out |
|---|---|---|---|---|---|---|
| soclaas_x-test-2 | **1.0853** | +0.0% | `▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 20 | 4 | 486,693 |
| soclaas_gemma4_26b | **1.0853** | +0.0% | `▁▁▁▁▁` | 5 | 4 | 0 |
| soclaas_qwen3.6_35b | **1.0853** | +0.0% | `·▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 20 | 4 | 41,256 |
| soclaas_x-test-1 | **1.0853** | +0.0% | `▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 14 | 10 | 0 |
| soclaas_qwen3-coder-next | **1.0853** | +0.0% | `▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 20 | 5 | 23,986 |
| soclaas_ornith1.5_35b | **1.0853** | +0.0% | `▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 20 | 14 | 268,310 |
| soclaas_qwen3.8_27b | **1.0853** | +0.0% | `▁▁▁▁▁▁▁▁▁▁▁` | 11 | 10 | 0 |
| soclaas_coding | **1.0853** | +0.0% | `···▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 20 | 19 | 160,000 |
| soclaas_qwen3-vl_32b | **1.0853** | +0.0% | `▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁` | 20 | 4 | 18,565 |
| soclaas_llama3.1_8b | **1.1189** | +3.1% | `······▁▁▁▁████████████` | 22 | 16 | 10,577 |
| soclaas_qwen3.5_9b | **fail** | — | `` | 18 | 18 | 0 |

## Composite

| model | cache (↑) | binpack (↓) | verdict |
|---|---|---|---|
| soclaas_x-test-2 | 0.6443 | 1.0853 | beats LRU by 48% |
| soclaas_x-test-1 | 0.6206 | 1.0853 | beats LRU by 43% |
| soclaas_qwen3-coder-next | 0.6162 | 1.0853 | beats LRU by 42% |
| soclaas_qwen3-vl_32b | 0.5653 | 1.0853 | beats LRU by 30% |
| soclaas_ornith1.5_35b | 0.5534 | 1.0853 | beats LRU by 28% |
| soclaas_llama3.1_8b | 0.5857 | 1.1189 | beats LRU by 35% |
| soclaas_qwen3.8_27b | 0.4829 | 1.0853 | beats LRU by 11% |
| soclaas_gemma4_26b | 0.4759 | 1.0853 | beats LRU by 10% |
| soclaas_qwen3.6_35b | 0.4703 | 1.0853 | beats LRU by 8% |
| soclaas_coding | 0.4527 | 1.0853 | beats LRU by 4% |
| soclaas_qwen3.5_9b | fail | fail | — |

## What actually got evolved (cache task)

- **x-test-2 (DeepSeek V4.1 Flash) — 0.6443:** a *trace-shape classifier* policy. It measures a uniqueness ratio and burst statistics over the 64-key recent window, detects "scan-like" vs "cyclic-like" vs "hot-set" regimes, and switches between frequency-weighted LRU, MRU-among-cold (anti-loop-thrash), and burst-protected cold eviction. Essentially a hand-rolled Adaptive Replacement Policy discovered by iteration.
- **x-test-1 (GLM 5.3 Flash) — 0.6206:** a *poor-man's Belady*. Keeps a per-key deque of the last 3 inter-arrival gaps, predicts each cached key's next access time, evicts the key predicted to return furthest in the future; keys seen only once are treated as never-returning (scan resistance), and keys overdue vs their predicted gap fall back to LRU handling.
- **qwen3-coder-next (80B A3B) — 0.6162:** recency + saturating global-frequency blend scored from the recent-window positions.
- **llama3.1:8b — 0.5857:** the smallest model beat every other open-weight model except qwen3-coder-next, with a compact recency/frequency hybrid. Best tok_efficiency of the field (~10k output tokens total vs 300-570k for the reasoners).

## Failure modes (they count as results)

- **qwen3.5:9b: 0/50 candidates produced a code block.** It spends its entire ~4k output budget on "Thinking Process:" prose before writing any code, across 32 attempts including a format-constrained remediation pass. Total waste.
- **x-test-3 (unnamed test model): down all day** — persistent HTTP 502 from the cluster; zero generations.
- **gemma4:26b: ollama-served and extremely slow** (~1 gen per 15-30 min), 24/25 requests failed under concurrent load; only 1 valid candidate each task.
- **The 27k-token reasoners** (x-test-1/2) burn ~10-25x the tokens of the small models per candidate and need islands to finish 20 generations in reasonable wall time. Quality per candidate is high; cost per point of fitness is ~100x llama3.1:8b's.

## Task-2 plateau

Every model that produced valid code converged to exactly the FFD reference (1.0853, identical per-instance vectors) — single-shot ordering heuristics saturate at FFD. Nobody found the search-based packing (local search inside the 20s budget) that would break below it. Cache eviction, with its online/adversarial structure, was the far more discriminative task.
