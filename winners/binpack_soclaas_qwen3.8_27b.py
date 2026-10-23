# soclaas_qwen3.8_27b | binpack | fitness 1.08533
def pack(payload):
    items = payload.get("items", [])
    capacity = payload.get("capacity", 0)
    n = len(items)
    if n == 0:
        return []
    if capacity < 0:
        capacity = 0
    # quick optimal if all fit
    # But sum may be expensive? O(n) okay.
    # If any size > capacity and total <= capacity? impossible for nonnegative; but if negative sizes? ignore.
    # Use max? If all fit in one bin: total <= capacity and all sizes <= capacity (if nonnegative, total<=capacity implies max<=capacity). If negative sizes, weird.
    total = sum(items)
    if total <= capacity:
        return [list(range(n))]
    ordered = [(items[i], i) for i in range(n)]
    ordered.sort(key=lambda x: x[0], reverse=True)
    def ffd():
       bins=[]
       for size, idx in ordered:
          if size > capacity:
             bins.append([0, [idx]])
             continue
          for b in bins:
             if b[0] >= size:
                b[0] -= size
                b[1].append(idx)
                break
          else:
             bins.append([capacity - size, [idx]])
       return [b[1] for b in bins]
    def bfd():
       bins=[]
       for size, idx in ordered:
          if size > capacity:
             bins.append([0, [idx]])
             continue
          best = None
          best_rem = None
          for b in bins:
             rem = b[0]
             if rem >= size:
                if best is None or rem < best_rem:
                   best = b
                   best_rem = rem
                   if rem == size:
                      break
          if best is None:
             bins.append([capacity - size, [idx]])
          else:
             best[0] -= size
             best[1].append(idx)
       return [b[1] for b in bins]
    # If n large, maybe only FFD? But let's run both if n <= 5000? Could just run both.
    # To avoid BFD too slow for very large, threshold:
    if n <= 5000:
       sol1=ffd(); sol2=bfd(); return sol1 if len(sol1) <= len(sol2) else sol2
    else:
       return ffd()