# fitness 1.0853322045933025
def pack(payload):
    items = payload["items"]
    capacity = payload["capacity"]
    n = len(items)
    
    # Pair each item with its original index and sort by descending size
    indexed_items = sorted(enumerate(items), key=lambda x: -x[1])
    
    bins = []  # list of lists of indices
    
    for idx, size in indexed_items:
        placed = False
        for bin_ in bins:
            if sum(items[i] for i in bin_) + size <= capacity:
                bin_.append(idx)
                placed = True
                break
        if not placed:
            bins.append([idx])
    
    return bins