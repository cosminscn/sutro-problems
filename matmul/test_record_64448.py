"""Exact-output and frozen-artifact contracts for the 64,448 submission."""
import unittest
from unittest.mock import patch
from matmul.submissions import best_64448


class Record64448Tests(unittest.TestCase):
    def test_exact_outputs_cost_and_artifact(self):
        # Two exact polynomial representations check all 256 outputs. The
        # verifier also checks paid source/exit reads and the frozen hash.
        self.assertEqual(best_64448.verify(), 64448)

    def test_hash_gate_rejects_changed_artifact(self):
        changed = best_64448.generate_best_64448() + '\n'
        self.assertEqual(best_64448.score_16x16(changed), 64448)
        with patch.object(best_64448, 'generate_best_64448', return_value=changed):
            with self.assertRaises(AssertionError):
                best_64448.verify()


if __name__ == '__main__':
    unittest.main()
