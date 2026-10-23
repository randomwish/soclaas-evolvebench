# fitness 1.0853322045933025
def pack(payload) -> list[list[int]]:
    """
    Pack items into bins using a Best-Fit Decreasing (BFD) heuristic.
    
    Args:
        payload: A dictionary with keys 'items' (list of item sizes) and 'capacity' (int).
        
    Returns:
        A list of bins, where each bin is a list of original item indices.
    """
    items = payload['items']
    capacity = payload['capacity']
    
    n = len(items)
    if n == 0:
        return []
    
    # Create list of (size, original_index)
    indexed_items = [(size, i) for i, size in enumerate(items)]
    
    # Sort items by size in descending order (Decreasing)
    # If sizes are equal, the order doesn't strictly matter for BFD,
    # but stable sort preserves original order for consistency.
    indexed_items.sort(key=lambda x: x[0], reverse=True)
    
    # Bins will store tuples of (remaining_capacity, list_of_indices)
    # Using remaining_capacity for easy Best-Fit comparison
    bins = []
    
    for size, original_index in indexed_items:
        # If item size exceeds capacity, it can't be packed (should not happen in valid instances)
        if size > capacity:
            # In some formulations, this might be an error or handled separately.
            # Assuming valid input where size <= capacity.
            continue
            
        # Best Fit: Find the bin with the smallest remaining space that can still hold the item
        best_bin_idx = -1
        best_remaining = float('inf')
        
        for i, (rem_cap, _) in enumerate(bins):
            if rem_cap >= size:
                if rem_cap - size < best_remaining:
                    best_remaining = rem_cap - size
                    best_bin_idx = i
        
        if best_bin_idx != -1:
            # Place item in the best fitting existing bin
            bins[best_bin_idx] = (best_remaining, bins[best_bin_idx][1] + [original_index])
        else:
            # No existing bin fits, open a new bin
            remaining_after = capacity - size
            bins.append((remaining_after, [original_index]))
    
    # Extract just the list of indices from each bin tuple
    result_bins = [bin_indices for _, bin_indices in bins]
    
    return result_bins