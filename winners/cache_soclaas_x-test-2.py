# soclaas_x-test-2 | cache | fitness 0.6443
import math
import random


def evict(cache, meta):
    if not cache:
        return 0

    n = len(cache)
    time = meta.get("time", 0)
    cache_freq = meta.get("cache_freq", {})
    cache_last = meta.get("cache_last", {})
    recent = meta.get("recent", [])
    capacity = meta.get("capacity", n)

    recent_count = {}
    for k in recent:
        recent_count[k] = recent_count.get(k, 0) + 1

    L = len(recent)
    uniq = len(recent_count)
    uniq_ratio = (uniq / L) if L else 0.0
    max_r = max(recent_count.values()) if recent_count else 0

    freqs = [cache_freq.get(k, 0) for k in cache]
    lasts = [cache_last.get(k, -1) for k in cache]

    min_f = min(freqs) if freqs else 0
    max_f = max(freqs) if freqs else 0

    def mru_among(indices):
        best_i = indices[0]
        best_last = lasts[best_i]
        ties = [best_i]

        for i in indices[1:]:
            li = lasts[i]
            if li > best_last:
                best_i = i
                best_last = li
                ties = [i]
            elif li == best_last:
                ties.append(i)

        if len(ties) > 1:
            return random.choice(ties)
        return best_i

    def cold_evict(threshold):
        candidates = [i for i, f in enumerate(freqs) if f <= threshold]
        if not candidates:
            candidates = list(range(n))

        # Protect keys that are clearly part of a current burst.
        if max_r >= 3:
            cold = [i for i in candidates if recent_count.get(cache[i], 0) < 3]
            if cold:
                candidates = cold
            else:
                # All candidates are burst-hot. Evict the least valuable
                # among them, using a small frequency/recent tradeoff.
                best_i = candidates[0]
                best_score = freqs[best_i] + 4.0 * recent_count.get(cache[best_i], 0)
                best_last = lasts[best_i]

                for i in candidates[1:]:
                    score = freqs[i] + 4.0 * recent_count.get(cache[i], 0)
                    if score < best_score - 1e-12:
                        best_score = score
                        best_i = i
                        best_last = lasts[i]
                    elif abs(score - best_score) <= 1e-12 and lasts[i] > best_last:
                        best_i = i
                        best_last = lasts[i]
                return best_i

        # For scan/loop pollution, evict the most recently used cold key.
        return mru_among(candidates)

    # ---------- improved cyclic / loop detection ----------
    periodic = False
    if L >= 24 and uniq_ratio >= 0.35:
        max_k = min(32, L // 2)
        for k in range(3, max_k + 1):
            total = L - k
            if total <= 0:
                continue

            matches = 0
            for i in range(k, L):
                if recent[i] == recent[i - k]:
                    matches += 1

            if matches >= int(0.75 * total):
                if len(set(recent[-k:])) >= max(2, k // 2):
                    periodic = True
                    break

    if max_f == min_f:
        uniform = True
    else:
        uniform = (max_f - min_f <= 2)
        if max_f > 0 and (max_f - min_f) <= max(2, int(0.15 * max_f)):
            uniform = True

    similar_threshold = min_f + max(1, int(0.10 * min_f) + 1)
    similar_count = sum(1 for f in freqs if f <= similar_threshold)
    majority_similar = (min_f > 1 and similar_count >= int(0.50 * n))

    loop_mode = False
    if time > 2 * capacity and L >= 24 and uniq_ratio >= 0.45:
        if periodic or uniform:
            loop_mode = True
        elif majority_similar and uniq_ratio >= 0.50:
            loop_mode = True

    if loop_mode:
        if max_f - min_f <= 2:
            threshold = max_f
        else:
            sorted_f = sorted(freqs)
            med_f = sorted_f[n // 2]
            threshold = med_f + 1
        return cold_evict(threshold)

    # ---------- scan detection ----------
    scan_mode = False
    if time > capacity and L >= 32:
        if uniq_ratio >= 0.82:
            scan_mode = True
        elif uniq_ratio >= 0.72 and max_r <= 2:
            if max_f - min_f > max(5, 3 * min_f + 2):
                scan_mode = True

        if max_f - min_f <= 2 and uniq_ratio >= 0.85:
            scan_mode = True

        if uniq_ratio >= 0.70 and max_f > min_f * 3 + 2 and max_r <= 4:
            scan_mode = True

    if scan_mode:
        if max_f - min_f <= 2:
            threshold = max_f
        else:
            threshold = min_f
        return cold_evict(threshold)

    # ---------- drift detection ----------
    drift = False
    drift_score = 0.0

    if L >= 16 and time > 200:
        max_k = None
        max_r_val = 0

        for k, r in recent_count.items():
            if r > max_r_val:
                max_r_val = r
                max_k = k

            if r >= 2:
                f = cache_freq.get(k, 0)
                expected = f * L / (time + 1.0)
                surprise = r - expected - 2.5
                if surprise > 0:
                    drift_score += surprise

        if max_r_val >= 5 and max_k is not None:
            f = cache_freq.get(max_k, 0)
            expected = f * L / (time + 1.0)

            if max_r_val > expected * 2.5 + 4.0:
                drift = True

            if max_f > 0 and f < max_f * 0.4 and max_r_val >= 4:
                drift = True

        if drift_score > 10.0:
            drift = True

    if drift:
        TAU = 100.0
        FREQ_CAP = 32.0
        RECENT_BONUS = 12.0
    else:
        # Much closer to pure LFU on stationary Zipf traces.
        TAU = 20000.0
        FREQ_CAP = 100000.0
        RECENT_BONUS = 0.5

    # ---------- normal adaptive LFU / recency scoring ----------
    best_score = None
    candidates = []

    for i, key in enumerate(cache):
        f = freqs[i]
        last = lasts[i]

        age = time - last if last >= 0 else time + 1
        if age < 0:
            age = 0

        r = recent_count.get(key, 0)
        fcap = min(f, FREQ_CAP)
        decay = math.exp(-age / TAU)
        bonus = RECENT_BONUS * max(0, r - 1)
        score = fcap * decay + bonus

        if best_score is None or score < best_score - 1e-12:
            best_score = score
            candidates = [i]
        elif abs(score - best_score) <= 1e-12:
            candidates.append(i)

    if len(candidates) == 1:
        return candidates[0]

    # Tie-break toward the oldest last access.
    best_i = candidates[0]
    best_last = lasts[best_i]
    ties = [best_i]

    for i in candidates[1:]:
        li = lasts[i]
        if li < best_last:
            best_i = i
            best_last = li
            ties = [i]
        elif li == best_last:
            ties.append(i)

    if len(ties) > 1:
        return random.choice(ties)
    return best_i