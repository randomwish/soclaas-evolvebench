# fitness 0.47587999999999997
import math

def evict(cache, meta) -> int:
    """
    Implements an Aging-based Frequency-Recency Hybrid policy.
    Calculates an importance score for each item in the cache and 
    evicts the item with the minimum score.
    """
    curr_time = meta['time']
    cache_freq = meta['cache_freq']
    cache_last = meta['cache_last']
    
    best_idx = -1
    min_score = float('inf')

    for i, key in enumerate(cache):
        # Frequency of the key seen so far in the trace
        freq = cache_freq.get(key, 0)
        
        # Time elapsed since this key was last requested
        last_access = cache_last.get(key, curr_time)
        gap = curr_time - last_access
        
        # Importance Score:
        # We use log-transformed frequency to prevent high-frequency keys 
        # from dominating the cache indefinitely (protecting against drifting Zipf).
        # We use square-root decay on the recency gap to provide a smoother 
        # transition than LRU (protecting against scans).
        score = math.log1p(freq) / math.sqrt(gap + 1)

        if score < min_score:
            min_score = score
            best_idx = i

    return best_idx