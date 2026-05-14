# Matrix Multiplication

**Author:** Codex and Cosmin
**Date:** 2026-05-14
**Problem:** 16x16 matmul
**Cost:** 67,904
**IR:** [`output_repacked_tail_zero_copy_deferred_value_colored_live_b_16x16.ir`](output_repacked_tail_zero_copy_deferred_value_colored_live_b_16x16.ir)
**Method:** `generate_output_repacked_tail_zero_copy_deferred_value_colored_live_b_16x16` (zero-copy local reorder + output deferral + live-B evacuation + value-lifetime coloring)

## Idea

This submission builds on the 67,911 deferred value-colored live-B trace with
one local zero-extra-copy reorder around the value eventually colored to home
address `70`.  It moves an existing A reload, `copy 3,295`, three legal
positions earlier across independent arithmetic, then rebuilds the same
max-chain value coloring.

No instruction is added or removed.  The trace still has 1,575 `copy`
operations, and the uncolored post-evacuation score remains 68,041.  The full
7-point gain appears only after value coloring, because the reorder changes the
nearby lifetime interval endpoints enough for the coloring pass to choose a
slightly cheaper address assignment.

In the uncolored post-evac trace, the local reorder is:

```text
old 4761: add  281,36,2
old 4762: mul  2,5,1
old 4763: mul  1,6,1
old 4764: copy 3,295

new 4761: copy 3,295
new 4762: add  281,36,2
new 4763: mul  2,5,1
new 4764: mul  1,6,1
```

The moved copy is independent of the three operations it crosses.  The
moved instruction is an existing reload, not an extra copy operation.

## Path to 67,904

| step | score | savings |
|------|------:|--------:|
| current-order output-repacked tail | 68,433 | |
| + 39 live-B evacuation moves | 68,041 | 392 |
| + value-lifetime address coloring | 67,927 | 114 |
| + three output-write deferrals before coloring | 67,911 | 16 |
| + zero-copy home-70 reload lift before coloring | **67,904** | 7 |

## Cost Breakdown By Address Tier

| tier | addrs | reads | cost |
|------|-------|------:|-----:|
| 1 | 1 | 5,057 | 5,057 |
| 2 | 2..4 | 4,993 | 9,986 |
| 3 | 5..9 | 2,349 | 7,047 |
| 4 | 10..16 | 847 | 3,388 |
| 5 | 17..25 | 1,089 | 5,445 |
| 6 | 26..36 | 1,329 | 7,974 |
| 7 | 37..49 | 328 | 2,296 |
| 8 | 50..64 | 120 | 960 |
| 9 | 65..81 | 124 | 1,116 |
| 10..16 | 82..256 | 785 | 10,304 |
| 17..26 | 257..676 | 682 | 14,331 |
| **total** | | **17,703** | **67,904** |

## Instruction Distribution

| instruction | count | paid reads |
|-------------|------:|-----------:|
| `mul` | 4,096 | 8,192 |
| `add` | 3,840 | 7,680 |
| `copy` | 1,575 | 1,575 |
| output exit | 256 | 256 |
| **total** | **9,511 ops** | **17,703** |

## Verification

```bash
python matmul/submissions/output_repacked_tail_zero_copy_deferred_value_colored_live_b_16x16.py
python matmul/experiments/random_true_matmul_check.py \
  matmul/submissions/output_repacked_tail_zero_copy_deferred_value_colored_live_b_16x16.ir \
  --n 16 --trials 500 --seed 20260524 --min -73 --max 73
```

Observed locally:

```text
output_repacked_tail_zero_copy_deferred_value_colored_live_b_16x16.ir  cost=67,904
matmul/submissions/output_repacked_tail_zero_copy_deferred_value_colored_live_b_16x16.ir: cost=67,904 ok 500 random trials
```
