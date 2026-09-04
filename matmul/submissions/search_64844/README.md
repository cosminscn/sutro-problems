# Reproduce the 64,844 matmul program

The literal generator uses row widths **[5,5,6]**, column widths **[6,10]**,
macro-tile contraction chunks **[1,1,2,2,2,2]**, and persistent B captures for
columns **j >= 6**. It rebuilds the submitted full 16×16 program without loading
an earlier candidate as a seed.

From the repository root, with Python 3.12:

```sh
python -m pip install -r matmul/submissions/search_64844/requirements.txt
python matmul/submissions/search_64844/reproduce.py
```

Optional outputs:

```sh
python matmul/submissions/search_64844/reproduce.py \
  --output replayed_64844.ir --manifest replayed_64844.json
```

The recorded fresh-process run used Python **3.12.14**, NumPy **2.3.5**, and
OR-Tools **9.15.6755**, completing in **7.05 seconds**. Versions are pinned because
equal-cost flow choices can affect bytes. The replay imports only unchanged
repository-local helpers: `search_64953/core.py`, `search_64953/pair_alloc.py`,
and `search_value_coloring.allocate_dp_chains`. Exact helper hashes appear in
`validation.json`. No machine-specific native library, compiler, home directory,
or external artifact is required.

## Generator and exact lineage

Visit the 6-column panel first, with row groups 5,5,6, then the 10-column panel
with the same row groups. The first two tiles use one-term contraction chunks;
the other four use two terms. Reverse column traversal after each chunk.
Stage A at first use within a chunk and reuse it across columns. Stage B within
each column and reuse it across rows. Existing C is accumulated immediately
through the products of each chunk. Capture the first staged B value for each
of the 160 entries in columns 6–15; later row groups reload that capture.

The generator comes from the mixed-chunk geometry experiment. Its parent used
the same rows and chunk choices with columns [7,9] and scored 64,915. Changing
the columns to [6,10] and aligning the capture threshold to 6, with the same DP
and allocation configuration, produced this witness. The portable source
contains these choices literally rather than replaying the search campaign.

| Checkpoint | Score | SHA-256 |
|---|---:|---|
| Semantic generator + 160 B captures | 1,173,542 | `3ffcb44e9d05d466e0198f6a9c29e2e9f9ed8338b752bb5049981ac85c81cc48` |
| Weighted lifetime-chain initialization | 64,955 | `4569972f5b02cd7f657b096d9ebbe95475f97e46185d9a414b0ba352a29925fd` |
| Pair allocation: 2 rounds, seed 0, ties disabled | 64,943 | `d49883c8f07544e814b837d2f649037510d956caec78c9dee3564031e90fb362` |
| Pair allocation: 5 rounds, seed 11, ties enabled | **64,844** | `2f09749a34daa66227b23320de8a19d67ff443e0248a604b175fbb66d8d9f786` |

The allocated initial IR is reparsed **before either pair pass**, matching the
discovered run's canonical value IDs and tie ordering. There is no reparse
between the two passes. Allocation uses fixed round counts with no wall-time
cutoff; its usual no-improvement early exit remains enabled when ties are off.
Every checkpoint passes the unchanged official scorer and independent exact
noncommutative proof. The final artifact is read only for byte comparison.

## Scope and attribution

This is a verified witness, not proof of optimal scheduling, address placement,
or matrix multiplication. Older fixed-trace lower bounds do not apply. The
local pair-tier min-cost-flow problems are exact, while their complete sequence
is a heuristic. Research used a reference-compatible native graph-preparation
engine, but this replay uses Python preparation with the same native OR-Tools
solver and reference RNG. Language throughput does not change the scored cost.

The generator and geometry choices were developed in cosminscn's campaign with
Codex. Repository value-coloring, persistent capture, and column-panel staging
work underpin the implementation. The reused `search_64953` helpers and
`best_66178._prove` retain their attribution. The earlier
[64,863 report](../best_64863.md) records the preceding capture experiments and
the connection to Juraj Selep's [PR #50](https://github.com/cybertronai/sutro-problems/pull/50).
