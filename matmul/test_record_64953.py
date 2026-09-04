"""Regression for the 64,953 submitted physical IR."""
from matmul.submissions.best_64953 import verify


def test_best_64953_exact_symbolic_score_and_artifact():
    assert verify() == 64953
