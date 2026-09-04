"""Submission identity and exact-output contract for the 64,475 record."""
import pytest
from matmul.submissions import best_64475


def test_best_64475_exact_outputs_cost_and_artifact():
    # Checks all 256 outputs with two exact polynomial representations, plus
    # the paid source/exit reads, operation counts, and frozen artifact hash.
    assert best_64475.verify() == 64475


def test_best_64475_hash_gate_rejects_changed_artifact(monkeypatch):
    # Even a semantically harmless formatting change must fail identity checks.
    changed = best_64475.generate_best_64475() + '\n'
    assert best_64475.score_16x16(changed) == 64475
    monkeypatch.setattr(best_64475, 'generate_best_64475', lambda: changed)
    with pytest.raises(AssertionError):
        best_64475.verify()
