# fitness 1.0853322045933025
def pack(payload):
    items = payload["items"]
    capacity = payload["capacity"]
    n = len(items)
    
    # Create list of (size, original_index) pairs
    indexed_items = [(items[i], i) for i in range(n)]
    
    # Sort by size in descending order
    indexed_items.sort(key=lambda x: x[0], reverse=True)
    
    # Initialize bins (each bin is a list of item indices)
    bins = []
    
    for size, orig_idx in indexed_items:
        # Try to place item in existing bin
        placed = False
        for bin in bins:
            if sum(items[i] for i in bin) + size <= capacity:
                bin.append(orig_idx)
                placed = True
                break
        
        # If not placed, create a new bin
        if not placed:
            bins.append([orig_idx])
    
    return bins