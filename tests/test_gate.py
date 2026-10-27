import copy
import unittest
from scripts.promotion_gate import assess


class GateTests(unittest.TestCase):
    def valid(self):
        return dict(
            assigned_lane='synthetic test lane, not scientific evidence',
            experiments_run=1, experiment_elapsed_seconds=60,
            holdout=dict(evidence_class='HOLDOUT-DTI', evaluator_version='test-v1',
                         withheld_positives=1, dti=.2, ci95=[.1, .3],
                         paired_delta_ci95=[.01, .02], same_evaluator_current_best=True,
                         fold_manifest_sha256='b' * 64,
                         baseline=dict(evaluator_version='test-v1', dti=.15, fold_manifest_sha256='b' * 64)),
            feature_auc=[.6],
            registry=dict(reference_ids=['r1'], **{s: dict(complete=True, comparisons=[
                dict(reference_id='r1', spearman=.90, overlap_3px=.70)]) for s in ['surface', 'final_dots']}),
            validator=dict(raster_sha256='a' * 64, **{k: True for k in [
                'saved_bytes_checked', 'single_band', 'finite_inside', 'range_0_1',
                'crs_match', 'shape_match', 'transform_match']}),
            raster_sha256='a' * 64, submission_name='test', note='test only')

    def test_malformed_objects_fail_closed(self):
        for bad in [None, [], '', 1, {}, {'holdout': []}, {'registry': 'bad'}, {'validator': 2}]:
            with self.subTest(bad=bad):
                self.assertEqual(assess(bad)['verdict'], 'negative')

    def test_valid_is_not_upload_authorization(self):
        result = assess(self.valid())
        self.assertEqual(result['verdict'], 'promote')
        self.assertFalse(result['ok_to_submit'])

    def test_mutations_rejected(self):
        changes = [
            ('assigned_lane', '   '), ('experiments_run', 4), ('experiments_run', True),
            ('experiment_elapsed_seconds', 7201), ('feature_auc', [.90001]),
            ('feature_auc', [float('nan')]), ('feature_auc', [True]),
            ('note', 'a' * 141), ('raster_sha256', 'c' * 64),
            ('holdout.dti', float('inf')), ('holdout.dti', .8),
            ('holdout.ci95', [True, .3]), ('holdout.paired_delta_ci95', [-.01, .02]),
            ('holdout.baseline.evaluator_version', 'other'),
            ('holdout.baseline.fold_manifest_sha256', 'c' * 64),
            ('holdout.baseline.dti', .25), ('validator.transform_match', False),
            ('registry.reference_ids', []), ('registry.reference_ids', ['r1', 'missing']),
            ('registry.reference_ids', ['r1', 'r1']),
            ('registry.surface.comparisons', []), ('registry.surface.comparisons', [None]),
            ('registry.surface.comparisons', [dict(reference_id=[], spearman=0, overlap_3px=0)]),
            ('registry.final_dots.complete', False),
        ]
        for path, value in changes:
            with self.subTest(path=path, value=value):
                card = copy.deepcopy(self.valid())
                parts = path.split('.')
                target = card
                for key in parts[:-1]:
                    target = target[key]
                target[parts[-1]] = value
                self.assertEqual(assess(card)['verdict'], 'negative')

    def test_duplicate_thresholds_both_stages(self):
        for stage in ['surface', 'final_dots']:
            for field, value in [('spearman', .90001), ('spearman', -.90001), ('overlap_3px', .70001)]:
                card = self.valid()
                card['registry'][stage]['comparisons'][0][field] = value
                self.assertEqual(assess(card)['verdict'], 'negative')


if __name__ == '__main__':
    unittest.main()
