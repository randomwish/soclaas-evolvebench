# soclaas_qwen3-coder-next | binpack | fitness 1.08533
import random

def pack(payload):
    items = payload["items"]
    capacity = payload["capacity"]
    n = len(items)
    total_size = sum(items)
    lower_bound = (total_size + capacity - 1) // capacity  # ceil(total/capacity)

    # Helper: run FFD with custom tie-breaking on equal-sized items
    def ffd_with_tie_break(indexed_items, key):
        bins = []
        # Sort by descending size, with custom tie-breaking via `key`
        sorted_items = sorted(indexed_items, key=key)
        for idx, size in sorted_items:
            placed = False
            for bin_ in bins:
                if sum(items[i] for i in bin_) + size <= capacity:
                    bin_.append(idx)
                    placed = True
                    break
            if not placed:
                bins.append([idx])
        return bins

    # Base indexed items: (original_index, size)
    indexed = list(enumerate(items))

    # Variant 1: standard — sort by (-size, index)
    sol1 = ffd_with_tie_break(indexed, key=lambda x: (-x[1], x[0]))

    # Variant 2: tie-break by descending index (reverse within equal-size groups)
    sol2 = ffd_with_tie_break(indexed, key=lambda x: (-x[1], -x[0]))

    # Variant 3: random shuffle within equal-size groups (deterministic seed)
    random.seed(42)
    # Group by size, shuffle indices per group, then sort by -size
    groups = {}
    for idx, size in indexed:
        groups.setdefault(size, []).append(idx)
    shuffled_indexed = []
    for size in groups:
        indices = groups[size][:]
        random.shuffle(indices)
        for idx in indices:
            shuffled_indexed.append((idx, size))
    sol3 = ffd_with_tie_break(shuffled_indexed, key=lambda x: (-x[1], 0))  # key ignored; already sorted

    # Choose best (fewest bins); tie-break by lexicographically smallest bin assignment for determinism (optional but safe)
    candidates = [sol1, sol2, sol3]
    best = min(candidates, key=lambda bins: (len(bins), bins))
    return best