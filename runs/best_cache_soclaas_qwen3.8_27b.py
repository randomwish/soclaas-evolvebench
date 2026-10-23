# fitness 0.47153999999999996
import math

_TAU = 64.0

def evict(cache, meta):
    if not cache:
        return 0
    t = meta.get('time', 0)
    freq = meta.get('cache_freq', {})
    last = meta.get('cache_last', {})
    best_i = 0
    best_key = None
    best_score = float('inf')
    best_f = float('inf')
    best_last = float('inf')
    for i, k in enumerate(cache):
        f = freq.get(k, 0)
        l = last.get(k, t)
        age = t - l
        if age < 0: age = 0
        # score lower = evict
        score = math.log1p(f) * (64.0 / (age + 64.0))
        # If f == 0, score 0.
        # Tie: lower f, older (smaller last)
        if (score < best_score - 1e-12) or (abs(score - best_score) <= 1e-12 and (f < best_f or (f == best_f and l < best_last))):
             best_i = i; best_key=k; best_score=score; best_f=f; best_last=l
    return best_i