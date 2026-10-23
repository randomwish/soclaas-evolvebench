# soclaas_qwen3.6_35b | binpack | fitness 1.08533
def pack(payload) -> list[list[int]]:
    items = payload['items']
    capacity = payload['capacity']
    n = len(items)
    
    if n == 0:
        return []
    
    # Create list of (size, original_index)
    indexed_items = [(size, i) for i, size in enumerate(items)]
    
    def run_bfd(items_sorted):
        bins = []  # List of (remaining_capacity, list_of_indices)
        for size, original_index in items_sorted:
            best_bin_idx = -1
            best_remaining = float('inf')
            
            for i, (rem_cap, _) in enumerate(bins):
                if rem_cap >= size:
                    rem_after = rem_cap - size
                    if rem_after < best_remaining:
                        best_remaining = rem_after
                        best_bin_idx = i
            
            if best_bin_idx != -1:
                bins[best_bin_idx] = (best_remaining, bins[best_bin_idx][1] + [original_index])
            else:
                bins.append((capacity - size, [original_index]))
        return [bin_indices for _, bin_indices in bins]

    def run_ffd(items_sorted):
        bins = []  # List of (remaining_capacity, list_of_indices)
        for size, original_index in items_sorted:
            best_bin_idx = -1
            for i, (rem_cap, _) in enumerate(bins):
                if rem_cap >= size:
                    best_bin_idx = i
                    break
            
            if best_bin_idx != -1:
                bins[best_bin_idx] = (bins[best_bin_idx][0] - size, bins[best_bin_idx][1] + [original_index])
            else:
                bins.append((capacity - size, [original_index]))
        return [bin_indices for _, bin_indices in bins]

    # Sort items descending by size
    indexed_items.sort(key=lambda x: x[0], reverse=True)
    
    # Run BFD
    bins_bfd = run_bfd(indexed_items)
    
    # Run FFD
    bins_ffd = run_ffd(indexed_items)
    
    # Pick the better one
    if len(bins_bfd) <= len(bins_ffd):
        return bins_bfd
    else:
        return bins_ffd