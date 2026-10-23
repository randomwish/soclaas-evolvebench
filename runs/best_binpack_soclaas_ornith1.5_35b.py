# fitness 1.0853322045933025
def pack(payload):
    """Bin packing via Best-Fit-Decreasing (FFD-style baseline).

    Items are placed largest-first into the open bin with the tightest
    remaining capacity that still fits them, minimizing wasted space and
    driving the bins-used count toward the ceil(total/capacity) lower bound.
    """
    items = payload["items"]
    capacity = payload["capacity"]
    n = len(items)
    if n == 0:
        return []

    # Largest items first; break ties arbitrarily (stable).
    order = sorted(range(n), key=lambda i: items[i], reverse=True)

    remaining = []   # remaining capacity of each currently open bin
    contents = []    # list of item indices stored in each open bin

    for i in order:
        s = items[i]
        # Best-Fit: pick the bin with the least leftover space that still fits.
        best_bin = -1
        best_rem = capacity + 1
        for b in range(len(remaining)):
            r = remaining[b]
            if s <= r and r < best_rem:
                best_rem = r
                best_bin = b

        if best_bin == -1:
            # No existing bin fits -> open a fresh bin.
            remaining.append(capacity - s)
            contents.append([i])
        else:
            remaining[best_bin] -= s
            contents[best_bin].append(i)

    return contents