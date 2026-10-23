# fitness 1.1188803274625
def pack(payload):
    capacity = payload["capacity"]
    items = list(range(len(payload["items"])))
    sorted_items = sorted(items, key=lambda i: len([j for j in items if payload["items"][i] > payload["items"][j]]), reverse=True)
    bins = [[0] * capacity]
    bin_indices = [0] * len(items)

    for item_idx in sorted_items:
        best_bin_idx = 0
        while best_bin_idx < len(bins):
            if sum(payload["items"][i] for i in bins[best_bin_idx]) + payload["items"][item_idx] <= capacity:
                bins[best_bin_idx].append(item_idx)
                bin_indices[item_idx] = best_bin_idx
                break
            else:
                best_bin_idx += 1
        if best_bin_idx == len(bins):
            bins.append([item_idx])
            bin_indices[item_idx] = len(bins) - 1

    return [[i for i, j in enumerate(bin_indices) if j == bin_index] for bin_index in range(len(bins))]