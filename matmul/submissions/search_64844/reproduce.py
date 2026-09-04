"""Rebuild 64,844 from literal mixed-chunk loops with portable reference allocation."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SUPPORT = HERE.parent / 'search_64953'
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SUPPORT))
import core
from pair_alloc import improve
from matmul.submissions.search_value_coloring import Value, allocate_dp_chains
import numpy
import ortools

ROW_WIDTHS = (5, 5, 6)
COLUMN_WIDTHS = (6, 10)
MACRO_CHUNKS = (1, 1, 2, 2, 2, 2)
CAPTURE_THRESHOLD = 6
EXPECTED = {
    'captured_generator': (1173542, '3ffcb44e9d05d466e0198f6a9c29e2e9f9ed8338b752bb5049981ac85c81cc48'),
    'dp_initial': (64955, '4569972f5b02cd7f657b096d9ebbe95475f97e46185d9a414b0ba352a29925fd'),
    'pair2_seed0_no_ties': (64943, 'd49883c8f07544e814b837d2f649037510d956caec78c9dee3564031e90fb362'),
    'pair5_seed11_ties': (64844, '2f09749a34daa66227b23320de8a19d67ff443e0248a604b175fbb66d8d9f786'),
}


def groups(widths):
    result, start = [], 0
    for width in widths:
        result.append(list(range(start, start + width)))
        start += width
    assert start == 16
    return result


def generate():
    """Column panels first; each macro tile has its literal q1/q2 choice."""
    ops, outputs = [], {}
    next_value = 512

    def emit(code, *sources):
        nonlocal next_value
        dest = next_value
        next_value += 1
        ops.append(core.Op(dest, code, sources))
        return dest

    macro = 0
    for columns in groups(COLUMN_WIDTHS):
        for rows in groups(ROW_WIDTHS):
            chunk = MACRO_CHUNKS[macro]
            macro += 1
            accumulators = {}
            for chunk_id, start_k in enumerate(range(0, 16, chunk)):
                staged_a = {}
                traversal = list(reversed(columns)) if chunk_id % 2 else columns
                for j in traversal:
                    staged_b = {}
                    for i in rows:
                        local = accumulators.get((i, j))
                        for k in range(start_k, start_k + chunk):
                            if k not in staged_b:
                                staged_b[k] = emit('copy', 256 + k * 16 + j)
                            if (i, k) not in staged_a:
                                staged_a[i, k] = emit('copy', i * 16 + k)
                            product = emit('mul', staged_a[i, k], staged_b[k])
                            local = product if local is None else emit('add', local, product)
                        accumulators[i, j] = local
            outputs.update(accumulators)
    assert macro == len(MACRO_CHUNKS)
    return core.Program(tuple(range(512)), ops,
                        tuple(outputs[i, j] for i in range(16) for j in range(16)),
                        {v: v + 1 for v in range(next_value)})


def capture_b(p):
    """Save B[k,j], j>=6, from its first staged value for later row groups."""
    counts = Counter(op.src[0] for op in p.ops if op.code == 'copy')
    q = p.clone()
    q.ops = []
    saved = {}
    next_value = max(p.assignment) + 1
    for op in p.ops:
        origin = op.src[0]
        selected = (op.code == 'copy' and 256 <= origin < 512
                    and counts[origin] > 1
                    and (origin - 256) % 16 >= CAPTURE_THRESHOLD)
        if not selected:
            q.ops.append(op)
        elif origin in saved:
            q.ops.append(replace(op, src=(saved[origin],)))
        else:
            q.ops.append(op)
            saved[origin] = next_value
            q.ops.append(core.Op(next_value, 'copy', (op.dest,)))
            q.assignment[next_value] = next_value + 1
            next_value += 1
    assert len(saved) == 160
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


def reproduce(output=None, manifest=None):
    started = time.monotonic()
    stages = []

    def checkpoint(name, p):
        ir = core.emit(p)
        proof = core.verify_ir(ir)
        score, digest = EXPECTED[name]
        assert proof['score'] == score, (name, proof)
        assert proof['sha256'] == digest, (name, 'stage hash mismatch', proof)
        stages.append({'name': name, **proof})
        print(json.dumps({'stage': name, 'score': score, 'sha256': digest}), flush=True)
        return ir

    p = capture_b(generate())
    checkpoint('captured_generator', p)
    p = initial_allocation(p)
    # The discovered run reparsed the allocated IR here, before either pass.
    # This canonicalizes inserted capture IDs and fixes the flow tie ordering.
    p = core.parse_ir(checkpoint('dp_initial', p))
    for name, rounds, seed, ties in [('pair2_seed0_no_ties', 2, 0, False),
                                     ('pair5_seed11_ties', 5, 11, True)]:
        # Fixed rounds, no host-speed cutoff; use the existing reference RNG.
        p, _ = improve(p, rounds=rounds, seed=seed, max_seconds=float('inf'),
                       allow_ties=ties, checkpoint=None)
        checkpoint(name, p)
    ir = core.emit(p)
    assert ir.encode() == (HERE.parent / 'best_64844.ir').read_bytes(), 'Replay differs from submission'
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(ir)
    helpers = [SUPPORT / name for name in ('core.py', 'pair_alloc.py')]
    helpers.append(REPO / 'matmul/submissions/search_value_coloring.py')
    result = {'score': 64844, 'sha256': EXPECTED['pair5_seed11_ties'][1],
              'fresh_process_replay': True, 'byte_identical_to_submission': True,
              'elapsed_seconds': time.monotonic() - started,
              'configuration': {'row_widths': ROW_WIDTHS, 'column_widths': COLUMN_WIDTHS,
                                'macro_chunks': MACRO_CHUNKS, 'capture_threshold': CAPTURE_THRESHOLD},
              'versions': {'python': platform.python_version(), 'numpy': numpy.__version__, 'ortools': ortools.__version__},
              'helper_sha256': {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in helpers},
              'stages': stages}
    if manifest is not None:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(result, indent=2) + '\n')
    print('Portable generator replay is byte-identical to best_64844.ir.', flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    reproduce(args.output, args.manifest)
