"""Reproduce the winning trace from the attributed PR50 seed, without downloads."""
from pathlib import Path
import hashlib
import json

import core
from pair_alloc import improve
import schedule_search as schedules

SEED_SHA256 = "600502a7a2b10f762f145a682b21ecb9062ee81eb3723b250d9a2dbccab03c3e"


def change_passes(ir, passes):
    trace = schedules.parse(ir)
    order = schedules.reorder(trace, {(0, 1, k): (True, False) for k in passes})
    homes, score = schedules.repair(trace, order)
    ir = schedules.emit(trace, order, homes)
    assert core.verify_ir(ir)["score"] == score
    return core.parse_ir(ir)


def reproduce():
    ir = core.SEED.read_text()
    assert hashlib.sha256(ir.encode()).hexdigest() == SEED_SHA256
    p = change_passes(ir, [1, 3, 5, 7, 9])
    assert core.assignment_score(p) == 65319
    p, history = improve(p, rounds=5, seed=0, max_seconds=3600, allow_ties=True)
    assert core.assignment_score(p) == 64953
    path, verified = core.save(p, "reproduced", {
        "source": "https://github.com/cybertronai/sutro-problems/pull/50",
        "seed_sha256": SEED_SHA256,
        "passes": [1, 3, 5, 7, 9], "allocation": history,
    })
    print(json.dumps({"path": str(path), **verified}, indent=2))
    expected = Path(__file__).resolve().parent.parent / "best_64953.ir"
    assert path.read_bytes() == expected.read_bytes(), "Replay differs from submission"
    print("Replay is byte-identical to the submitted IR.")
    return path, verified


if __name__ == "__main__":
    reproduce()
