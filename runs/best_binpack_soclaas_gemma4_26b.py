# fitness 1.0853322045933025
def pack(payload) -> list[list[int]]:
    items = payload["items"]
    capacity = payload["capacity"]

    # Track items with their original indices to satisfy return requirements
    # Format: (size, original_index)
    indexed_items = []
    for i, size in enumerate(items):
        indexed_items.append((size, i))

    # Sort items in descending order (The "Decreasing" part of FFD)
    # Larger items are harder to fit later, so we place them first.
    indexed_items.sort(key=lambda x: x[0], reverse=True)

    bins = []      # List of lists containing item indices
    bin_sums = []  # Tracks the current total size in each bin

    for size, original_idx in indexed_items:
        placed = False
        
        # Attempt to find the first bin that can fit the current item
        for i in range(len(bins)):
            if bin_sums[i] + size <= capacity:
                bins[i].append(original_idx)
                bin_sums[i] += size
                placed = True
                break
        
        # If no existing bin can fit the item, create a new bin
        if not placed:
            bins.append([original_idx])
            bin_sums.append(size)

    return bins