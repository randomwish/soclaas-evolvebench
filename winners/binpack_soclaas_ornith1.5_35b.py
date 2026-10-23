# soclaas_ornith1.5_35b | binpack | fitness 1.08533
import random

def pack(payload):
    items = payload["items"]
    capacity = payload["capacity"]
    n = len(items)
    if n == 0:
        return []
    if n == 1:
        return [[0]]
    
    # Precompute for speed
    order = sorted(range(n), key=lambda i: items[i], reverse=True)
    
    def bfd(o):
        bins = []
        room = []
        for i in o:
            s = items[i]
            best_b = -1
            best_r = capacity + 1
            for b in range(len(bins)):
                r = room[b]
                if s <= r and r < best_r:
                    best_r = r
                    best_b = b
            if best_b == -1:
                bins.append([i])
                room.append(capacity - s)
            else:
                bins[best_b].append(i)
                room[best_b] -= s
        return bins, room
    
    def reduce_bins(bins, room):
        improved = True
        while improved:
            improved = False
            for i in range(len(bins)):
                if len(bins[i]) <= 1:
                    continue
                # redistribute bin i into others
                new_bins = [list(bins[j]) for j in range(len(bins)) if j != i]
                new_room = [room[j] for j in range(len(bins)) if j != i]
                placed = []
                ok = True
                for k in sorted(bins[i], key=lambda x: items[x], reverse=True):
                    s = items[k]
                    bi = -1
                    br = capacity + 1
                    for j in range(len(new_bins)):
                        if s <= new_room[j] and new_room[j] < br:
                            br = new_room[j]
                            bi = j
                    if bi == -1:
                        ok = False
                        break
                    new_bins[bi].append(k)
                    new_room[bi] -= s
                    placed.append((k, bi))
                if ok:
                    bins.clear()
                    bins.extend(new_bins)
                    room.clear()
                    room.extend(new_room)
                    improved = True
                    break
        return bins, room
    
    def swap_improve(bins, room):
        # try to move/swap items to reduce waste
        improved = True
        while improved:
            improved = False
            for a in range(len(bins)):
                for b in range(a+1, len(bins)):
                    # try moving each item of a into b
                    for idx in range(len(bins[a]) - 1, -1, -1):
                        k = bins[a][idx]
                        s = items[k]
                        if s <= room[b]:
                            bins[a].pop(idx)
                            room[a] += s
                            bins[b].append(k)
                            room[b] -= s
                            improved = True
                            break
                    if improved:
                        break
        return bins, room
    
    import random
    random.seed(12345)
    best = None
    best_count = None
    # try BFD + local search, plus restarts
    for r in range(13):
        if r == 0:
            cand = list(order)
        else:
            cand = list(order)
            random.shuffle(cand)
        bins, room = bfd(cand)
        bins, room = reduce_bins(bins, room)
        bins, room = swap_improve(bins, room)
        c = len(bins)
        if best is None or c < best_count:
            best = bins
            best_count = c
    return best