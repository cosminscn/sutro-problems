"""Rebuild 64,475 with heterogeneous panel row groups and portable allocation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from matmul.submissions.search_64829 import reproduce as reference

core = reference.core
COLUMN_WIDTHS = (6, 10)
ROW_WIDTHS_BY_PANEL = ((4, 4, 4, 4), (5, 5, 6))
CHUNKS_BY_PANEL = (1, 2)
EXPECTED = {
    'captured_generator': (1184459, '6317711c972453658b0b276c08043a1c48a62ea633fe92974e2f6dfc9f0521c0'),
    'dp_initial': (64566, '115d764fd7c296ed9b914fc9f6d8677a255a6b24ecb737b97076be60e560a3d9'),
    'pair2_seed0_no_ties': (64538, 'a83d8b98e6ea6bcd36fbb20174a6638239e9370b73c7facd91f2af7b76df76a7'),
    'pair5_seed11_ties': (64475, 'f8c3255a43f5867e6e4173ebed3d8f7cfe6284a85eb77bc661f1d7f4aa25cf90'),
}
EXPECTED_HISTORY_SHA256 = {
    'pair2_seed0_no_ties': '31379dfa861729fbfa963dc8ed84dfabbaa375f9d4a0e4a667ffd3b1a8292361',
    'pair5_seed11_ties': 'a460814e13ccf1cc569502ff0d391484b5396cf4a3b24601d625f911477ed26b',
}


def generate():
    """Each column panel uses its own literal row partition and chunk width."""
    ops, outputs = [], {}
    next_value = 512

    def emit(code, *sources):
        nonlocal next_value
        dest = next_value
        next_value += 1
        ops.append(core.Op(dest, code, sources))
        return dest

    for columns, widths, chunk in zip(reference.groups(COLUMN_WIDTHS), ROW_WIDTHS_BY_PANEL, CHUNKS_BY_PANEL):
        for rows in reference.groups(widths):
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
            assert not set(outputs).intersection(accumulators)
            outputs.update(accumulators)
    assert set(outputs) == {(i, j) for i in range(16) for j in range(16)}
    return core.Program(tuple(range(512)), ops,
                        tuple(outputs[i, j] for i in range(16) for j in range(16)),
                        {v: v + 1 for v in range(next_value)})


def reproduce(output=None, manifest=None):
    started = time.monotonic()
    stages = []

    def checkpoint(name, p, history=None):
        ir = core.emit(p)
        proof = core.verify_ir(ir)
        score, digest = EXPECTED[name]
        assert proof['score'] == score, (name, proof)
        assert proof['sha256'] == digest, (name, 'stage hash mismatch', proof)
        record = {'name': name, **proof}
        if history is not None:
            record['accepted_history'] = history
            record['history_sha256'] = hashlib.sha256(json.dumps(history, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            assert record['history_sha256'] == EXPECTED_HISTORY_SHA256[name], (name, 'history mismatch')
        stages.append(record)
        print(json.dumps({'stage': name, 'score': score, 'sha256': digest}), flush=True)
        return ir

    p = reference.capture_b(generate())
    checkpoint('captured_generator', p)
    p = reference.initial_allocation(p)
    p = core.parse_ir(checkpoint('dp_initial', p))
    for name, rounds, seed, ties in [('pair2_seed0_no_ties', 2, 0, False),
                                     ('pair5_seed11_ties', 5, 11, True)]:
        # Keep fixed rounds and the reference RNG; no machine-speed cutoff.
        p, history = reference.improve(p, rounds=rounds, seed=seed, max_seconds=float('inf'),
                                       allow_ties=ties, checkpoint=None)
        checkpoint(name, p, history)
    ir = core.emit(p)
    assert ir.encode() == (HERE.parent / 'best_64475.ir').read_bytes(), 'Replay differs from submission'
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(ir)
    helpers = [Path(reference.__file__), reference.SUPPORT / 'core.py', reference.SUPPORT / 'pair_alloc.py',
               REPO / 'matmul/submissions/search_value_coloring.py']
    result = {'score': 64475, 'sha256': EXPECTED['pair5_seed11_ties'][1],
              'fresh_process_replay': True, 'byte_identical_to_submission': True,
              'accepted_histories_match_discovery': True,
              'elapsed_seconds': time.monotonic() - started,
              'configuration': {'row_widths_by_panel': ROW_WIDTHS_BY_PANEL, 'column_widths': COLUMN_WIDTHS,
                                'chunks_by_panel': CHUNKS_BY_PANEL, 'capture_threshold': reference.CAPTURE_THRESHOLD},
              'versions': {'python': platform.python_version(), 'numpy': reference.numpy.__version__,
                           'ortools': reference.ortools.__version__},
              'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'helper_sha256': {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in helpers},
              'stages': stages}
    if manifest is not None:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(result, indent=2) + '\n')
    print('Portable generator replay is byte-identical to best_64475.ir.', flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    reproduce(args.output, args.manifest)
