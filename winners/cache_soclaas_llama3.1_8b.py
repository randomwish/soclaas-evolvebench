# soclaas_llama3.1_8b | cache | fitness 0.58572
import math
import collections

# module constants
CAPACITY = 50

def evict(cache, meta) -> int:
    # find least frequently used item in the last 64 requests (LFRU)
    lfu_cache_freq = collections.Counter(meta["recent"])
    
    # Dynamic weights for frequency and recency based on their relative importance
    alpha = max(0.5 * math.exp(1 - len(meta["cache_last"]) / CAPACITY), 0.2)  
    beta = 1 - alpha
    
    scores = {}
    for key in meta["cache_last"]:
        recentness = max(0, meta["time"] - meta["cache_last"][key])
        
        freq_in_recent_64 = min(lfu_cache_freq[key], 32)
        freq_outside_recent_64 = lfu_cache_freq.get(key, 0)
        
        # Introduce a "volatility" penalty for keys that are highly requested recently but have low frequency overall
        volatile_penalty = max(0, freq_outside_recent_64 / (max(freq_in_recent_64, 1) + 1))
        
        # Adaptive scoring function balancing frequency and recency with volatility consideration
        score = alpha * math.log10(max(freq_outside_recent_64, freq_in_recent_64) + 1) + beta * max(0, math.log10(freq_in_recent_64 + 1)) * (recentness - volatile_penalty)
        
        scores[key] = score
    
    # find index of lowest score (best candidate to evict)
    worst_key = min(scores, key=scores.get)
    
    return cache.index(worst_key)