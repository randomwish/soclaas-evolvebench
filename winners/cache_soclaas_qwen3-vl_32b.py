# soclaas_qwen3-vl_32b | cache | fitness 0.5653
import random
from collections import defaultdict

def evict(cache, meta):
    time = meta["time"]
    cache_freq = meta["cache_freq"]
    cache_last = meta["cache_last"]
    recent = meta["recent"]
    capacity = meta["capacity"]

    if not cache:
        return 0

    # Detect scan vs burst: use last 32 requests (or as many as available)
    recent_len = len(recent)
    if recent_len < 32:
        # Not enough data — assume bursty
        scan_prob = 0.0
    else:
        # Count distinct keys in last 32
        distinct = len(set(recent[-32:]))
        # Scan score: proportion of distinct keys — higher = more likely scanning
        scan_score = distinct / 32.0
        # If > 0.7, likely scanning; if < 0.3, likely bursty
        scan_prob = max(0.0, min(1.0, (scan_score - 0.3) / 0.4))  # map [0.3, 0.7] to [0, 1]

    # Compute score for each item: higher score = less likely to evict
    scores = []

    for i, key in enumerate(cache):
        freq = cache_freq.get(key, 0)
        last_access = cache_last.get(key, 0)
        time_since_last = time - last_access

        # Frequency weight: higher frequency = higher score (keep it)
        freq_weight = 1.0 / (freq + 1)  # normalize, so high freq = low weight
        # Invert to make high freq = higher score
        freq_score = 1.0 - freq_weight

        # Recency weight: recent = higher score (keep it)
        recency_weight = 1.0 / (time_since_last + 1)
        recency_score = 1.0 - recency_weight  # invert for higher = better

        # Burst bonus: if key appears in recent, boost score
        recent_count = recent.count(key)
        burst_bonus = recent_count * 0.015  # tuned for better balance

        # Cold key detection: if accessed 8-32 steps ago, may be part of scan
        # In scan mode, we want to keep these
        if 8 <= time_since_last <= 32:
            cold_boost = 0.02
        else:
            cold_boost = 0.0

        # Adaptive scoring: blend based on scan_prob
        # In scan mode: favor frequency (freq_score), reduce recency
        # In burst mode: favor recency (recency_score), reduce frequency
        if scan_prob > 0.5:
            # Scan mode: prioritize frequency
            base_score = freq_score * 0.8 + recency_score * 0.2
            base_score += burst_bonus + cold_boost
        else:
            # Burst mode: prioritize recency
            base_score = recency_score * 0.8 + freq_score * 0.2
            base_score += burst_bonus + cold_boost

        scores.append((base_score, i))

    # Sort by score descending: highest score = least likely to evict
    scores.sort(key=lambda x: x[0], reverse=True)

    # Return index of item with lowest score (most evictable)
    return scores[-1][1]