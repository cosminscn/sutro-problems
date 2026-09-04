# Reproduce the 64,829 matmul program

The literal generator uses row widths **[5,5,6]**, column widths **[6,10]**,
macro-tile contraction chunks **[1,1,1,2,2,2]**, and persistent B captures for
columns **j >= 6**. It rebuilds the submitted full 16×16 program without loading
an earlier candidate as a seed.

From the repository root, with Python 3.12:

```sh
python -m pip install -r matmul/submissions/search_64829/requirements.txt
python matmul/submissions/search_64829/reproduce.py
```

Optional outputs:

```sh
python matmul/submissions/search_64829/reproduce.py \
  --output replayed_64829.ir --manifest replayed_64829.json
```

The recorded fresh-process run used Python **3.12.14**, NumPy **2.3.5**, and
OR-Tools **9.15.6755**, completing in **7.17 seconds**. Versions are pinned because
equal-cost flow choices can affect bytes. The replay imports only unchanged
repository-local helpers: `search_64953/core.py`, `search_64953/pair_alloc.py`,
and `search_value_coloring.allocate_dp_chains`. Exact helper hashes appear in
`validation.json`. No machine-specific native library, compiler, home directory,
or external artifact is required.

## Generator and exact lineage

Visit the 6-column panel first, with row groups 5,5,6, then the 10-column panel
with the same row groups. The first three tiles use one-term contraction chunks;
the other three use two terms. Reverse column traversal after each chunk.
Stage A at first use within a chunk and reuse it across columns. Stage B within
each column and reuse it across rows. Existing C is accumulated immediately
through the products of each chunk. Capture the first staged B value for each
of the 160 entries in columns 6–15; later row groups reload that capture.

The generator comes from the mixed-chunk geometry experiment. Its immediate
parent, [64,844](../best_64844.md), uses the same rows, columns, and capture
threshold, with chunks [1,1,2,2,2,2]. Changing only the third macro tile to
one-term chunks produces [1,1,1,2,2,2] (mask 56), which scores 64,829 after the
same DP and allocation configuration. The portable source contains these
choices literally rather than replaying the search campaign.

| Checkpoint | Score | SHA-256 |
|---|---:|---|
| Semantic generator + 160 B captures | 1,173,642 | `093cd429879795f762f23ddd5d323952ea114d9072f70ec6d5db3698aa7188f8` |
| Weighted lifetime-chain initialization | 64,929 | `71cb9d284deebe670655e82679abb37f469415a52a39224c13d0d200c6462caa` |
| Pair allocation: 2 rounds, seed 0, ties disabled | 64,913 | `ae164e5c09855928f92e49c8ff142353a811d17b104a0f163b67eea6f9cec76f` |
| Pair allocation: 5 rounds, seed 11, ties enabled | **64,829** | `0ee7a25b688c090150a8a4039cf394b6115fc6ab666827ac76471c0c83bb0c88` |

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
