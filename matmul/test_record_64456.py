"""Exact-output and frozen-artifact contracts for the 64,456 submission."""
import unittest
from unittest.mock import patch
from matmul.submissions import best_64456


class Record64456Tests(unittest.TestCase):
    def test_exact_outputs_cost_and_artifact(self):
        # Two exact polynomial representations check all 256 outputs. The
        # verifier also checks paid source/exit reads and the frozen hash.
        self.assertEqual(best_64456.verify(), 64456)

    def test_hash_gate_rejects_changed_artifact(self):
        changed = best_64456.generate_best_64456() + '\n'
        self.assertEqual(best_64456.score_16x16(changed), 64456)
        with patch.object(best_64456, 'generate_best_64456', return_value=changed):
            with self.assertRaises(AssertionError):
                best_64456.verify()


if __name__ == '__main__':
    unittest.main()
