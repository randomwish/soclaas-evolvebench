# soclaas_llama3.1_8b | binpack | fitness 1.11888
def pack(payload):
    capacity = payload["capacity"]
    items = list(range(len(payload["items"])))
    sorted_items = sorted(items, key=lambda i: len([j for j in items if payload["items"][i] > payload["items"][j]]), reverse=True)

    # Initialize bins and bin indices
    bins = [[0] * capacity]
    bin_indices = [0] * len(items)
    bin_sizes = [capacity] * len(bins)  # track remaining capacity in each bin

    for item_idx in sorted_items:
        best_bin_idx = -1
        min_remaining_capacity = float('inf')
        
        for i, (bin_size, items_in_bin) in enumerate(zip(bin_sizes, bins)):
            if sum(payload["items"][j] for j in items_in_bin) + payload["items"][item_idx] <= capacity:
                remaining_capacity = bin_size - sum(payload["items"][j] for j in items_in_bin)
                if remaining_capacity < min_remaining_capacity:
                    min_remaining_capacity = remaining_capacity
                    best_bin_idx = i
        
        # If no bin has enough capacity, create a new one
        if best_bin_idx == -1:
            bins.append([item_idx])
            bin_indices[item_idx] = len(bins) - 1
            bin_sizes.append(capacity)
        else:
            bins[best_bin_idx].append(item_idx)
            bin_indices[item_idx] = best_bin_idx

    return [[i for i, j in enumerate(bin_indices) if j == bin_index] for bin_index in range(len(bins))]