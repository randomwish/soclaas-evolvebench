# fitness 0.5631999999999999
# Poor-man's Belady: predict each cached key's next access time from its
# recent inter-request gaps; evict the key predicted to be needed furthest
# in the future. Keys seen only once are predicted to never return (evicted
# first -> scan resistance). Keys silent longer than their predicted gap are
# "overdue" and become LRU-like candidates (handles drift/non-stationarity).

from collections import deque

_INF = float("inf")
_MAXGAPS = 3          # gaps remembered per key
_seen = {}            # key -> deque of last request times (maxlen _MAXGAPS+1)
_t_proc = None        # request index up to which we've processed `recent`


def _reset():
    global _t_proc
    _seen.clear()
    _t_proc = None


def _process_recent(meta):
    global _t_proc
    t = meta["time"]
    if _t_proc is not None and t < _t_proc:
        _reset()  # new trace detected
    recent = meta["recent"]
    if _t_proc is None:
        n = len(recent)
    else:
        n = t - _t_proc
        if n <= 0:
            return
        if n > len(recent):
            n = len(recent)
    start = t - n + 1
    seen = _seen
    for i in range(n):
        k = recent[len(recent) - n + i]
        ti = start + i
        d = seen.get(k)
        if d is None:
            seen[k] = deque([ti], maxlen=_MAXGAPS + 1)
        else:
            d.append(ti)
    _t_proc = t


def evict(cache, meta):
    _process_recent(meta)
    t = meta["time"]
    cl = meta["cache_last"]
    best_i = 0
    best_pred = None
    best_neglast = None
    for i, k in enumerate(cache):
        d = _seen.get(k)
        last = cl.get(k, t)
        if d is None or len(d) < 2:
            pred = _INF
        else:
            est = _INF
            prev = d[-1]
            for j in range(len(d) - 1, 0, -1):
                g = d[j] - d[j - 1]
                if g < est:
                    est = g
            silence = t - last
            if silence > est:
                est = silence
            pred = last + est
        neglast = -last
        if best_pred is None or pred > best_pred or (pred == best_pred and neglast > best_neglast):
            best_pred = pred
            best_neglast = neglast
            best_i = i
    return best_i