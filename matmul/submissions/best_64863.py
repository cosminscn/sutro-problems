"""Load and independently verify the 64,863 16x16 matmul submission."""
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from matmul import score_16x16
from matmul.submissions.best_66178 import _prove

EXPECTED_SCORE = 64863
EXPECTED_SHA256 = '3cfa88db51db23c350fc41056f617677bea51dc859ff37cb2898c88f80eecb1e'
EXPECTED_OPERATIONS = {'copy': 1683, 'mul': 4096, 'add': 3840}
EXPECTED_READ_COSTS = {'copy': 21312, 'mul': 14272, 'add': 24782, 'output': 4497}
IR_PATH = Path(__file__).with_suffix('.ir')


def generate_best_64863():
    return IR_PATH.read_text(encoding='utf-8')


def verify():
    ir = generate_best_64863()
    assert hashlib.sha256(ir.encode()).hexdigest() == EXPECTED_SHA256
    score = score_16x16(ir)
    operations, read_costs = _prove(ir)
    assert score == EXPECTED_SCORE == sum(read_costs.values())
    assert operations == EXPECTED_OPERATIONS
    assert read_costs == EXPECTED_READ_COSTS
    return score


if __name__ == '__main__':
    print(f'{IR_PATH.name}: score={verify():,}, sha256={EXPECTED_SHA256}')
    print('formal proof: 256/256 outputs match exact noncommutative integer polynomials')
    print(f'operations: {EXPECTED_OPERATIONS}')
    print(f'read costs: {EXPECTED_READ_COSTS}')
