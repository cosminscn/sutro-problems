"""Boundary and optimality checks for the allocation/search machinery."""
import itertools
import random
import unittest

from core import Op, Program, check_assignment, lifetimes, parse_ir
from pair_alloc import optimize_pair


class Boundaries(unittest.TestCase):
    def test_read_before_write(self):
        p = parse_ir("1,2;mul 1,1,2;1")
        self.assertTrue(check_assignment(p))
        self.assertEqual(lifetimes(p)[0], [0, 1, 1])

    def test_outputs_live_to_exit(self):
        p = parse_ir("1,2;mul 3,1,2;copy 4,1;3,4")
        p.assignment[3] = 3
        with self.assertRaises(ValueError):
            check_assignment(p)

    def test_duplicate_operand_counts_two_reads(self):
        p = parse_ir("1;mul 2,1,1;2")
        self.assertEqual(lifetimes(p)[0][2], 2)

    def test_pair_flow_matches_exhaustive(self):
        rng = random.Random(22)
        for _ in range(40):
            lives = {v: [s := rng.randrange(6), rng.randrange(s + 1, 8), rng.randrange(1, 6)]
                     for v in range(8)}
            feasible = []
            for labels in itertools.product((1, 2), repeat=8):
                if all(sum(s <= t < e and labels[v] == tier for v, (s, e, _) in lives.items()) <= 2*tier-1
                       for t in range(8) for tier in (1, 2)):
                    feasible.append((sum(lives[v][2] * labels[v] for v in lives), labels))
            if not feasible:
                continue
            original, labels = rng.choice(feasible)
            tiers = dict(enumerate(labels))
            assignment, gain = optimize_pair(lives, tiers, 1, 2)
            self.assertEqual(original - gain, min(x[0] for x in feasible))


if __name__ == "__main__":
    unittest.main()
