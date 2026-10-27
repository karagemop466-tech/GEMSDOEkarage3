import copy
import unittest

from scripts.promotion_gate import assess


class GateTests(unittest.TestCase):
    def setUp(self):
        self.sha = 'a' * 64
        self.template_sha = 'b' * 64
        self.registry_sha = 'c' * 64
        self.fold_sha = 'd' * 64
        self.reference_ids = ['r1', 'r2', 'r3', 'r4']
        stage = dict(complete=True, expected_rasters=4, checked_rasters=4, failed_rasters=0,
                     manifest_sha256=self.registry_sha, candidate_sha256=self.sha,
                     max_abs_spearman=.9, max_overlap_3px=.7,
                     comparisons=[dict(reference_id=name, spearman=.9, overlap_3px=.7)
                                  for name in self.reference_ids])
        self.card = dict(
            hypothesis='test mechanism', mechanism='test', non_fault_mimic='contact',
            assigned_lane='test', experiments_run=1, elapsed_seconds=100,
            holdout=dict(evidence_class='HOLDOUT-DTI', evaluator_version='test-v1', withheld_positives=20,
                         dti=.2, ci95=[.1, .3], paired_delta=.05, paired_delta_ci95=[.01, .08],
                         same_evaluator_current_best=True, fold_manifest_sha256=self.fold_sha,
                         baseline=dict(evaluator_version='test-v1', fold_manifest_sha256=self.fold_sha, dti=.15),
                         whole_segment_buffered=True, catalogue_features_visible_only=True,
                         visible_faults_masked_pixel_exactly=True),
            feature_count=2, feature_names=['one', 'two'], feature_auc=[.6, .9],
            registry={'reference_ids': self.reference_ids, 'surface': copy.deepcopy(stage),
                      'final_dots': copy.deepcopy(stage)},
            validator=dict(template_organizer_authenticated=True, template_sha256=self.template_sha,
                           outside_encoding_policy_resolved=True, outside_policy='allfinite'),
            raster_sha256=self.sha, output_kind='binary', submission_name='test', note='test only')
        self.inspected = dict(core_checks_passed=True, raster_sha256=self.sha, template_sha256=self.template_sha,
                              inside_binary=True, whole_grid_finite_and_in_range=True, whole_grid_unmasked=True,
                              outside_footprint_all_null_or_nan=False)

    def test_missing_and_malformed_fail_closed(self):
        for data in ({}, None, [], {'registry': [], 'holdout': 'bad', 'validator': True}):
            with self.subTest(data=data):
                self.assertEqual(assess(data)['verdict'], 'negative')

    def test_valid_is_not_upload_authorization(self):
        result = assess(self.card, self.inspected)
        self.assertEqual(result['verdict'], 'promote')
        self.assertFalse(result['ok_to_submit'])
        self.assertTrue(result['selector_required'])

    def test_cannot_promote_without_saved_byte_inspection(self):
        self.assertEqual(assess(self.card)['verdict'], 'negative')

    def test_duplicate_at_either_stage(self):
        for stage in ('surface', 'final_dots'):
            card = copy.deepcopy(self.card)
            card['registry'][stage]['max_overlap_3px'] = .70001
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_incomplete_or_different_registry(self):
        for field, value in [('checked_rasters', 3), ('manifest_sha256', 'e' * 64), ('failed_rasters', 1)]:
            card = copy.deepcopy(self.card)
            card['registry']['final_dots'][field] = value
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_per_reference_coverage_and_measurements_fail_closed(self):
        for stage in ('surface', 'final_dots'):
            for changed in ([], [None], [dict(reference_id=[], spearman=0, overlap_3px=0)],
                            [dict(reference_id='r1', spearman=-.90001, overlap_3px=0)]):
                card = copy.deepcopy(self.card)
                card['registry'][stage]['comparisons'] = changed
                self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')
            card = copy.deepcopy(self.card)
            card['registry'][stage]['comparisons'][0]['overlap_3px'] = .70001
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')
            card = copy.deepcopy(self.card)
            card['registry'][stage]['comparisons'][0]['spearman'] = .8
            card['registry'][stage]['max_abs_spearman'] = .8
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')
        for ids in ([], ['r1', 'r1'], ['r1', 'missing'], [[]]):
            card = copy.deepcopy(self.card)
            card['registry']['reference_ids'] = ids
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_parallel_regression_malformed_sections_and_bounds(self):
        for field in ('holdout', 'registry', 'validator'):
            for value in (True, 42, 'bad', []):
                card = copy.deepcopy(self.card)
                card[field] = value
                self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')
        for field, value in [('assigned_lane', '  '), ('experiments_run', True),
                             ('feature_auc', [float('nan'), .5]),
                             ('feature_auc', [True, .5])]:
            card = copy.deepcopy(self.card)
            card[field] = value
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')
        for field, value in [('dti', float('inf')), ('ci95', [True, .3]),
                             ('paired_delta_ci95', [.1, 2])]:
            card = copy.deepcopy(self.card)
            card['holdout'][field] = value
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_canaries_are_complete_and_direction_invariant(self):
        for values in ([float('nan')], [.5], [.5, .90001], [.5, .09999]):
            card = copy.deepcopy(self.card)
            card['feature_auc'] = values
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_wrong_or_uninspected_bytes(self):
        for change in ({'raster_sha256': 'f' * 64}, {'core_checks_passed': False},
                       {'template_sha256': 'f' * 64}, {'inside_binary': False}, {'whole_grid_unmasked': False}):
            inspected = self.inspected | change
            self.assertEqual(assess(self.card, inspected)['verdict'], 'negative')

    def test_template_or_outside_provenance_missing(self):
        for field, value in [('template_organizer_authenticated', False),
                             ('outside_encoding_policy_resolved', False),
                             ('outside_policy', 'null_or_nan')]:
            card = copy.deepcopy(self.card)
            card['validator'][field] = value
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_probabilities_blocked_for_current_shared_template(self):
        card = copy.deepcopy(self.card)
        card['output_kind'] = 'probabilities'
        self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_missing_paired_improvement_or_matching_baseline(self):
        for update in ({'paired_delta_ci95': [-.01, .08]}, {'paired_delta': .04},
                       {'fold_manifest_sha256': 'e' * 64}, {'whole_segment_buffered': False},
                       {'ci95': [.21, .3]}):
            card = copy.deepcopy(self.card)
            card['holdout'].update(update)
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')

    def test_budget_and_note(self):
        for update in ({'experiments_run': 4}, {'elapsed_seconds': 7201}, {'note': 'x' * 141}):
            card = self.card | update
            self.assertEqual(assess(card, self.inspected)['verdict'], 'negative')


if __name__ == '__main__':
    unittest.main()
