# soclaas_x-test-1 | binpack | fitness 1.08533
import time
import random
from bisect import bisect_right


def pack(payload):
    items = list(payload["items"])
    capacity = payload["capacity"]
    n = len(items)
    if n == 0:
        return []

    t0 = time.time()
    deadline = t0 + 0.90                      # per-instance budget (~14s / 16 instances)

    total = sum(items)
    if total <= capacity:                     # trivial: one bin
        return [list(range(n))]

    lb = -(-total // capacity) if capacity > 0 else n   # lower bound on #bins

    rng = random.Random(0xC0FFEE)

    # ---------- Best-Fit Decreasing; open bins kept sorted by load ----------
    def bfd(order):
        loads, bins = [], []                  # parallel lists, loads ascending
        for i in order:
            s = items[i]
            pos = bisect_right(loads, capacity - s) - 1
            if pos >= 0:                      # tightest bin that still fits
                L = loads[pos] + s
                b = bins[pos]
                b.append(i)
                del loads[pos], bins[pos]
                k = bisect_right(loads, L)
                loads.insert(k, L)
                bins.insert(k, b)
            else:                             # open a new bin
                k = bisect_right(loads, s)
                loads.insert(k, s)
                bins.insert(k, [i])
        return bins

    # ---------- First-Fit Decreasing (extra candidate, small n only) ----------
    def ffd(order):
        bins, loads = [], []
        for i in order:
            s = items[i]
            for j in range(len(bins)):
                if loads[j] + s <= capacity:
                    loads[j] += s
                    bins[j].append(i)
                    break
            else:
                bins.append([i])
                loads.append(s)
        return bins

    # ---------- Optimal pairing when no bin can hold 3+ items ----------
    def pairing():
        if n and 3 * min(items) > capacity:
            dec = sorted(range(n), key=lambda i: -items[i])
            lo, hi = 0, n - 1
            bins = []
            while lo <= hi:
                if lo < hi and items[dec[lo]] + items[dec[hi]] <= capacity:
                    bins.append([dec[lo], dec[hi]])
                    lo += 1
                    hi -= 1
                else:
                    bins.append([dec[lo]])
                    lo += 1
            return bins
        return None

    # ---------- Improvement: dissolve whole bins into the others ----------
    def eliminate(binlists, dl):
        pairs = [[sum(items[i] for i in b), list(b)] for b in binlists if b]
        pairs.sort(key=lambda p: p[0])
        while time.time() < dl:
            m = len(pairs)
            progressed = False
            for v in range(min(m, 100)):      # try the 100 emptiest bins
                if time.time() >= dl:
                    return [p[1] for p in pairs]
                others = pairs[:v] + pairs[v + 1:]      # still load-sorted
                work = [p[0] for p in others]
                vits = pairs[v][1]
                if len(vits) > 1:
                    vits = sorted(vits, key=lambda i: -items[i])
                assign = []
                ok = True
                for i in vits:
                    s = items[i]
                    pos = bisect_right(work, capacity - s) - 1
                    if pos < 0:
                        ok = False
                        break
                    L = work[pos] + s
                    assign.append((others[pos], i))
                    work.pop(pos)
                    k2 = bisect_right(work, L)
                    work.insert(k2, L)
                if ok:                          # victim dissolved: commit
                    for b, i in assign:
                        b[0] += items[i]
                        b[1].append(i)
                    pairs = others
                    pairs.sort(key=lambda p: p[0])
                    progressed = True
                    break
            if not progressed:
                break
        return [p[1] for p in pairs]

    best = None
    best_count = n + 1

    def consider(binlists):
        nonlocal best, best_count
        if binlists and len(binlists) < best_count:
            best_count = len(binlists)
            best = [list(b) for b in binlists]

    order = sorted(range(n), key=lambda i: (-items[i], i))

    try:
        p = pairing()
        if p is not None:
            consider(p)
            if best_count <= lb:
                return best

        raw = bfd(order)
        consider(raw)
        if time.time() < deadline:
            consider(eliminate(raw, min(deadline, time.time() + 0.4)))
        if best_count <= lb:
            return best

        if n <= 600 and time.time() < deadline:
            raw = ffd(order)
            consider(raw)
            if time.time() < deadline:
                consider(eliminate(raw, min(deadline, time.time() + 0.4)))
            if best_count <= lb:
                return best

        # ----- randomized multi-start around the descending order -----
        avg = total / n
        spread = (max(items) - min(items)) or 1
        runs = 0
        last_imp = 0
        while runs < 3000 and time.time() < deadline:
            runs += 1
            t1 = time.time()
            regime = runs % 3
            if regime == 1:                   # mild noise
                w = 0.03 * avg + 0.5
                noise = [rng.uniform(-w, w) for _ in range(n)]
                o2 = sorted(range(n), key=lambda i: (-(items[i] + noise[i]), i))
            elif regime == 2:                 # local reshuffle
                o2 = list(order)
                for _ in range(max(1, n // 8)):
                    j = rng.randrange(n - 1)
                    o2[j], o2[j + 1] = o2[j + 1], o2[j]
            else:                             # strong noise
                w = 0.2 * avg + 1.5
                noise = [rng.uniform(-w, w) for _ in range(n)]
                o2 = sorted(range(n), key=lambda i: (-(items[i] + noise[i]), i))
            raw = bfd(o2)
            before = best_count
            if len(raw) <= best_count and n <= 900 and time.time() < deadline:
                consider(eliminate(raw, deadline))
            else:
                consider(raw)
            if best_count < before:
                last_imp = runs
            if best_count <= lb or runs - last_imp >= 400:
                break
            if time.time() - t1 > max(0.0, deadline - time.time()):
                break

        # final polish on the incumbent
        if best is not None and time.time() < deadline:
            consider(eliminate(best, deadline))
    except Exception:
        best = ffd(order)

    return best if best is not None else [[i] for i in range(n)]