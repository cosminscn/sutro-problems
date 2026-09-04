# Reproduce the 64,863 matmul program

`../best_64863.ir` computes the full 16×16 matrix product for a paid-read score of **64,863**. It has 4,096 multiplies, 3,840 additions, and 1,683 copies. Its SHA-256 is:

```
3cfa88db51db23c350fc41056f617677bea51dc859ff37cb2898c88f80eecb1e
```

| Charged reads | Cost |
|---|---:|
| Multiplication | 14,272 |
| Addition | 24,782 |
| Copy | 21,312 |
| Common exit | 4,497 |
| **Total** | **64,863** |

All 512 inputs exist at entry and all 256 outputs remain available at the common exit. Each read costs `ceil(sqrt(address))`; copy-source and output reads are included.

## Run the full deterministic replay

From the repository root, using Python 3.12:

```bash
python -m pip install -r matmul/submissions/search_64863/requirements.txt
python matmul/submissions/search_64863/reproduce.py
```

Optional output files:

```bash
python matmul/submissions/search_64863/reproduce.py \
  --output replayed_64863.ir --manifest replayed_64863.json
```

The replay generates the computation from semantic loops. It does not read any previous candidate IR as a starting seed; it reads `best_64863.ir` only for the final byte comparison. Every checkpoint passes the official scorer and the independent noncommutative polynomial verifier. The supplied validation run used Python **3.12.14**, NumPy **2.3.5**, and OR-Tools **9.15.6755**, and completed in **18.52 seconds** on the development host. Dependency versions are pinned because equal-cost flow choices can otherwise alter replay bytes.

No machine-specific compiler, binary, home directory, network access, or research workspace is required. The replay uses the unchanged repository-local `search_64953/core.py`, `pair_alloc.py`, and semantic parser in `schedule_search.py`, plus `search_value_coloring.allocate_dp_chains`. Their exact file hashes are recorded in `validation.json`. Pair allocation runs fixed round counts with no wall-time cutoff; its ordinary no-improvement early exit remains enabled when ties are disabled.

## Generator and checkpoints

The generator processes row groups `4+4+4+4` and column groups **7+9**, visiting column panels first. Within each tile, contraction passes alternate column direction. A values are staged at their first multiply in each pass. For each `B[k,j]` with `j >= 7`, a persistent value is copied from its first already-staged B value; later row groups reload from that capture. This creates 144 persistent captures.

The recapture transformation is separate: after the first future reload of selected B values, copy the cheap staged value immediately before its final short arithmetic use. Redirect subsequent persistent uses to that new capture. Original physical homes remain feasible in each replayed transformation.

| Stage | Score | SHA-256 |
|---|---:|---|
| Semantic generator + 144 captures, before allocation | 1,199,136 | `b0b5b2009c15919ddb24847163faf86cc3b2c3cb687150a439b1908b87114c73` |
| Repeated maximum-weight lifetime-chain allocation | 65,097 | `8267e45855937191f32af6994e0fca21acf4096bb2d0ee6f4942e80b223e8899` |
| Pair allocation: 2 rounds, seed 0, ties disabled | 65,032 | `2c91abd71851716cde1a200269f1701c1c54068b5657dae9ce65a604eed10922` |
| Pair allocation: 5 rounds, seed 11, ties enabled | 64,892 | `e38133d58b3e43e53d028f0741052cb2032bcc0cf6d81f7f905f7af94ccc8f44` |
| Recapture B(0,13), B(0,14); 3 rounds, seed 456, ties enabled | 64,876 | `a5ad7729625ff9ae5522f29153049fed1fe6a6df1ee16d544d0ef458b833c084` |
| Pair allocation: 2 rounds, seed 0, ties enabled | 64,872 | `3a4ffee69365a56084073ea1cb34766ba3209df7032c8ee0952a98c5c0e69910` |
| Recapture B(0,8); 2 rounds, seed 271828, ties enabled | **64,863** | `3cfa88db51db23c350fc41056f617677bea51dc859ff37cb2898c88f80eecb1e` |

The two first recaptures initially cost 64,894 before reallocation; the final recapture initially costs 64,873. Thus the result depends on joint staging and allocation, rather than the new copies being free. In the final seven-coordinate screen, both unchanged controls stayed at 64,872 under the same two-round budgets and seeds 0/271828; B(0,8), seed 271828 reached 64,863. Combining the two strongest singleton candidates did not add their savings.

## Scope and attribution

This is a correct, reproducible witness, not a claim of globally optimal matrix multiplication or address allocation. The older 64,979 and 64,867 fixed-trace certificates apply to different instruction traces and do not bound this changed 7+9 staging graph. A pair-tier flow solve is exact for its selected two-tier subproblem; the complete sequence of pair moves is a heuristic for global allocation.

The 7+9 generator and additional recapture sequence were developed in cosminscn's matmul campaign with Codex. The persistent-capture approach builds on the earlier submission work, including jurajselep's [65,084 submission in PR #50](https://github.com/cybertronai/sutro-problems/pull/50). Existing repository lifetime coloring, the earlier `search_64953` infrastructure, and `best_66178._prove` are reused and retain their original attribution. This replay generates a new trace and does not embed PR #50's IR.

During research, a separate C++ graph-preparation helper accelerated the existing native OR-Tools solver. On a fixed 64,876 input, warm median two-round times were 2.373 seconds in Python and 1.554 seconds with reference-compatible native preparation, producing identical 64,872 bytes. A separate faster tie RNG changed the search path and was measured separately. These are **research iteration timings**, not leaderboard scores. The optional helper and its compiler/binaries are deliberately absent here; the portable replay uses the reference Python path throughout.
