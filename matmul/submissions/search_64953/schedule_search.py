"""Targeted SSA traversal experiments on the 65,084 snake schedule.

All schedule edits are topological reorderings of the existing arithmetic DAG.
The source physical allocation is retained as the first allocation candidate.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import heapq
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(ROOT))


@dataclass
class Trace:
    ops: list[tuple[str, int, tuple[int, ...]]]
    inputs: list[int]
    outputs: list[int]
    homes: list[int]
    labels: list[tuple]
    users: list[list[int]]


def parse(text: str) -> Trace:
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    addresses = list(map(int, lines[0].split(",")))
    cur = {a: i for i, a in enumerate(addresses)}
    homes = addresses[:]
    labels = [("A", i // 16, i % 16) if i < 256 else
              ("B", (i-256)//16, (i-256)%16) for i in range(512)]
    users: list[list[int]] = [[] for _ in addresses]
    ops = []
    for oi, line in enumerate(lines[1:-1]):
        op, rest = line.split()
        aa = list(map(int, rest.split(",")))
        src = tuple(cur[a] for a in (aa[1:] if len(aa) == 3 or op == "copy" else aa))
        dst = len(homes)
        ll = [labels[v] for v in src]
        if op == "copy":
            label = ll[0]
        elif op == "mul":
            a, b = ll
            if a[0] == "B":
                a, b = b, a
            assert a[0] == "A" and b[0] == "B" and a[2] == b[1]
            label = ("C", a[1], b[2], 1 << a[2])
        elif op == "add":
            a, b = ll
            assert a[:3] == b[:3] and not a[3] & b[3], (oi, a, b)
            label = (*a[:3], a[3] | b[3])
        else:
            raise ValueError(op)
        for s in src:
            users[s].append(oi)
        homes.append(aa[0]); labels.append(label); users.append([])
        ops.append((op, dst, src)); cur[aa[0]] = dst
    outputs = [cur[a] for a in map(int, lines[-1].split(","))]
    return Trace(ops, list(range(512)), outputs, homes, labels, users)


def pass_key(label: tuple) -> tuple[int, int, int]:
    assert label[0] == "C"
    return label[1]//4, label[2]//8, label[3].bit_length()-1


def reorder(t: Trace, changes: dict[tuple[int, int, int], tuple[bool, bool]]) -> list[int]:
    """Change column and row direction for selected contraction passes.

    Stable topological sorting repairs dependencies of input staging and
    persistent captures. Copies directly feeding arithmetic move to its first
    use; capture copies move with the short-lived copy source where possible.
    """
    priority = [float(i) for i in range(len(t.ops))]
    members: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for oi, (op, d, ss) in enumerate(t.ops):
        if op in ("mul", "add"):
            pk = pass_key(t.labels[d])
            if pk in changes:
                members[pk].append(oi)
    touched = set()
    for pk, mm in members.items():
        colrev, rowrev = changes[pk]
        def rank(oi: int):
            op, dst, _ = t.ops[oi]
            _, i, j, _ = t.labels[dst]
            rowrank = rowrev.index(i%4) if isinstance(rowrev, tuple) else (-i if rowrev else i)
            return (-j if colrev else j, rowrank, op == "add", oi)
        mm = sorted(mm, key=rank)
        lo, hi = min(mm), max(mm)
        for rank_i, oi in enumerate(mm):
            priority[oi] = lo + (hi-lo) * rank_i / max(1, len(mm)-1)
            touched.add(oi)
    for oi, (op, dst, ss) in enumerate(t.ops):
        if op != "copy":
            continue
        arithmetic_users = [u for u in t.users[dst] if t.ops[u][0] != "copy"]
        if arithmetic_users and any(u in touched for u in arithmetic_users):
            priority[oi] = min(priority[u] for u in arithmetic_users) - .2
            touched.add(oi)
        elif not arithmetic_users and ss[0] >= 512 and ss[0]-512 in touched:
            # A capture's source is already available cheaply here.
            priority[oi] = priority[ss[0]-512] + .01
            touched.add(oi)
    pending = [sum(s >= 512 for s in ss) for _, _, ss in t.ops]
    ready = [(priority[i], i) for i, n in enumerate(pending) if n == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        _, oi = heapq.heappop(ready)
        result.append(oi)
        for user in t.users[t.ops[oi][1]]:
            pending[user] -= 1
            if pending[user] == 0:
                heapq.heappush(ready, (priority[user], user))
    assert len(result) == len(t.ops)
    return result


def lifetimes(t: Trace, order: list[int]):
    defs = [0]*len(t.homes); ends = [0]*len(t.homes); reads = [0]*len(t.homes)
    for tm, oi in enumerate(order, 1):
        _, d, ss = t.ops[oi]
        defs[d] = ends[d] = tm
        for s in ss:
            assert s < 512 or defs[s] > 0
            ends[s] = tm; reads[s] += 1
    for s in t.outputs:
        ends[s] = len(order)+1; reads[s] += 1
    return defs, ends, reads


def emit(t: Trace, order: list[int], homes: list[int]) -> str:
    lines = [','.join(str(homes[v]) for v in t.inputs)]
    for oi in order:
        op, d, ss = t.ops[oi]
        lines.append(f"{op} " + ','.join(str(homes[v]) for v in (d, *ss)))
    lines.append(','.join(str(homes[v]) for v in t.outputs))
    return '\n'.join(lines)+'\n'


def repair(t: Trace, order: list[int], mode: str = "retain"):
    """Feasible incumbent-preserving coloring, trying original home first."""
    defs, ends, reads = lifetimes(t, order)
    homes = t.homes[:]
    occupied: dict[int, tuple[int, int]] = {}
    live = sorted(range(len(homes)), key=lambda v: (defs[v], -reads[v]))
    for v in live:
        preferred = homes[v]
        if preferred not in occupied or occupied[preferred][0] <= defs[v]:
            home = preferred
        else:
            # Lowest free cell, preserving original allocations when possible.
            home = 1
            while home in occupied and occupied[home][0] > defs[v]:
                home += 1
        homes[v] = home
        occupied[home] = (ends[v], v)
    score = sum(reads[v]*(math.isqrt(a-1)+1) for v,a in enumerate(homes))
    return homes, score
