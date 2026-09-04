"""Submission identity and exact-output contract for the 64,844 record."""
import pytest
from matmul.submissions import best_64844


def test_best_64844_exact_outputs_cost_and_artifact():
    # Checks all 256 outputs with two exact polynomial representations, plus
    # the paid source/exit reads, operation counts, and frozen artifact hash.
    assert best_64844.verify() == 64844


def test_best_64844_hash_gate_rejects_changed_artifact(monkeypatch):
    # Even a semantically harmless formatting change must fail identity checks.
    changed = best_64844.generate_best_64844() + '\n'
    assert best_64844.score_16x16(changed) == 64844
    monkeypatch.setattr(best_64844, 'generate_best_64844', lambda: changed)
    with pytest.raises(AssertionError):
        best_64844.verify()
