"""Verify the review's algebra, without implementing a holdout evaluator."""
import random
import unittest


class MetricReasoningTests(unittest.TestCase):
    def test_deletion_condition_matches_direct_tversky_comparison(self):
        alpha, beta, eps = 0.2, 0.8, 1e-12
        rng = random.Random(20261027)
        for _ in range(10000):
            truth = rng.uniform(1, 1000)
            tp = rng.uniform(0, truth)
            fn = truth - tp
            fp = rng.uniform(0, 1000)
            dt = rng.uniform(0, tp)
            df = rng.uniform(0, fp)
            before = tp / (tp + alpha * fp + beta * fn + eps)
            after = (tp-dt) / ((tp-dt) + alpha * (fp-df) + beta * (fn+dt) + eps)
            inequality = alpha * tp * df > dt * (alpha * fp + beta * truth + eps)
            self.assertEqual(after > before, inequality)


if __name__ == '__main__':
    unittest.main()
