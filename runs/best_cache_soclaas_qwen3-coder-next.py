# fitness 0.61616
def evict(cache, meta):
    t = meta["time"]
    recent = meta["recent"]
    global_freq = meta["cache_freq"]
    capacity = meta["capacity"]
    
    n_recent = len(recent)
    
    # Build last two positions in recent for each key in cache
    # recent[i] is most recent at index i, so position 0 = very recent
    last_pos = {}
    second_last_pos = {}
    
    # Scan recent from end (most recent) to start to get last two occurrences
    for i in range(n_recent - 1, -1, -1):
        key = recent[i]
        if key not in last_pos:
            last_pos[key] = i
        elif key not in second_last_pos:
            second_last_pos[key] = i
    
    # Now compute scores for each cached key
    scores = {}
    for idx, key in enumerate(cache):
        # Frequency: clamp to avoid division by zero
        gf = global_freq.get(key, 0)
        gf_score = min(1.0, gf / 10.0)  # normalize: 10+ freq = full score
        
        # Recency: position in recent (0 = very recent)
        rp = last_pos.get(key, n_recent)
        
        # Gap: time between last two accesses (only if ≥2 occurrences in recent)
        if key in second_last_pos:
            gap = last_pos[key] - second_last_pos[key]  # positive
            # Smaller gap → more stable pattern → protect
            gap_factor = max(0.2, 1.0 - gap / (n_recent + 1))
        else:
            # Only one occurrence — likely transient or scan
            gap_factor = 0.2
        
        # Gradient score: high if (recent & stable pattern) → low eviction score
        # Low if (old in recent OR unstable pattern) → high eviction score
        # Base: high recency (small rp) and small gap → very protected
        # Combine: use exponential decay on rp, modulated by gap stability
        recency_decay = 2 ** (-rp / max(1, n_recent / 4))
        gradient_score = recency_decay * gap_factor * (0.5 + gf_score)
        
        # Final score (higher = *more likely to evict*)
        # So we *invert*: low gradient_score → high eviction score
        evict_score = 1.0 - gradient_score
        
        # Amplify cold keys with only one recent appearance (scan suspects)
        if key not in last_pos or (key in last_pos and key not in second_last_pos):
            if gf <= 1:
                evict_score *= 2.5  # strong anti-scan boost
            elif gf <= 3:
                evict_score *= 1.8
        
        # Extra penalty for keys with *large* gaps (unstable, likely stale)
        if key in second_last_pos:
            gap = last_pos[key] - second_last_pos[key]
            if gap > n_recent // 2:
                evict_score *= 1.5
        
        # Protect keys that are *very* recent (top 3 in recent)
        if rp <= 2:
            evict_score *= 0.05  # near-zero eviction priority
        
        scores[idx] = evict_score
    
    # Evict highest score. Break ties by index (higher index = older in cache? not necessarily, so use index for stability)
    # We prefer higher index as tie-breaker (arbitrary but stable)
    return max(scores, key=lambda k: (scores[k], k))