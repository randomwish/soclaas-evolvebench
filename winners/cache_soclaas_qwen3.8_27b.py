# soclaas_qwen3.8_27b | cache | fitness 0.48294
import math

# Tunable constants for the generation-0 baseline.
_FREQ_TAU = 900.0
_REC_TAU = 45.0
_REPEAT_TAU = 500.0

_W_FREQ = 16.0
_W_RECENT = 4.0
_W_RECENT_REC = 1.5
_REPEAT_BONUS = 3.0
_MAX_RECENT = 4


def evict(cache, meta):
    """
    Return the index of the cache item to evict.

    The policy assigns each cached key a keep-score:
      - log-compressed lifetime frequency, slowly decayed by age
      - a bonus for keys that have been seen more than once
      - strong bonus for repeated hits in the last 64 requests
      - a small pure-recency term

    The lowest-scoring cached key is evicted.
    """
    if not cache:
        return 0

    time = meta.get("time", 0)
    freq = meta.get("cache_freq", {})
    last = meta.get("cache_last", {})
    recent = meta.get("recent", [])

    # Count recent hits per key, capped to avoid over-weighting extreme repeats.
    recent_count = {}
    for k in recent:
        c = recent_count.get(k, 0)
        if c < _MAX_RECENT:
            recent_count[k] = c + 1

    exp = math.exp
    log1p = math.log1p

    best_idx = 0
    best_score = None
    best_age = -1

    for i, k in enumerate(cache):
        f = freq.get(k, 1)
        l = last.get(k, -1)

        age = time - l
        if age < 0:
            age = 0

        c = recent_count.get(k, 0)
        if c > _MAX_RECENT:
            c = _MAX_RECENT

        # Lifetime frequency, compressed and decayed.
        score = _W_FREQ * log1p(f) * exp(-age / _FREQ_TAU)

        # Anti-scan bonus: any key observed before is more valuable than a fresh one-touch key.
        if f > 1:
            score += _REPEAT_BONUS * exp(-age / _REPEAT_TAU)

        # Recent-window repetition and recency.
        if c:
            score += _W_RECENT * c
        score += _W_RECENT_REC * exp(-age / _REC_TAU)

        # Evict lowest score; on near-ties, evict the older item.
        if (
            best_score is None
            or score < best_score - 1e-9
            or (abs(score - best_score) <= 1e-9 and age > best_age)
        ):
            best_score = score
            best_idx = i
            best_age = age

    return best_idx