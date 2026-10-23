# soclaas_ornith1.5_35b | cache | fitness 0.55338
def evict(cache, meta):
    from collections import Counter
    recent = meta["recent"]
    now = meta["time"]
    last = meta["cache_last"]
    freq = meta["cache_freq"]
    rc = Counter(recent)
    
    best_i = 0
    best_val = None
    for i, key in enumerate(cache):
        r = rc.get(key, 0)          # recent window frequency
        g = freq.get(key, 0)        # global frequency
        age = now - last.get(key, 0)  # recency age
        
        # Protection tiers:
        # Strongly protect: high global freq (LFU signal) — good for zipf/churn
        # Also protect: high recent freq (>= 2) — good for scan60
        if r >= 2 or g >= 3:
            # protected: rank by global freq (dominant) then recent freq then recency
            val = 1_000_000 + g * 1000 + r * 10 + age
        else:
            # probationary: evict by age (most aged first)
            val = age
        
        if best_val is None or val < best_val:
            best_val = val
            best_i = i
    return best_i