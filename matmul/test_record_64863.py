"""Regression for the 64,863 submitted physical IR."""
from matmul.submissions.best_64863 import verify


def test_best_64863_exact_symbolic_score_and_artifact():
    assert verify() == 64863
