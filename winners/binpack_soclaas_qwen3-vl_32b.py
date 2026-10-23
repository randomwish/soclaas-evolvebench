# soclaas_qwen3-vl_32b | binpack | fitness 1.08533
def pack(payload):
    items = payload["items"]
    capacity = payload["capacity"]
    n = len(items)
    
    if n == 0:
        return []
    
    # Group items by size, preserving original indices
    size_groups = {}
    for i, size in enumerate(items):
        if size not in size_groups:
            size_groups[size] = []
        size_groups[size].append(i)
    
    # Sort groups by size descending
    sorted_groups = sorted(size_groups.items(), key=lambda x: x[0], reverse=True)
    
    # Threshold for "large" items
    small_threshold = capacity // 3
    large_groups = []
    small_groups = []
    
    for size, item_indices in sorted_groups:
        if size > small_threshold:
            large_groups.append((size, item_indices))
        else:
            small_groups.append((size, item_indices))
    
    # Initialize bins
    bins = []
    bin_sums = []  # Track sum of sizes in each bin for efficiency
    
    # Pack large items: best-fit with preference for bins leaving 0-2*small_threshold space
    for size, item_indices in large_groups:
        for item_idx in item_indices:
            best_bin = -1
            best_remaining = float('inf')
            
            for i, bin in enumerate(bins):
                if bin_sums[i] + size <= capacity:
                    remaining = capacity - (bin_sums[i] + size)
                    # Prefer bins that leave space suitable for small items
                    if remaining <= 2 * small_threshold and remaining < best_remaining:
                        best_remaining = remaining
                        best_bin = i
            
            if best_bin != -1:
                bins[best_bin].append(item_idx)
                bin_sums[best_bin] += size
            else:
                bins.append([item_idx])
                bin_sums.append(size)
    
    # Pack small items: best-fit (not FFD) to reduce fragmentation
    for size, item_indices in small_groups:
        for item_idx in item_indices:
            best_bin = -1
            best_remaining = float('inf')
            
            for i, bin in enumerate(bins):
                if bin_sums[i] + size <= capacity:
                    remaining = capacity - (bin_sums[i] + size)
                    if remaining < best_remaining:
                        best_remaining = remaining
                        best_bin = i
            
            if best_bin != -1:
                bins[best_bin].append(item_idx)
                bin_sums[best_bin] += size
            else:
                bins.append([item_idx])
                bin_sums.append(size)
    
    # Post-optimization: try to move small items to merge bins
    # Only consider small items (<= small_threshold) for moving
    small_items = []
    for i, bin in enumerate(bins):
        for item_idx in bin:
            if items[item_idx] <= small_threshold:
                small_items.append((i, item_idx))
    
    # Try to move each small item to another bin
    for i, item_idx in small_items:
        item_size = items[item_idx]
        for j in range(len(bins)):
            if i != j and bin_sums[j] + item_size <= capacity:
                # Move item from bin i to bin j
                bins[j].append(item_idx)
                bin_sums[j] += item_size
                bins[i].remove(item_idx)
                bin_sums[i] -= item_size
                
                # If bin i becomes empty, remove it
                if len(bins[i]) == 0:
                    bins.pop(i)
                    bin_sums.pop(i)
                    # Adjust indices for remaining items (since we removed a bin)
                    # We don't need to reindex the small_items list because we're
                    # processing in order and we only care about the current bin
                    # being non-empty for future moves
                    break  # break inner loop, move to next small item
                break  # break inner loop, move to next small item
    
    return bins