# soclaas_x-test-1 | cache | fitness 0.62058
import math
import random

# --- tunable constants (targets for future generations) ---
_TAU = 800.0   # recency decay time constant, in requests (~16 * capacity)
_BAND = 2.0    # near-tie band: evict randomly among keys scoring within
               # _BAND * min_score  (randomization dodges LRU's cyclic pathology)


def evict(cache, meta):
    """Return index in `cache` of the item to evict on a miss.

    Policy: minimum time-decayed frequency
        score = freq * exp(-age / tau),  age = time - last_access
    with randomized tie-breaking inside a near-tie band.
    """
    n = len(cache)
    if n <= 1:
        return 0

    t = meta["time"]
    freq = meta.get("cache_freq") or {}
    last = meta.get("cache_last") or {}

    scores = []
    for k in cache:
        f = freq.get(k, 1)
        if f < 1:
            f = 1
        age = t - last.get(k, t)
        if age < 0:
            age = 0
        scores.append(f * math.exp(-age / _TAU))

    m = min(scores)
    thresh = m * _BAND + 1e-12

    # candidates: all keys essentially as cold as the coldest key
    cands = [i for i, s in enumerate(scores) if s <= thresh]

    if len(cands) == 1:
        return cands[0]
    # random among near-ties: acts like Random on cycles/scans where
    # frequency carries no signal, but like cold-first eviction otherwise
    return random.choice(cands)