# Reproduce the 64,456 matmul program

Use the 64,475 layout: column widths **[6,10]**, panel-specific row widths
**[4,4,4,4] / [5,5,6]**, contraction chunks **q1 / q2**, staged operands,
early consumption of old C, and column traversal that reverses each chunk.
The only generator change is **B-capture threshold 7**, independent of the
column-panel boundary at 6. The 144 B inputs in columns 7–15 are retained from
their first staged values; column 6 is reloaded directly in all three row
groups. There are 1,520 copies, 4,096 multiplies and 3,840 adds.

From the repository root, using Python 3.12:

```sh
python -m pip install -r matmul/submissions/search_64456/requirements.txt
python matmul/submissions/search_64456/reproduce.py
```

Optional replay outputs:

```sh
python matmul/submissions/search_64456/reproduce.py \
  --output replayed_64456.ir --manifest replayed_64456.json
```

The generator and capture rule are literal local code. Initialization and pair
allocation reuse the unchanged portable 64,829 helpers, with dependencies on
`search_64953/core.py`, `search_64953/pair_alloc.py` and
`search_value_coloring.allocate_dp_chains`. Helper hashes and exact runtime
versions are recorded in `validation.json`. No external seed, research checkout,
native ABI, compiler or network access is needed after installing the pinned
dependencies. NumPy and OR-Tools versions are pinned because equal-cost flow
choices can affect bytes.

## Four exact checkpoints

| Checkpoint | Score | SHA-256 |
|---|---:|---|
| Literal generator + 144 captures | 1,180,763 | `aacd667605aa14aba986f5681955476de704e87d046973c00598154984841e75` |
| Weighted lifetime-chain initialization | 64,569 | `740a569b8b4704e99086e540951bf74d804d490b071a2696f92b1717f7681421` |
| Pair allocation: 2 rounds, seed 0, no ties | 64,541 | `05c0457a1d721fb3cf38d2d5e6ca445a7128c8df2a3347d3d8bb08284e551462` |
| Pair allocation: 5 rounds, seed 11, ties | **64,456** | `729fbafe50f61e0553f1f3e5e87ec2a6e3d4bdbe0d7bbfefafe5998ba63f445f` |

The allocated initial IR is reparsed before the pair passes; there is no
reparse between them. The portable allocator uses fixed rounds and reference
RNG, with no machine-speed cutoff and the usual early exit when ties are
disabled. All four checkpoints pass the official scorer and independent exact
noncommutative proof. Both accepted allocation histories are hashed and checked
against discovery. The submitted IR is read only for the final byte-comparison
gate, never to construct or seed the candidate.

Fresh-process replay matched all four stage bytes and both histories in
**6.837865084 seconds**, with Python **3.12.14**, NumPy **2.3.5** and OR-Tools
**9.15.6755**. The standalone verifier and two focused tests passed with
third-party site packages disabled (`python -S`); the tests took **0.053s**.

## Measured effect and limits

Relative to 64,475, sixteen fewer captures remove 16 capture-creation reads and
32 captured-value reloads, and require 32 extra original-B reloads. Net copies
fall by 16. Complete-program allocation reduces copy cost by 57; multiply cost
does not change, while add cost increases 10 and exit cost 28. The result saves 19.
The narrow/wide output geometry and arithmetic traversal are unchanged.

This package reproduces one verified witness. It does not establish an optimal
schedule or allocation, and earlier fixed-trace lower bounds do not apply.
No previous source or submission is changed. The original staging, allocation
and proof attribution is retained through the existing package lineage.

- [Literal generator](reproduce.py)
- [Recorded portable validation](validation.json)
- [Replay log](replay.log)
- [Standard-library verification log](proof.log)
- [Focused test log](tests.log)
- [Submitted program and method](../best_64456.md)
- [Immediate parent](../search_64475/README.md)
- [Unchanged portable allocation helpers](../search_64829/README.md)
