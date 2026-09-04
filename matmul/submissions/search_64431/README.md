# Reproduce the 64,431 matmul program

The generator imports the existing `search_64448.reproduce` literal generator
and B-capture function. It does not call that package's allocation replay or
load either final submission as a seed. It checks the parent's raw hash, then
applies exactly these five sequential operation-list slides:

| Source | Destination | Length |
|---:|---:|---:|
| 7902 | 7905 | 2 |
| 7893 | 7991 | 1 |
| 1823 | 1825 | 1 |
| 226 | 222 | 4 |
| 1281 | 1287 | 1 |

Indices are zero-based in the current list. Remove the indicated block first,
then insert it at the destination in the shortened list. After every edit,
the generator checks all dependencies and preservation of every original
operation and operand list. Initial inputs and the final output list remain
the same. The inherited geometry, chunks, rotations and captures are described
in the [parent package](../search_64448/README.md).

## Run

From the repository root, using Python 3.12:

```sh
python3 -m pip install -r matmul/submissions/search_64431/requirements.txt
python3 matmul/submissions/search_64431/reproduce.py
```

Optional outputs:

```sh
python3 matmul/submissions/search_64431/reproduce.py \
  --output replayed_64431.ir --manifest replayed_64431.json
```

The generator and allocator use repository-local Python only. The unchanged
portable 64,829 helpers provide lifetime-chain initialization and pair allocation,
using `search_64953/core.py`, `search_64953/pair_alloc.py` and
`search_value_coloring.allocate_dp_chains`. Parent-generator and helper hashes
are checked against `discovery.json` before replay. NumPy and OR-Tools are
pinned because flow tie choices can affect exact bytes. No research directory,
external seed, native DP library, graph-preparation library, compiler, or network
is needed after dependency installation. `best_64431.ir` is read only for the
final byte-equality assertion.

## Exact checkpoints

| Checkpoint | Score | SHA-256 |
|---|---:|---|
| Prior raw generator plus five edits | 1,177,063 | `3c86365a522ca3909e8b1a892ef38e9edc21f3c54eb873f074854ff7e638be13` |
| Weighted lifetime-chain initialization | 64,458 | `0393e6775e7b73ea8f117dd541247a07f5e8de146359b2ac422cf87d9155f184` |
| Pair allocation: 2 rounds, seed 0, no ties | 64,431 | `66929dab27c72e9714bf8a1ae77f1942b4201fe81d0d7a255a8547108eabadc3` |
| Pair allocation: 5 rounds, seed 11, ties | **64,431** | `9d94114a87fecd30168fbcf63931bbc98a50778984a11fe0c3b16940218bcf11` |

Reparse the allocated initial IR before pair allocation; do not reparse between
the two passes. Fixed rounds, the reference RNG and no machine-speed cutoff
reproduce the discovery settings. The no-tie pass retains its normal early stop
when no improvement exists. Its only strict improvement moves tiers 2/3 and
saves 27. The five-round tie pass has an empty strict-improvement history, yet
changes addresses while preserving total cost. Both histories are checked
against discovery as exact objects and SHA-256 hashes.

Every checkpoint passes the unchanged official scorer and independent exact
noncommutative proof. Fresh portable replay matched all four byte hashes,
both histories and the final submitted bytes in **6.466421250 seconds**, with
Python **3.12.14**, NumPy **2.3.5** and OR-Tools **9.15.6755**. The standalone
verifier and two focused tests also passed under `python -S`; tests took
**0.046 seconds**. These are validation timings, not a language-speed benchmark.

## Discovery and scope

The anchored local-order pilot proposed single-operation slides (45%), contiguous
2–4-operation slides (35%), and swaps of two 1–4-operation bundles (20%). Each
proposal affected at most 128 positions in its parent order. Seed 20260906,
an explicit 20% restart from the exact anchor, and a beam of best four plus four
coarse order signatures within 80 DP points defined the finite search. Cumulative
edits can span multiple original windows.

There were 5,159 proposals: 988 newly screened orders, 4,026 dependency-invalid
orders and 145 duplicates. The screen stopped at its 180-second wall boundary;
the last started candidate completed at 180.049 seconds. Each accepted raw and
DP-initial IR received full official and noncommutative proof. Five mutants and
the exact control received matched final refinement. Including the best research
replay gives 990 generation runs and 1,994 saved stage-proof pairs; repeated
controls, replay, and proof stages are not new algorithms. This package's
portable validation is separate from those research counts.

The selected order changes 117 positions, with maximum displacement 98 and
unchanged peak live count 606. Operation counts remain 1,504 copies, 4,096
multiplies and 3,840 additions; all 17,632 paid reads include the 256 exits.
Versus the exact 64,448 parent, copy cost falls 13 and addition falls 12, while
exit rises 8 and multiplication stays fixed: **17 points saved**. The five edits
were selected jointly; their individual savings are not independently established.
An earlier two-edit finalist also reached the same score, but this package
reproduces the five-edit witness selected and freshly replayed by the search.

The search was heuristic. No global schedule or allocation optimum is claimed,
and fixed-order allocation bounds from earlier traces do not transfer merely
because the arithmetic DAG is unchanged. Previous packages preserve attribution
for the underlying staging, capture, coloring, pair-allocation and proof methods.

- [Generator and replay](reproduce.py)
- [Five-edit configuration](configuration.json)
- [Frozen lineage, stages and history pins](discovery.json)
- [Portable validation](validation.json)
- [Replay log](replay.log)
- [Standard-library proof](proof.log)
- [Focused tests](tests.log)
- [Submitted method](../best_64431.md)
- [Immediate parent](../best_64448.md)
- [Portable allocation helpers](../search_64829/README.md)
- [Earlier attribution](../best_64863.md)
