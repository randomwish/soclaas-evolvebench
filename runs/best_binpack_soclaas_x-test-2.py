# fitness 1.0853322045933025
def pack(payload):
    import bisect

    items = payload["items"]
    cap = payload["capacity"]
    n = len(items)
    if n == 0:
        return []

    total = sum(items)
    lb = (total + cap - 1) // cap if cap > 0 else 0

    # Best-Fit-Decreasing
    def bfd():
        order = sorted(range(n), key=lambda i: items[i], reverse=True)
        free = []       # sorted free capacities
        bin_ids = []    # parallel bin indices
        bins = []
        for idx in order:
            s = items[idx]
            pos = bisect.bisect_left(free, s)
            if pos == len(free):
                bid = len(bins)
                bins.append([idx])
                nf = cap - s
                ins = bisect.bisect_left(free, nf)
                free.insert(ins, nf)
                bin_ids.insert(ins, bid)
            else:
                bid = bin_ids[pos]
                old = free[pos]
                nf = old - s
                free.pop(pos)
                bin_ids.pop(pos)
                bins[bid].append(idx)
                ins = bisect.bisect_left(free, nf)
                free.insert(ins, nf)
                bin_ids.insert(ins, bid)
        return bins

    # First-Fit-Decreasing
    def ffd():
        order = sorted(range(n), key=lambda i: items[i], reverse=True)
        bins = []
        loads = []
        for idx in order:
            s = items[idx]
            placed = False
            for b in range(len(bins)):
                if loads[b] + s <= cap:
                    bins[b].append(idx)
                    loads[b] += s
                    placed = True
                    break
            if not placed:
                bins.append([idx])
                loads.append(s)
        return bins

    bins1 = bfd()
    bins2 = ffd()

    if len(bins1) == lb:
        return bins1
    if len(bins2) == lb:
        return bins2

    bins = bins1 if len(bins1) <= len(bins2) else bins2
    loads = [sum(items[i] for i in b) for b in bins]

    max_iter = len(bins) * 2 + 10
    iter_count = 0
    improved = True

    while improved and iter_count < max_iter:
        improved = False
        iter_count += 1

        order = sorted(range(len(bins)), key=lambda b: loads[b])

        for target in order:
            if not bins[target]:
                continue

            target_items = bins[target][:]
            target_items.sort(key=lambda i: items[i], reverse=True)

            other_bins = [b for b in range(len(bins)) if b != target and bins[b]]
            if not other_bins:
                continue

            target_sum = sum(items[i] for i in target_items)
            total_res = sum(cap - loads[b] for b in other_bins)
            if target_sum > total_res:
                continue

            # Greedy redistribution attempt
            res = [cap - loads[b] for b in other_bins]
            assign = []
            ok = True

            for item_idx in target_items:
                s = items[item_idx]
                best_j = -1
                best_r = None
                for j, r in enumerate(res):
                    if r >= s and (best_r is None or r < best_r):
                        best_r = r
                        best_j = j
                if best_j == -1:
                    ok = False
                    break
                res[best_j] -= s
                assign.append(best_j)

            if ok:
                for k, item_idx in enumerate(target_items):
                    j = assign[k]
                    b = other_bins[j]
                    bins[b].append(item_idx)
                    loads[b] += items[item_idx]
                bins[target] = []
                loads[target] = 0
                improved = True
                break

            # Bounded backtracking for small target bins
            if len(target_items) <= 15:
                res = [cap - loads[b] for b in other_bins]
                assignment = [None] * len(target_items)
                nodes = [0]
                LIMIT = 5000

                def dfs(k):
                    if k == len(target_items):
                        return True
                    if nodes[0] > LIMIT:
                        return False
                    nodes[0] += 1

                    s = items[target_items[k]]
                    cand = []
                    for j, r in enumerate(res):
                        if r >= s:
                            cand.append((r, j))
                    if not cand:
                        return False

                    cand.sort()
                    last_r = None
                    for r, j in cand:
                        if r == last_r:
                            continue
                        last_r = r
                        res[j] -= s
                        assignment[k] = j
                        if dfs(k + 1):
                            return True
                        res[j] += s
                        assignment[k] = None
                    return False

                if dfs(0):
                    for k, item_idx in enumerate(target_items):
                        j = assignment[k]
                        b = other_bins[j]
                        bins[b].append(item_idx)
                        loads[b] += items[item_idx]
                    bins[target] = []
                    loads[target] = 0
                    improved = True
                    break

    result = [b for b in bins if b]

    # Safety fallback
    if sum(len(b) for b in result) != n:
        return ffd()

    return result