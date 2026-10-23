# soclaas_coding | cache | fitness 0.45272
import math

_TAU = 64.0

def evict(cache, meta):
    time = meta.get("time", 0)
    recent = meta.get("recent", ())
    # count recent window for cache keys? 
    win = {}
    # only need counts for keys in cache, but current requested last maybe not in cache; can count all then lookup.
    for k in recent:
        win[k] = win.get(k, 0) + 1
    cf = meta.get("cache_freq", {})
    cl = meta.get("cache_last", {})
    best_i = 0
    best_s = float("inf")
    # maybe capacity = len(cache)
    for i, k in enumerate(cache):
        f = cf.get(k, 0)
        age = max(0, time - cl.get(k, time))
        # local frequency in last 64; if key not recent, 0
        w = win.get(k, 0)
        # score to keep: higher better
        # log frequency: log1p(f)
        # window factor: 1+w
        # recency decay: 1/(1+age/tau)
        s = (1.0 + w) * (1.0 + math.log1p(f)) * (1.0 / (1.0 + age / _TAU))
        # tie-break: prefer evict older? If same score, maybe evict older (larger age) or lower f. 
        if s < best_s or (s == best_s and age > best_age):
             best_s=s; best_i=i; best_age=age
    return best_i