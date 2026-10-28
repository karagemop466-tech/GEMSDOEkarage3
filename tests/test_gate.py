import unittest

from scripts.promotion_gate import assess


class GateTests(unittest.TestCase):
    def valid(self):
        return dict(
            assigned_lane='test',
            holdout=dict(
                evidence_class='HOLDOUT-DTI', evaluator_version='test-v1',
                withheld_positives=1, dti=.2, ci95=[.1, .3],
                paired_delta_ci95=[.01, .02], same_evaluator_current_best=True,
            ),
            feature_auc=[.6],
            registry={
                'surface': dict(
                    complete=True, max_abs_spearman=.9, max_overlap_3px=.7,
                    comparisons=[dict(sha256='b' * 64, abs_spearman=.9, overlap_3px=.7)],
                ),
                'final_dots': dict(
                    complete=True, max_abs_spearman=.9, max_overlap_3px=.7,
                    max_literal_overlap_3px=.7,
                    comparisons=[dict(sha256='b' * 64, abs_spearman=.9,
                                     overlap_3px=.7, literal_overlap_3px=.7)],
                ),
                'inventory_sha256': ['b' * 64],
                'manifest_sha256': 'd' * 64,
                'literal_all_rasters_final_passed': True,
            },
            validator={
                **{k: True for k in (
                    'saved_bytes_checked', 'single_band', 'finite_inside', 'range_0_1',
                    'whole_array_finite_range', 'crs_match', 'shape_match', 'transform_match',
                )},
                'raster_sha256': 'a' * 64,
            },
            raster_sha256='a' * 64, submission_name='test', note='test only',
        )

    def test_missing(self):
        self.assertEqual(assess({})['verdict'], 'negative')

    def test_valid_promotes_and_clears_for_selector(self):
        result = assess(self.valid())
        self.assertEqual(result['verdict'], 'promote')
        self.assertTrue(result['ok_to_submit'])
        self.assertTrue(result['selector_required'])

    def test_negative_never_ok_to_submit(self):
        card = self.valid()
        card['holdout']['paired_delta_ci95'] = [-.01, .02]
        result = assess(card)
        self.assertEqual(result['verdict'], 'negative')
        self.assertFalse(result['ok_to_submit'])

    def test_null_calibration_never_waives_literal_failure(self):
        card = self.valid()
        card['registry']['literal_all_rasters_final_passed'] = False
        card['registry']['null_calibrated_all_rasters_final_passed'] = True
        card['registry']['duplicate_rule'] = 'null-calibrated excess overlap <= 0.70'
        card['registry']['final_dots']['max_literal_overlap_3px'] = .9936
        card['registry']['final_dots']['comparisons'][0]['literal_overlap_3px'] = .9936
        self.assertEqual(assess(card)['verdict'], 'negative')
        self.assertTrue(any('null-calibration cannot waive' in r for r in assess(card)['reasons']))

    def test_raw_literal_overlap_above_threshold_fails_even_if_calibrated_passes(self):
        card = self.valid()
        card['registry']['null_calibrated_all_rasters_final_passed'] = True
        card['registry']['final_dots']['max_literal_overlap_3px'] = .70001
        card['registry']['final_dots']['comparisons'][0]['literal_overlap_3px'] = .70001
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_raw_literal_overlap_at_threshold_passes(self):
        card = self.valid()
        self.assertEqual(assess(card)['verdict'], 'promote')

    def test_duplicate(self):
        card = self.valid()
        card['registry']['final_dots']['max_overlap_3px'] = .70001
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_surface_overlap_and_manifest_required(self):
        card = self.valid()
        card['registry']['surface']['comparisons'][0]['overlap_3px'] = .70001
        self.assertEqual(assess(card)['verdict'], 'negative')
        card = self.valid()
        del card['registry']['surface']['comparisons'][0]['overlap_3px']
        self.assertEqual(assess(card)['verdict'], 'negative')
        card = self.valid()
        del card['registry']['manifest_sha256']
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_boundaries_at_both_stages(self):
        self.assertEqual(assess(self.valid())['verdict'], 'promote')
        for stage in ('surface', 'final_dots'):
            card = self.valid()
            card['registry'][stage]['comparisons'][0]['abs_spearman'] = .90001
            self.assertEqual(assess(card)['verdict'], 'negative')

    def test_legacy_excluded_rasters_stop(self):
        card = self.valid()
        card['correlation_and_overlap_vs_registry'] = {'literal_all_rasters_final_passed': False}
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_literal_required(self):
        card = self.valid()
        del card['registry']['literal_all_rasters_final_passed']
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_malformed(self):
        self.assertEqual(assess({'holdout': [], 'registry': [], 'validator': []})['verdict'], 'negative')
        self.assertEqual(assess([])['verdict'], 'negative')

    def test_missing_reference_and_wrong_hash(self):
        card = self.valid()
        card['registry']['inventory_sha256'].append('c' * 64)
        self.assertEqual(assess(card)['verdict'], 'negative')
        card = self.valid()
        card['validator']['raster_sha256'] = 'c' * 64
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_unhashable_registry_id_fails_closed(self):
        card = self.valid()
        card['registry']['surface']['comparisons'][0]['sha256'] = []
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_literal_failure_overrides_filtered_pass(self):
        card = self.valid()
        card['correlation_and_overlap_vs_registry'] = {'literal_all_rasters_final_passed': False}
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_dense_lattice_is_not_exempt(self):
        card = self.valid()
        card['evidence'] = {'is_calibration_lattice': True, 'within_3px_fraction': .996866}
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_ci_must_contain_estimate(self):
        card = self.valid()
        card['holdout']['ci95'] = [.3, .4]
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_nan(self):
        card = self.valid()
        card['feature_auc'] = [float('nan')]
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_whole_array_finite_range_is_required(self):
        for value in (None, False):
            card = self.valid()
            card['validator']['whole_array_finite_range'] = value
            self.assertEqual(assess(card)['verdict'], 'negative')
        card = self.valid()
        del card['validator']['whole_array_finite_range']
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_wrong_grid(self):
        card = self.valid()
        card['validator']['transform_match'] = False
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_missing_ci(self):
        card = self.valid()
        card['holdout']['paired_delta_ci95'] = [-.01, .02]
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_point_outside_ci_rejected(self):
        card = self.valid()
        card['holdout']['dti'] = .9
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_reverse_label_leakage_rejected(self):
        card = self.valid()
        card['feature_auc'] = [.05]
        self.assertEqual(assess(card)['verdict'], 'negative')


class GateRegressionTests(GateTests):
    def test_ci_must_contain_point(self):
        card = self.valid()
        card['holdout']['ci95'] = [.01, .1]
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_reverse_discriminator_is_also_a_canary(self):
        card = self.valid()
        card['feature_auc'] = [.05]
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_superseded_card_cannot_promote(self):
        card = self.valid()
        card['release_review'] = {'reason': 'literal registry failure'}
        self.assertEqual(assess(card)['verdict'], 'negative')


if __name__ == '__main__':
    unittest.main()
