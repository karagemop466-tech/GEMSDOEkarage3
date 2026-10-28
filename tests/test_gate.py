import json
import unittest
from pathlib import Path

from scripts.promotion_gate import assess

ROOT = Path(__file__).resolve().parents[1]


class GateTests(unittest.TestCase):
    def valid(self):
        stages = {
            'surface': dict(
                complete=True,
                max_abs_spearman=.9,
                max_overlap_3px=.7,
                comparisons=[dict(sha256='b' * 64, abs_spearman=.9, overlap_3px=.7)],
            ),
            'final_dots': dict(
                complete=True,
                max_abs_spearman=.9,
                max_overlap_3px=.7,
                max_literal_overlap_3px=.7,
                comparisons=[dict(sha256='b' * 64, abs_spearman=.9, overlap_3px=.7, literal_overlap_3px=.7)],
            ),
        }
        return dict(
            assigned_lane='test',
            holdout=dict(evidence_class='HOLDOUT-DTI', evaluator_version='test-v1', withheld_positives=1,
                         dti=.2, ci95=[.1, .3], paired_delta_ci95=[.01, .02], same_evaluator_current_best=True),
            feature_auc=[.6],
            registry={**stages, 'inventory_sha256':['b' * 64], 'manifest_sha256':'d' * 64,
                      'literal_all_rasters_final_passed':True},
            validator={**{k:True for k in ['saved_bytes_checked', 'single_band', 'finite_inside', 'range_0_1',
                                           'whole_array_finite_range', 'crs_match', 'shape_match', 'transform_match']},
                       'raster_sha256':'a' * 64},
            raster_sha256='a' * 64,
            submission_name='test',
            note='test only',
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

    def test_null_calibration_cannot_override_literal_failure(self):
        card = self.valid()
        card['registry']['literal_all_rasters_final_passed'] = False
        card['registry']['null_calibrated_all_rasters_final_passed'] = True
        card['registry']['duplicate_rule'] = 'diagnostic only: null-calibrated excess overlap'
        card['registry']['final_dots']['max_literal_overlap_3px'] = .9936
        card['registry']['final_dots']['comparisons'][0]['literal_overlap_3px'] = .9936
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_literal_overlap_above70_is_never_exempt(self):
        card = self.valid()
        card['evidence'] = {'within_3px_fraction':.9936, 'footprint_3px_coverage_p0':.9987,
                            'null_calibrated_excess_overlap':0.0}
        self.assertEqual(assess(card)['verdict'], 'negative')
        card = self.valid()
        card['registry']['final_dots']['comparisons'][0]['literal_overlap_3px'] = .70001
        card['registry']['final_dots']['max_literal_overlap_3px'] = .70001
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_final_literal_overlap_must_be_explicit(self):
        card = self.valid()
        del card['registry']['final_dots']['comparisons'][0]['literal_overlap_3px']
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_duplicate(self):
        card = self.valid()
        card['registry']['final_dots']['max_literal_overlap_3px'] = .70001
        card['registry']['final_dots']['comparisons'][0]['literal_overlap_3px'] = .70001
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_surface_rank_correlation_and_manifest_required(self):
        card = self.valid()
        card['registry']['surface']['comparisons'][0]['abs_spearman'] = .90001
        self.assertEqual(assess(card)['verdict'], 'negative')
        card = self.valid()
        del card['registry']['manifest_sha256']
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_null_calibrated_excess_is_diagnostic_only(self):
        card = self.valid()
        card['registry']['final_dots']['comparisons'][0]['null_calibrated_excess_overlap'] = .99
        self.assertEqual(assess(card)['verdict'], 'promote')

    def test_boundaries_at_both_stages(self):
        self.assertEqual(assess(self.valid())['verdict'], 'promote')
        for stage in ('surface', 'final_dots'):
            card = self.valid()
            card['registry'][stage]['comparisons'][0]['abs_spearman'] = .90001
            self.assertEqual(assess(card)['verdict'], 'negative')

    def test_legacy_excluded_rasters_stop(self):
        card = self.valid()
        card['correlation_and_overlap_vs_registry'] = {'literal_all_rasters_final_passed':False}
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
        card['correlation_and_overlap_vs_registry'] = {'literal_all_rasters_final_passed':False}
        self.assertEqual(assess(card)['verdict'], 'negative')

    def test_dense_lattice_is_not_exempt(self):
        card = self.valid()
        card['evidence'] = {'is_calibration_lattice':True, 'within_3px_fraction':.996866}
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
        card['release_review'] = {'reason':'literal registry failure'}
        self.assertEqual(assess(card)['verdict'], 'negative')


class CurrentReleaseRegressionTests(unittest.TestCase):
    def test_archived_k3c_candidate_is_blocked_by_literal_gate(self):
        card = json.loads((ROOT / 'docs/k3c/run-card.json').read_text())
        result = assess(card)
        self.assertEqual(result['verdict'], 'negative')
        self.assertFalse(result['ok_to_submit'])
        self.assertFalse(card['registry']['literal_all_rasters_final_passed'])

    def test_current_decision_pages_do_not_advertise_download_approval(self):
        for relative in ('index.html', 'executive-summary.html', 'docs/index.html',
                         'docs/executive-summary.html', 'docs/k3c/index.html', 'docs/k3c/how-to-submit.html'):
            page = (ROOT / relative).read_text()
            self.assertNotIn('OK TO DOWNLOAD AND SUBMIT: YES', page, relative)
            self.assertNotIn('PROMOTE · OK TO SUBMIT', page, relative)
        for relative in ('docs/k3c/index.html', 'docs/k3c/how-to-submit.html'):
            page = (ROOT / relative).read_text()
            self.assertNotIn('Download submission .tif', page, relative)
            self.assertIn('DO NOT SUBMIT', page, relative)
