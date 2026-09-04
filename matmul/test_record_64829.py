"""Submission identity and exact-output contract for the 64,829 record."""
import pytest
from matmul.submissions import best_64829


def test_best_64829_exact_outputs_cost_and_artifact():
    # Checks all 256 outputs with two exact polynomial representations, plus
    # the paid source/exit reads, operation counts, and frozen artifact hash.
    assert best_64829.verify() == 64829


def test_best_64829_hash_gate_rejects_changed_artifact(monkeypatch):
    # Even a semantically harmless formatting change must fail identity checks.
    changed = best_64829.generate_best_64829() + '\n'
    assert best_64829.score_16x16(changed) == 64829
    monkeypatch.setattr(best_64829, 'generate_best_64829', lambda: changed)
    with pytest.raises(AssertionError):
        best_64829.verify()
