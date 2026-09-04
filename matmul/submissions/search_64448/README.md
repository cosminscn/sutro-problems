# Reproduce the 64,448 matmul program

This package rebuilds one selected witness from literal loops. It keeps the
64,456 program's column panels **[6,10]**, panel-specific row groups
**[4,4,4,4] / [5,5,6]**, and one-term/two-term contraction chunks. It changes
three tiles' contraction starting points, reverses the initial column traversal
in two tiles, and raises the persistent B-capture threshold from 7 to **8**.

Each tile visits `k = offset, ..., 15, 0, ..., offset-1`, consuming every
contraction index exactly once. Two-term chunks partition this rotated sequence.
Column direction alternates after each chunk; the table gives its first direction.
All indices and half-open intervals below are zero-based.

| Rows | Columns | Chunk width | k offset | Initial column direction |
|---|---|---:|---:|---|
| [0,4) | [0,6) | 1 | 3 | Ascending |
| [4,8) | [0,6) | 1 | 11 | Ascending |
| [8,12) | [0,6) | 1 | 0 | Ascending |
| [12,16) | [0,6) | 1 | 0 | Ascending |
| [0,5) | [6,16) | 2 | 0 | Descending |
| [5,10) | [6,16) | 2 | 0 | Ascending |
| [10,16) | [6,16) | 2 | 4 | Descending |

Tiles run in table order. A is staged at first use and reused across columns;
B is staged per column and reused across rows. Products are always
`A[i,k] * B[k,j]`, and each is immediately folded into its output accumulator.
The first staged B values in columns 8–15 create 128 persistent captures for
the later wide-panel row groups. Columns 6 and 7 reload their original inputs.

From the repository root, using Python 3.12:

```sh
python3 -m pip install -r matmul/submissions/search_64448/requirements.txt
python3 matmul/submissions/search_64448/reproduce.py
```

Optional outputs:

```sh
python3 matmul/submissions/search_64448/reproduce.py \
  --output replayed_64448.ir --manifest replayed_64448.json
```

The generator and capture rule are literal local code. Initialization and
pair allocation reuse the unchanged portable 64,829 helpers, with dependencies
on `search_64953/core.py`, `search_64953/pair_alloc.py`, and the repository's
`search_value_coloring.allocate_dp_chains`. NumPy and OR-Tools are pinned because
equal-cost flow choices can affect bytes. No external seed, research checkout,
native DP library, graph-preparation ABI, compiler, or network access is needed
after installing these dependencies. The submitted IR is read only for the
final comparison, never to construct or seed the candidate.

## Exact checkpoints

| Checkpoint | Score | SHA-256 |
|---|---:|---|
| Literal generator + 128 captures | 1,177,063 | `6dca745d2e7fff3e23794dc28c6481fde140bb522922ab34c06d9e2c3cfb089a` |
| Weighted lifetime-chain initialization | 64,476 | `88bca3be93761060e23de4d10b0c0a0419e0ca513ada0154686da099110be3df` |
| Pair allocation: 2 rounds, seed 0, no ties | 64,448 | `e01319a1c15e676daa105e094513df78d6e4a85f1cf92656b1053175e96f1053` |
| Pair allocation: 5 rounds, seed 11, ties | **64,448** | `5cbf44a58ab45a28da2da90fdad48083d332daa57971da7ab5340225018be33b` |

Reparse the allocated initial IR before the pair passes; do not reparse between
them. The portable allocator uses fixed rounds, reference RNG, no machine-speed
cutoff, and the usual early exit when ties are disabled. Every checkpoint passes
the unchanged official scorer and independent exact noncommutative proof.
Both strict-improvement histories are hashed and checked against discovery.
Neutral moves in the final pass change placement without changing the score;
that pass's strict-improvement history is empty.

Fresh portable replay matched all four stage hashes, both history hashes, and
the final submitted bytes in **6.385736291 seconds**, with Python **3.12.14**,
NumPy **2.3.5**, and OR-Tools **9.15.6755**. The standalone verifier and two
focused tests also passed with site packages disabled (`python -S`); tests took
**0.046 seconds**. The package records helper, generator and discovery-config
hashes in `validation.json`.

## Measured effect and scope

The final program contains **1,504 copies**, **4,096 multiplies**, **3,840 adds**,
and **17,632 paid reads**, including all 256 common-exit reads. Compared with
64,456, it removes 16 persistent B captures: 16 fewer capture-creation reads and
32 fewer captured-value reloads, replaced by 32 original-B reloads. There are
16 fewer copies overall. After the combined schedule/capture changes and
allocation, copy cost rises 50, multiplication is unchanged, addition falls 7,
and exit falls 51, producing the **eight-point** gain. These coupled costs do not
establish separate savings from each mutation.

The witness was selected from a finite search of 1,000 new raw-distinct programs,
seeded by the parent and six archived structural configurations. The search
also allowed guillotine geometry, nonuniform per-leaf contraction compositions,
orientation, and traversal changes. Nine configurations received matched final
refinement. This winning witness retains uniform chunks and the parent geometry;
it is not evidence of a large gain from nonuniform contraction compositions.

Discovery used a parity-checked native DP initializer and native graph preparation
to accelerate iteration. This portable replay uses the reference Python
implementations and checks identical stage hashes and histories. The reported
score is paid read cost, not execution time. No optimal schedule/allocation claim
is made; fixed-graph bounds for previous programs do not transfer.

The preceding packages preserve attribution for staging, captures, value
coloring, pair allocation, and the exact proof, including Juraj Selep's PR #50.
No previous source or submission is changed by this package.

- [Literal generator](reproduce.py)
- [Exact discovery configuration](configuration.json)
- [Discovery stage and history pins](discovery.json)
- [Portable validation](validation.json)
- [Replay log](replay.log)
- [Standard-library verification log](proof.log)
- [Focused test log](tests.log)
- [Submitted program and method](../best_64448.md)
- [Immediate parent](../best_64456.md)
- [Portable allocation helpers](../search_64829/README.md)
- [Earlier attribution](../best_64863.md)
- [Juraj Selep's PR #50](https://github.com/cybertronai/sutro-problems/pull/50)
