# soclaas_qwen3.6_35b | cache | fitness 0.47034
import math

def evict(cache, meta):
    """
    Evicts the item with the lowest Recency-Decayed Frequency Score.
    
    Score = freq / (1 + TSLA * decay)
    
    This policy combines LFU (frequency) with a recency decay factor.
    Unlike pure LFU, it adapts to changing hot sets because the score
    of an item decays over time if it is not accessed.
    Unlike LRU, it protects globally frequent items from being evicted
    by a single recent access (unless they become very frequent).
    
    This is particularly effective against 'Scan' traces where keys
    are accessed cyclically but not 'hot' in the long run, allowing
    stable hot keys to survive due to their lower TSLA.
    """
    if not cache:
        return -1

    cache_freq = meta.get("cache_freq", {})
    cache_last = meta.get("cache_last", {})
    current_time = meta.get("time", 0)
    
    # Decay factor: Controls how quickly frequency is discounted by staleness.
    # A smaller decay means more like LFU. A larger decay means more like LRU.
    # We use a moderate value to balance adaptability and stability.
    decay_rate = 0.05 

    best_evict_idx = -1
    lowest_score = float('inf')
    
    for idx, key in enumerate(cache):
        freq = cache_freq.get(key, 0)
        last_access = cache_last.get(key, 0)
        
        # Time Since Last Access
        tsla = current_time - last_access
        
        # Calculate Score
        # Using a power law decay or exponential decay can work.
        # Let's use a simple rational function for stability:
        # Score = freq / (1 + tsla * decay_rate)
        
        # If freq is 0, it's a candidate.
        # If freq > 0, it has some value.
        
        # Edge case: If tsla is 0 (just accessed), score is freq.
        # If tsla is large, score approaches 0.
        
        if freq == 0:
            score = 0.0
        else:
            # Add a small epsilon to denominator to avoid division by zero if tsla=0 and decay=0
            # But decay > 0, so denominator >= 1.
            score = freq / (1.0 + tsla * decay_rate)

        # We want to evict the LOWEST score.
        if score < lowest_score:
            lowest_score = score
            best_evict_idx = idx
        elif score == lowest_score:
            # Tie-breaker: Evict the one with the largest TSLA (oldest access)
            # because it's "colder".
            current_best_tsla = current_time - cache_last.get(cache[best_evict_idx], 0)
            if tsla > current_best_tsla:
                best_evict_idx = idx
                
    return best_evict_idx