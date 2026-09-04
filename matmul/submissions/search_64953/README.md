# Reproduce the 64,953 submission

This replays the successful search from Juraj Selep's 65,084 IR in
[PR #50](https://github.com/cybertronai/sutro-problems/pull/50), pinned at commit
`61abdfbd4f883add0fbdbc57e186b4edf66976c4`. The attributed source IR is included
as `seed_65084.ir`; its SHA-256 is checked before use. No network access is used
during replay. The new search implementation is by Cosmin and Codex.

From the repository root, with Python 3.12:

```sh
python3 -m venv /tmp/matmul-record-replay
/tmp/matmul-record-replay/bin/python -m pip install -r matmul/submissions/search_64953/requirements.txt
/tmp/matmul-record-replay/bin/python matmul/submissions/search_64953/reproduce.py
```

The replay reverses the column traversal of contraction passes 1, 3, 5, 7, and 9
in the block covering rows 0–3 and columns 8–15, repairs the original placement,
and runs five exact pair-tier allocation sweeps with seed 0, including
cost-neutral moves.

Expected checkpoints: `65,084 → 65,319 → 64,953`.
Intermediate regressions are intentional: scheduling and placement are evaluated
together. Final outputs are symbolically verified and compared byte for byte
with `../best_64953.ir`. Replay took about ten seconds on the development
machine; timing is not part of the optimization objective.

`pair_alloc.py` solves each two-tier subproblem by integral min-cost flow.
Timeline capacities enforce both tiers' occupancy limits. Random integer tie
breaks explore equally good placements while preserving the primary score.
Each subproblem is exact; the overall schedule/allocation is not claimed optimal.

Boundary and small exhaustive optimality checks:

```sh
cd matmul/submissions/search_64953
/tmp/matmul-record-replay/bin/python -m unittest -q test_core.py
```

Pinned replay SHA-256: `e4d210fc2c6a31bd3d363625eacc154847bc83c205eb0a65b658722c8a883e5c`.
