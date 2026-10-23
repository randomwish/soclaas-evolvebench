# soclaas_coding | binpack | fitness 1.08533
def pack(payload):
    items = payload.get("items", [])
    capacity = int(payload.get("capacity", 0))
    n = len(items)
    if n == 0:
        return []

    # Separate zero-size items; they do not affect capacity.
    zero = [i for i, s in enumerate(items) if s <= 0]
    pos = [i for i, s in enumerate(items) if s > 0]
    if not pos:
        return [zero] if zero else []

    if capacity <= 0:
        bins = [[i] for i in pos]
        if zero:
            if bins:
                bins[0].extend(zero)
            else:
                bins.append(zero)
        return bins

    pos.sort(key=lambda i: (-items[i], i))
    bins = []
    rem = []
    # Use best-fit when the problem is small enough; otherwise first-fit for speed.
    total = sum(items[i] for i in pos)
    lb = (total + capacity - 1) // capacity
    if len(pos) * max(1, lb) <= 4_000_000:
        from bisect import bisect_left, insort
        rem_pairs = []
        for i in pos:
            s = items[i]
            if s > capacity:
                b = len(bins)
                bins.append([i])
                insort(rem_pairs, (0, b))
                continue
            p = bisect_left(rem_pairs, (s, -1))
            if p == len(rem_pairs):
                b = len(bins)
                bins.append([i])
                insort(rem_pairs, (capacity - s, b))
            else:
                r, b = rem_pairs.pop(p)
                new_r = r - s
                bins[b].append(i)
                insort(rem_pairs, (new_r, b))
    else:
        for i in pos:
            s = items[i]
            if s > capacity:
                bins.append([i])
                rem.append(0)
                continue
            for b, r in enumerate(rem):
                if r >= s:
                    bins[b].append(i)
                    rem[b] = r - s
                    break
            else:
                bins.append([i])
                rem.append(capacity - s)

    if zero:
        if bins:
            bins[0].extend(zero)
        else:
            bins.append(zero[:])
    return bins