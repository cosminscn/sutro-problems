# Reproduce the 64,475 matmul program

The literal generator uses column widths **[6,10]**, with different row groups
for the two panels: **[4,4,4,4]** in the narrow panel and **[5,5,6]** in the wide
panel. Their contraction chunks are q1 and q2, respectively. This produces
seven macro tiles with chunks **[1,1,1,1,2,2,2]**. Column traversal reverses
after each chunk, and existing C is consumed immediately through the products.

All 160 B inputs in columns 6–15 are captured from their first cheap stage.
Each capture supplies the later two wide-panel row groups. Narrow-panel B
inputs are staged four times. The result has 1,536 copies, 4,096 multiplies,
3,840 additions and 256 paid exit reads.

From the repository root, with Python 3.12:

```sh
python -m pip install -r matmul/submissions/search_64475/requirements.txt
python matmul/submissions/search_64475/reproduce.py
```

Optional replay artifacts:

```sh
python matmul/submissions/search_64475/reproduce.py \
  --output replayed_64475.ir --manifest replayed_64475.json
```

The package reuses the unchanged portable 64,829 capture, initialization and
allocation helpers. Their dependencies are `search_64953/core.py`,
`search_64953/pair_alloc.py` and `search_value_coloring.allocate_dp_chains`.
Exact hashes and runtime versions are recorded in `validation.json`. NumPy and
OR-Tools versions are pinned because equal-cost flow choices can change bytes.
No research checkout, native ABI, compiler, external seed or network access is
required after those dependencies are installed.

The recorded fresh-process replay used Python **3.12.14**, NumPy **2.3.5** and
OR-Tools **9.15.6755**, finishing in **7.24 seconds**. All four stage bytes and
both accepted allocation-history hashes matched discovery. The focused
`matmul/test_record_64475.py` tests passed (two tests in 0.07 seconds).

## Four exact checkpoints

| Checkpoint | Score | SHA-256 |
|---|---:|---|
| Semantic generator + 160 B captures | 1,184,459 | `6317711c972453658b0b276c08043a1c48a62ea633fe92974e2f6dfc9f0521c0` |
| Weighted lifetime-chain initialization | 64,566 | `115d764fd7c296ed9b914fc9f6d8677a255a6b24ecb737b97076be60e560a3d9` |
| Pair allocation: 2 rounds, seed 0, ties disabled | 64,538 | `a83d8b98e6ea6bcd36fbb20174a6638239e9370b73c7facd91f2af7b76df76a7` |
| Pair allocation: 5 rounds, seed 11, ties enabled | **64,475** | `f8c3255a43f5867e6e4173ebed3d8f7cfe6284a85eb77bc661f1d7f4aa25cf90` |

The allocated initial IR is reparsed before either pair pass; there is no
reparse between the passes. Allocation uses fixed rounds with no wall-time
cutoff, retaining the usual early exit when ties are disabled. Every checkpoint
passes the official scorer and independent noncommutative proof. Both accepted
allocation histories are hashed and checked against discovery. The submitted
IR is read only at the final byte-comparison gate, never as a generator seed.

## Measured change

The immediate parent uses [5,5,6] in both panels and scores 64,829. Changing
only the narrow panel's row partition yields 64,475 under the same allocator.
It adds 96 B reloads but reduces the active narrow tile from at most 36 outputs
to 24. Copy cost rises 663; multiplication, addition and exit save 1,017 in
total. The 354-point net gain is a verified complete-program result. Separate
component minima are not combined into an imagined score.

This is a witness, not an optimality proof. Fixed-trace bounds for earlier
submissions do not transfer. The procedure and its helpers retain the earlier
campaign's attribution; no previous source or submission is modified.

- [Generator](reproduce.py)
- [Recorded portable validation](validation.json)
- [Recorded replay log](replay.log)
- [Submitted program and method](../best_64475.md)
- [Portable 64,829 helpers and lineage](../search_64829/README.md)
