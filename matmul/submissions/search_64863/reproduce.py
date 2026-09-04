"""Rebuild the 64,863 witness from a semantic 7+9 generator, without downloads."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SUPPORT = HERE.parent / "search_64953"
# These existing repository-local helpers are deliberately reused unchanged.
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SUPPORT))
import core
from pair_alloc import improve
import schedule_search
from matmul.submissions.search_value_coloring import Value, allocate_dp_chains
import numpy
import ortools

EXPECTED = {
    "captured_generator": (None, "b0b5b2009c15919ddb24847163faf86cc3b2c3cb687150a439b1908b87114c73"),
    "dp_initial": (65097, "8267e45855937191f32af6994e0fca21acf4096bb2d0ee6f4942e80b223e8899"),
    "pair2_seed0_no_ties": (65032, "2c91abd71851716cde1a200269f1701c1c54068b5657dae9ce65a604eed10922"),
    "pair5_seed11_ties": (64892, "e38133d58b3e43e53d028f0741052cb2032bcc0cf6d81f7f905f7af94ccc8f44"),
    "recapture_13_14_pair3_seed456": (64876, "a5ad7729625ff9ae5522f29153049fed1fe6a6df1ee16d544d0ef458b833c084"),
    "pair2_seed0_ties": (64872, "3a4ffee69365a56084073ea1cb34766ba3209df7032c8ee0952a98c5c0e69910"),
    "recapture_8_pair2_seed271828": (64863, "3cfa88db51db23c350fc41056f617677bea51dc859ff37cb2898c88f80eecb1e"),
}


def generate():
    """Ordinary matmul: four row groups and two column groups of widths 7,9."""
    ops = []
    next_value = 512
    outputs = {}

    def emit(code, *sources):
        nonlocal next_value
        value = next_value
        next_value += 1
        ops.append(core.Op(value, code, sources))
        return value

    for columns in (range(7), range(7, 16)):
        for row_start in range(0, 16, 4):
            rows = range(row_start, row_start + 4)
            accumulators = {}
            for k in range(16):
                staged_a = {}
                traversal = reversed(columns) if k % 2 else columns
                for j in traversal:
                    staged_b = emit("copy", 256 + k * 16 + j)
                    for i in rows:
                        if i not in staged_a:
                            staged_a[i] = emit("copy", i * 16 + k)
                        product = emit("mul", staged_a[i], staged_b)
                        accumulators[i, j] = (
                            emit("add", accumulators[i, j], product) if k else product
                        )
            outputs.update(accumulators)
    return core.Program(
        tuple(range(512)), ops,
        tuple(outputs[i, j] for i in range(16) for j in range(16)),
        {v: v + 1 for v in range(next_value)},
    )


def capture_second_panel(p):
    """Capture each B[k,j], j>=7, from its first existing cheap staging copy."""
    counts = Counter(op.src[0] for op in p.ops if op.code == "copy")
    q = p.clone()
    q.ops = []
    next_value = max(p.assignment) + 1
    captures = {}
    for op in p.ops:
        origin = op.src[0]
        selected = (op.code == "copy" and 256 <= origin < 512
                    and (origin - 256) % 16 >= 7 and counts[origin] > 1)
        if not selected:
            q.ops.append(op)
        elif origin in captures:
            q.ops.append(replace(op, src=(captures[origin],)))
        else:
            q.ops.append(op)
            captures[origin] = next_value
            q.ops.append(core.Op(next_value, "copy", (op.dest,)))
            q.assignment[next_value] = max(q.assignment.values()) + 1
            next_value += 1
    assert len(captures) == 144
    return q


def initial_allocation(p):
    lives = core.lifetimes(p)
    assignment = allocate_dp_chains([Value(v, d, e, n) for v, (d, e, n) in lives.items()])
    fresh = max(assignment.values()) + 1
    for v in lives:
        if v not in assignment:
            assignment[v] = fresh
            fresh += 1
    q = p.clone()
    q.assignment = assignment
    core.check_assignment(q)
    return q


def recapture(p, columns):
    """Move later persistent uses onto a new capture of the first reloaded B."""
    # Canonical IDs make semantic parser labels agree with Program value IDs.
    p = core.parse_ir(core.emit(p))
    labels = schedule_search.parse(core.emit(p)).labels
    lives = core.lifetimes(p)
    users = defaultdict(list)
    for i, op in enumerate(p.ops):
        for value in set(op.src):
            users[value].append(i)
    q = p.clone()
    replacements = {}
    insertions = defaultdict(list)
    next_value = max(q.assignment) + 1
    for j in sorted(columns):
        candidates = [op.dest for op in p.ops if op.code == "copy"
                      and labels[op.dest] == ("B", 0, j) and lives[op.dest][2] == 3]
        assert len(candidates) == 1
        value = candidates[0]
        first_read = users[value][0]
        staged = p.ops[first_read]
        assert staged.code == "copy"
        last_short_use = max(users[staged.dest])
        assert first_read < last_short_use < users[value][1]
        insertions[last_short_use].append(core.Op(next_value, "copy", (staged.dest,)))
        replacements[value] = (first_read, next_value)
        q.assignment[next_value] = p.assignment[value]
        next_value += 1
    q.ops = []
    for i, op in enumerate(p.ops):
        q.ops.extend(insertions[i])
        sources = tuple(replacements[v][1] if v in replacements
                        and i > replacements[v][0] else v for v in op.src)
        q.ops.append(core.Op(op.dest, op.code, sources))
    # Every replayed recapture retains feasible original homes; no repair heuristic.
    core.check_assignment(q)
    return q


def reproduce(output=None, manifest=None):
    started = time.monotonic()
    stages = []

    def checkpoint(name, p, canonicalize=False):
        ir = core.emit(p)
        proof = core.verify_ir(ir)
        score, digest = EXPECTED[name]
        assert score is None or proof["score"] == score, (name, proof)
        assert proof["sha256"] == digest, (name, "stage hash mismatch", proof)
        stages.append({"name": name, **proof})
        print(json.dumps({"stage": name, "score": proof["score"], "sha256": digest}), flush=True)
        return core.parse_ir(ir) if canonicalize else p

    def allocate(p, rounds, seed, ties):
        # Fixed round counts, with an infinite time guard: no host-speed cutoff.
        p, _ = improve(p, rounds=rounds, seed=seed, max_seconds=float("inf"),
                       allow_ties=ties, checkpoint=None)
        return p

    p = checkpoint("captured_generator", capture_second_panel(generate()))
    p = checkpoint("dp_initial", initial_allocation(p))
    p = checkpoint("pair2_seed0_no_ties", allocate(p, 2, 0, False), canonicalize=True)
    p = checkpoint("pair5_seed11_ties", allocate(p, 5, 11, True), canonicalize=True)
    p = recapture(p, (13, 14))
    assert core.assignment_score(p) == 64894
    p = checkpoint("recapture_13_14_pair3_seed456", allocate(p, 3, 456, True), canonicalize=True)
    p = checkpoint("pair2_seed0_ties", allocate(p, 2, 0, True), canonicalize=True)
    p = recapture(p, (8,))
    assert core.assignment_score(p) == 64873
    p = checkpoint("recapture_8_pair2_seed271828", allocate(p, 2, 271828, True))
    ir = core.emit(p)
    submitted = HERE.parent / "best_64863.ir"
    assert ir.encode() == submitted.read_bytes(), "Replay differs from the submitted artifact"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(ir)
    helpers = [SUPPORT / name for name in ("core.py", "pair_alloc.py", "schedule_search.py")]
    helpers.append(REPO / "matmul/submissions/search_value_coloring.py")
    result = {
        "score": 64863, "sha256": EXPECTED["recapture_8_pair2_seed271828"][1],
        "fresh_process_replay": True, "byte_identical_to_submission": True,
        "elapsed_seconds": time.monotonic() - started,
        "versions": {"python": platform.python_version(), "numpy": numpy.__version__, "ortools": ortools.__version__},
        "helper_sha256": {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in helpers},
        "stages": stages,
    }
    if manifest is not None:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(result, indent=2) + "\n")
    print("Full generator replay is byte-identical to best_64863.ir.", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path for the rebuilt IR")
    parser.add_argument("--manifest", type=Path, help="Optional JSON validation manifest")
    args = parser.parse_args()
    reproduce(args.output, args.manifest)
