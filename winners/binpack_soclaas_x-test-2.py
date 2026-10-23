# soclaas_x-test-2 | binpack | fitness 1.08533
def pack(payload):
    import time
    import random
    import itertools

    items = payload["items"]
    capacity = payload["capacity"]
    n = len(items)
    if n == 0:
        return []

    total = sum(items)
    if total == 0:
        return [list(range(n))]

    LB = (total + capacity - 1) // capacity
    if len(items) == 1:
        return [[0]]

    start_time = time.time()
    deadline = start_time + 1.12

    def loads_of(bins):
        return [sum(items[i] for i in b) for b in bins]

    def first_fit_decreasing(order):
        bins = []
        loads = []
        for idx in order:
            sz = items[idx]
            placed = False
            for i, load in enumerate(loads):
                if load + sz <= capacity:
                    bins[i].append(idx)
                    loads[i] += sz
                    placed = True
                    break
            if not placed:
                bins.append([idx])
                loads.append(sz)
        return bins, loads

    def best_fit_decreasing(order):
        bins = []
        loads = []
        for idx in order:
            sz = items[idx]
            best_i = -1
            best_rem = capacity + 1
            for i, load in enumerate(loads):
                rem = capacity - load - sz
                if rem >= 0 and rem < best_rem:
                    best_rem = rem
                    best_i = i
            if best_i == -1:
                bins.append([idx])
                loads.append(sz)
            else:
                bins[best_i].append(idx)
                loads[best_i] += sz
        return bins, loads

    order_desc = sorted(range(n), key=lambda i: (-items[i], i))
    bins_bfd, loads_bfd = best_fit_decreasing(order_desc)
    bins_ffd, loads_ffd = first_fit_decreasing(order_desc)

    if len(bins_bfd) <= len(bins_ffd):
        best_bins = [b[:] for b in bins_bfd]
        best_loads = loads_bfd[:]
    else:
        best_bins = [b[:] for b in bins_ffd]
        best_loads = loads_ffd[:]
    best_count = len(best_bins)

    def update_solution(sol):
        nonlocal best_bins, best_loads, best_count
        if sol is None:
            return False
        if len(sol) < best_count:
            best_bins = [b[:] for b in sol]
            best_loads = loads_of(best_bins)
            best_count = len(best_bins)
            return True
        return False

    if best_count <= LB:
        return best_bins

    # ------------------------------------------------------------------
    # Minimum Bin Slack, order-based variant
    # ------------------------------------------------------------------
    def subset_sum_best_from_order(order, cap):
        if not order:
            return []
        s = 0
        for i in order:
            s += items[i]
        if s <= cap:
            return order[:]

        if cap <= 200000:
            bits = 1
            hist = [1]
            mask = (1 << (cap + 1)) - 1
            for idx in order:
                sz = items[idx]
                if sz <= cap:
                    bits = (bits | (bits << sz)) & mask
                hist.append(bits)
            target = bits.bit_length() - 1
            if target < 0:
                return []
            subset = []
            rem = target
            for i in range(len(order) - 1, -1, -1):
                idx = order[i]
                sz = items[idx]
                if rem >= sz and ((hist[i] >> (rem - sz)) & 1):
                    subset.append(idx)
                    rem -= sz
            return subset
        else:
            subset = []
            cur = 0
            for idx in order:
                sz = items[idx]
                if cur + sz <= cap:
                    subset.append(idx)
                    cur += sz
            return subset

    def mbs_order(mode, seed, limit):
        rem = list(range(n))
        rem_sum = total
        bins = []
        rng = random.Random(seed)
        while rem:
            if time.time() > limit:
                return None
            if rem_sum <= capacity:
                bins.append(rem[:])
                break

            if mode == 0:
                order = sorted(rem, key=lambda i: -items[i])
            elif mode == 1:
                order = sorted(rem, key=lambda i: items[i])
            else:
                order = rem[:]
                random.Random(seed + len(bins) * 997).shuffle(order)

            subset = subset_sum_best_from_order(order, capacity)
            if not subset:
                subset = [order[0]]

            bins.append(subset)
            subset_sum = sum(items[i] for i in subset)
            rem_sum -= subset_sum
            subset_set = set(subset)
            rem = [i for i in rem if i not in subset_set]
        return bins

    # ------------------------------------------------------------------
    # Minimum Bin Slack, repeated-size count-based variant
    # ------------------------------------------------------------------
    def best_subset_counts(counts, cap, rng, limit):
        groups = []
        sizes = list(counts.keys())
        rng.shuffle(sizes)

        for size in sizes:
            if size <= 0:
                continue
            max_use = cap // size
            cnt = min(counts[size], max_use)
            k = 1
            while cnt > 0:
                take = min(k, cnt)
                shift = size * take
                if shift <= cap:
                    groups.append((size, take))
                cnt -= take
                k <<= 1

        rng.shuffle(groups)
        bits = 1
        history = [1]
        mask = (1 << (cap + 1)) - 1

        for gi, (size, mult) in enumerate(groups):
            if (gi & 15) == 0 and time.time() > limit:
                return None
            shift = size * mult
            bits = (bits | (bits << shift)) & mask
            history.append(bits)

        target = bits.bit_length() - 1
        if target <= 0:
            return None

        chosen = {}
        cur = target
        for idx in range(len(groups) - 1, -1, -1):
            prev = history[idx]
            if (prev >> cur) & 1:
                continue
            size, mult = groups[idx]
            chosen[size] = chosen.get(size, 0) + mult
            cur -= size * mult
        return chosen

    def mbs_counts(seed, limit):
        size_lists = {}
        for idx, sz in enumerate(items):
            size_lists.setdefault(sz, []).append(idx)

        counts = {sz: len(lst) for sz, lst in size_lists.items()}
        rng = random.Random(seed)
        bins = []

        while counts:
            if time.time() > limit:
                return None

            chosen = best_subset_counts(counts, capacity, rng, limit)
            if chosen is None:
                return None
            if not chosen:
                sz = max(counts)
                chosen = {sz: 1}

            bin_items = []
            for sz, mult in chosen.items():
                lst = size_lists.get(sz, [])
                mult = min(mult, len(lst))
                for _ in range(mult):
                    bin_items.append(lst.pop())
                counts[sz] -= mult
                if counts[sz] <= 0:
                    del counts[sz]

            if not bin_items:
                break
            bins.append(bin_items)

        return bins

    # ------------------------------------------------------------------
    # Exact/near-exact packing of a small group into at most target bins
    # ------------------------------------------------------------------
    def exact_pack_subset(inds, target, time_limit):
        if not inds:
            return []
        total_g = sum(items[i] for i in inds)
        if total_g > target * capacity:
            return None
        if target <= 0:
            return None
        if total_g <= capacity:
            return [inds[:]]
        if target == 1:
            return None

        # Fast two-bin exact split by subset sum.
        if target == 2:
            low = total_g - capacity
            if low < 0:
                low = 0
            use_bits = capacity <= 5000 or (capacity <= 50000 and len(inds) <= 40)
            if use_bits:
                bits = 1
                hist = [1]
                mask = (1 << (capacity + 1)) - 1
                for idx in inds:
                    sz = items[idx]
                    if sz <= capacity:
                        bits = (bits | (bits << sz)) & mask
                    hist.append(bits)

                possible = bits & (((1 << (capacity + 1)) - 1) ^ ((1 << low) - 1))
                if possible == 0:
                    return None

                target_sum = possible.bit_length() - 1
                subset = []
                rem = target_sum
                for i in range(len(inds) - 1, -1, -1):
                    idx = inds[i]
                    sz = items[idx]
                    if rem >= sz and ((hist[i] >> (rem - sz)) & 1):
                        subset.append(idx)
                        rem -= sz

                subset_sum = target_sum
                comp_sum = total_g - subset_sum
                if subset_sum <= capacity and comp_sum <= capacity:
                    subset_set = set(subset)
                    bin2 = [i for i in inds if i not in subset_set]
                    return [b for b in (subset, bin2) if b]
                return None

        sorted_inds = sorted(inds, key=lambda i: -items[i])

        # Quick best-fit feasibility attempt.
        loads_h = [0] * target
        assign_h = [-1] * len(sorted_inds)
        ok = True
        for pos, idx in enumerate(sorted_inds):
            sz = items[idx]
            best_b = -1
            best_rem = capacity + 1
            for b in range(target):
                rem = capacity - loads_h[b] - sz
                if rem >= 0 and rem < best_rem:
                    best_rem = rem
                    best_b = b
            if best_b == -1:
                ok = False
                break
            loads_h[best_b] += sz
            assign_h[pos] = best_b

        if ok:
            res = [[] for _ in range(target)]
            for pos, b in enumerate(assign_h):
                res[b].append(sorted_inds[pos])
            return [b for b in res if b]

        # General DFS.
        szs = [items[i] for i in sorted_inds]
        m = len(szs)
        loads = [0] * target
        assignment = [-1] * m
        suffix = [0] * (m + 1)
        for i in range(m - 1, -1, -1):
            suffix[i] = suffix[i + 1] + szs[i]

        memo = set()
        start_dfs = time.time()

        def dfs(pos):
            if time.time() - start_dfs > time_limit:
                raise TimeoutError
            if pos == m:
                return True
            if suffix[pos] > target * capacity - sum(loads):
                return False

            key = (pos, tuple(sorted(loads)))
            if key in memo:
                return False

            sz = szs[pos]
            cand = [b for b in range(target) if loads[b] + sz <= capacity]
            cand.sort(key=lambda b: -loads[b])

            prev = -1
            for b in cand:
                if loads[b] == prev:
                    continue
                prev = loads[b]
                loads[b] += sz
                assignment[pos] = b
                if dfs(pos + 1):
                    return True
                loads[b] -= sz
                assignment[pos] = -1

            memo.add(key)
            return False

        try:
            ok = dfs(0)
        except TimeoutError:
            return None

        if ok:
            res = [[] for _ in range(target)]
            for pos, b in enumerate(assignment):
                res[b].append(sorted_inds[pos])
            return [b for b in res if b]
        return None

    # ------------------------------------------------------------------
    # Initial MBS attempts
    # ------------------------------------------------------------------
    if capacity <= 100000 and n <= 20000:
        count_deadline = min(deadline, start_time + 0.32)
        for seed in range(8):
            if time.time() > count_deadline:
                break
            sol = mbs_counts(1000 + seed * 7919, count_deadline)
            update_solution(sol)
            if best_count <= LB:
                return best_bins

    modes = []
    if n <= 1000 and capacity <= 20000:
        modes = [(0, 0), (1, 0), (2, 1), (2, 2), (2, 3), (2, 4)]
    elif n <= 300 and capacity <= 200000:
        modes = [(0, 0), (1, 0), (2, 1), (2, 2)]
    elif n <= 150 and capacity <= 1000000:
        modes = [(0, 0), (2, 1)]
    elif n <= 2000:
        modes = [(2, 1)]

    if modes:
        order_deadline = min(deadline, start_time + 0.68)
        for mode, seed in modes:
            if time.time() > order_deadline:
                break
            sol = mbs_order(mode, seed, order_deadline)
            update_solution(sol)
            if best_count <= LB:
                return best_bins

    if best_count <= LB:
        return best_bins

    # ------------------------------------------------------------------
    # Exact assignment search for small n
    # ------------------------------------------------------------------
    def try_exact_K(K, time_limit):
        if K * capacity < total:
            return ("INFEASIBLE", None)

        order = sorted(range(n), key=lambda i: -items[i])

        # Quick BFD into K bins.
        loads_h = [0] * K
        assign_h = [-1] * n
        ok = True
        for idx in order:
            sz = items[idx]
            best_b = -1
            best_rem = capacity + 1
            for b in range(K):
                rem = capacity - loads_h[b] - sz
                if rem >= 0 and rem < best_rem:
                    best_rem = rem
                    best_b = b
            if best_b == -1:
                ok = False
                break
            loads_h[best_b] += sz
            assign_h[idx] = best_b

        if ok:
            res = [[] for _ in range(K)]
            for idx in range(n):
                if assign_h[idx] != -1:
                    res[assign_h[idx]].append(idx)
            return ("OK", [b for b in res if b])

        caps = [capacity] * K
        assignment = [-1] * n
        start_k = time.time()
        memo = set()

        def dfs(pos):
            if time.time() - start_k > time_limit:
                raise TimeoutError
            if pos == n:
                return True

            key = (pos, tuple(sorted(caps)))
            if key in memo:
                return False

            idx = order[pos]
            sz = items[idx]
            cand = [b for b in range(K) if caps[b] >= sz]
            cand.sort(key=lambda b: caps[b])

            prev = -1
            for b in cand:
                c = caps[b]
                if c == prev:
                    continue
                prev = c
                caps[b] -= sz
                assignment[idx] = b
                if dfs(pos + 1):
                    return True
                caps[b] += sz
                assignment[idx] = -1
                if c == capacity:
                    break

            memo.add(key)
            return False

        try:
            ok = dfs(0)
        except TimeoutError:
            return ("TIMEOUT", None)

        if ok:
            res = [[] for _ in range(K)]
            for idx in range(n):
                res[assignment[idx]].append(idx)
            return ("OK", [b for b in res if b])
        return ("INFEASIBLE", None)

    if n <= 62 and time.time() < deadline:
        exact_deadline = min(deadline, start_time + 0.96)
        for K in range(LB, best_count):
            if time.time() > exact_deadline:
                break
            remaining = exact_deadline - time.time()
            if remaining <= 0:
                break
            status, sol = try_exact_K(K, min(0.28, remaining))
            if status == "OK":
                best_bins = [b[:] for b in sol]
                best_loads = loads_of(best_bins)
                best_count = len(best_bins)
                if best_count <= LB:
                    return best_bins
                break
            elif status == "TIMEOUT":
                break

    if best_count <= LB:
        return best_bins

    # ------------------------------------------------------------------
    # Local search and group repacking
    # ------------------------------------------------------------------
    def pack_group(inds, target, time_limit):
        return exact_pack_subset(inds, target, time_limit)

    bins = [b[:] for b in best_bins]
    loads = best_loads[:]

    while len(bins) > LB and time.time() < deadline:
        # Standard local search loop.
        while len(bins) > LB and time.time() < deadline:
            improved = False
            B = len(bins)

            # Greedy merge of two bins.
            order_bins = sorted(range(B), key=lambda i: loads[i])
            best_pair = None
            best_sum = -1
            M = min(B, 200)

            for ai in range(M):
                i = order_bins[ai]
                if loads[i] >= capacity:
                    continue
                rem_cap = capacity - loads[i]
                for bi in range(ai + 1, M):
                    j = order_bins[bi]
                    if loads[j] > rem_cap:
                        break
                    s = loads[i] + loads[j]
                    if s > best_sum:
                        best_sum = s
                        best_pair = (i, j)

            if best_pair is not None:
                i, j = best_pair
                bins[i].extend(bins[j])
                loads[i] += loads[j]
                del bins[j]
                del loads[j]
                improved = True
                continue

            cand_bins = sorted(range(B), key=lambda i: (loads[i], len(bins[i])))

            # Try 3 bins -> 2 bins.
            M = min(B, 40)
            cand = cand_bins[:M]
            found = False
            attempts = 0
            max_attempts = 2000

            for a in range(len(cand)):
                if found or time.time() >= deadline:
                    break
                i = cand[a]
                for b in range(a + 1, len(cand)):
                    if found or time.time() >= deadline:
                        break
                    j = cand[b]
                    for c in range(b + 1, len(cand)):
                        if found or time.time() >= deadline:
                            break
                        attempts += 1
                        if attempts > max_attempts:
                            break
                        k = cand[c]
                        total_load = loads[i] + loads[j] + loads[k]
                        if total_load > 2 * capacity:
                            continue
                        inds = bins[i] + bins[j] + bins[k]
                        res = pack_group(inds, 2, 0.02)
                        if res is not None:
                            rem = sorted([i, j, k], reverse=True)
                            for idx in rem:
                                del bins[idx]
                                del loads[idx]
                            for b_items in res:
                                load = sum(items[x] for x in b_items)
                                bins.append(b_items)
                                loads.append(load)
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

            if found:
                improved = True
                continue

            # Try 4 bins -> 3 bins.
            if B >= 4 and time.time() < deadline:
                M = min(B, 25)
                cand = cand_bins[:M]
                found = False
                attempts = 0
                max_attempts = 1000

                for comb in itertools.combinations(cand, 4):
                    if found or time.time() >= deadline:
                        break
                    attempts += 1
                    if attempts > max_attempts:
                        break
                    total_load = sum(loads[idx] for idx in comb)
                    if total_load > 3 * capacity:
                        continue
                    inds = []
                    for idx in comb:
                        inds.extend(bins[idx])
                    res = pack_group(inds, 3, 0.03)
                    if res is not None:
                        rem = sorted(comb, reverse=True)
                        for idx in rem:
                            del bins[idx]
                            del loads[idx]
                        for b_items in res:
                            load = sum(items[x] for x in b_items)
                            bins.append(b_items)
                            loads.append(load)
                        found = True
                        break

                if found:
                    improved = True
                    continue

            # Try 5 bins -> 4 bins.
            if B >= 5 and time.time() < deadline:
                M = min(B, 15)
                cand = cand_bins[:M]
                found = False
                attempts = 0
                max_attempts = 300

                for comb in itertools.combinations(cand, 5):
                    if found or time.time() >= deadline:
                        break
                    attempts += 1
                    if attempts > max_attempts:
                        break
                    total_load = sum(loads[idx] for idx in comb)
                    if total_load > 4 * capacity:
                        continue
                    inds = []
                    for idx in comb:
                        inds.extend(bins[idx])
                    res = pack_group(inds, 4, 0.04)
                    if res is not None:
                        rem = sorted(comb, reverse=True)
                        for idx in rem:
                            del bins[idx]
                            del loads[idx]
                        for b_items in res:
                            load = sum(items[x] for x in b_items)
                            bins.append(b_items)
                            loads.append(load)
                        found = True
                        break

                if found:
                    improved = True
                    continue

            # Try to eliminate one low-load bin by moving its items.
            if not improved and time.time() < deadline:
                cand_skip = sorted(range(B), key=lambda i: (loads[i], len(bins[i])))
                for skip in cand_skip:
                    if time.time() >= deadline:
                        break
                    if len(bins[skip]) > 35:
                        continue

                    other_bins = [i for i in range(B) if i != skip]
                    caps_other = [capacity - loads[i] for i in other_bins]
                    inds = bins[skip][:]
                    inds.sort(key=lambda i: -items[i])
                    total_move = sum(items[i] for i in inds)

                    if sum(caps_other) < total_move:
                        continue

                    m = len(inds)
                    assignment = [-1] * m
                    states = 0
                    start_dfs = time.time()
                    max_states = 30000

                    def dfs_elim(pos):
                        nonlocal states
                        states += 1
                        if states > max_states or time.time() - start_dfs > 0.05:
                            return False
                        if pos == m:
                            return True

                        idx = inds[pos]
                        sz = items[idx]
                        cand = []
                        seen = set()
                        for j, c in enumerate(caps_other):
                            if c >= sz and c not in seen:
                                cand.append((c, j))
                                seen.add(c)
                        cand.sort()

                        for c, j in cand:
                            caps_other[j] -= sz
                            assignment[pos] = j
                            if dfs_elim(pos + 1):
                                return True
                            caps_other[j] += sz
                            assignment[pos] = -1
                        return False

                    if dfs_elim(0):
                        for pos, j in enumerate(assignment):
                            actual_bin = other_bins[j]
                            idx = inds[pos]
                            bins[actual_bin].append(idx)
                            loads[actual_bin] += items[idx]
                        del bins[skip]
                        del loads[skip]
                        improved = True
                        break

                if improved:
                    continue

            if not improved:
                break

        if len(bins) <= LB or time.time() >= deadline:
            break

        # Ruin/recreate: select several bins and try to repack them into one fewer bin.
        rng2 = random.Random(999 + len(bins) * 17 + int(time.time() * 1000) % 1000)
        improved_ruin = False
        for _ in range(20):
            if time.time() >= deadline or len(bins) <= LB:
                break
            num = len(bins)
            if num < 2:
                break

            k = rng2.randint(2, min(6, num))
            selected = rng2.sample(range(num), k)
            total_sel = sum(loads[i] for i in selected)
            target = k - 1
            if total_sel > target * capacity:
                continue

            combined = []
            for i in selected:
                combined.extend(bins[i])
            if len(combined) > 70:
                continue

            res = exact_pack_subset(combined, target, min(0.08, deadline - time.time()))
            if res is not None:
                sel_set = set(selected)
                new_bins = []
                new_loads = []
                for i in range(num):
                    if i not in sel_set:
                        new_bins.append(bins[i])
                        new_loads.append(loads[i])
                for b in res:
                    if b:
                        new_bins.append(b)
                        new_loads.append(sum(items[x] for x in b))
                if len(new_bins) < len(bins):
                    bins = new_bins
                    loads = new_loads
                    improved_ruin = True
                    break

        if not improved_ruin:
            break

    if len(bins) < len(best_bins):
        return bins
    return best_bins