"""Literal card-screen regressions; an affirmative screen still needs a selector."""
import json
from pathlib import Path
import unittest

from scripts.promotion_gate import KNOWN_WITNESS_SHA256, OVERLAP_METRIC, assess

ROOT = Path(__file__).resolve().parents[1]


class GateTests(unittest.TestCase):
    def valid(self):
        a, b, m, candidate = KNOWN_WITNESS_SHA256, 'b' * 64, 'c' * 64, 'd' * 64
        def stage():
            return {'complete': True, 'overlap_metric': OVERLAP_METRIC,
                    'support_count': 100, 'support_definition': 'pre-registered positive support',
                    'support_sha256': 'e' * 64, 'surface_sha256': 'f' * 64,
                    'candidate_raster_sha256': candidate,
                    'max_abs_spearman': .90, 'max_overlap_3px': .70,
                    'comparisons': [{'sha256': a, 'abs_spearman': .90, 'overlap_3px': .70},
                                    {'sha256': b, 'abs_spearman': .20, 'overlap_3px': .25}]}
        return {
            'assigned_lane': 'synthetic fixture; not a science result',
            'hypothesis': 'synthetic hypothesis', 'mechanism': 'synthetic mechanism',
            'named_non_fault_mimic': 'synthetic mimic', 'experiments_run': 1, 'elapsed_seconds': 5,
            'holdout': {'evidence_class': 'HOLDOUT-DTI', 'evaluator_version': 'fixture-v1',
                        'withheld_positives': 99, 'dti': .2, 'ci95': [.1, .3],
                        'paired_delta_ci95': [.01, .04], 'same_evaluator_current_best': True,
                        'current_best_dti': .19, 'withheld_unit': 'whole-fault-segment', 'buffer_m': 1500,
                        'catalogue_features_visible_only': True, 'visible_faults_masked_pixel_exactly': True,
                        'predictions_fold_local': True, 'pooled': True, 'alpha': .2, 'beta': .8,
                        'radius_m': 300, 'kernel': 'triangular', 'shared_template_commit': '1' * 40,
                        'evaluator_sha256': '2' * 64, 'holdout_implementation_sha256': '3' * 64,
                        'fold_assignment_sha256': '4' * 64,
                        'protocol_audit': {**{k: True for k in ('whole_fault_segments', 'truth_visible_buffer',
                            'visible_only_catalogue_features', 'visible_pixels_masked_exactly',
                            'zero_truth_false_positives_conserved')}, 'report_sha256': '5' * 64},
                        'current_best': {'evidence_class': 'HOLDOUT-DTI', 'evaluator_version': 'fixture-v1',
                            'evaluator_sha256': '2' * 64, 'holdout_implementation_sha256': '3' * 64,
                            'fold_assignment_sha256': '4' * 64, 'withheld_positives': 99,
                            'dti': .19, 'ci95': [.1, .25]}},
            'feature_names': ['synthetic1', 'synthetic2'], 'feature_auc': [.8, .5],
            'registry': {'inventory_sha256': [a, b], 'manifest_sha256': m,
                         'literal_all_rasters_final_passed': True,
                         'surface': stage(), 'final_dots': stage()},
            'validator': {**{k: True for k in ('saved_bytes_checked', 'geotiff', 'single_band', 'dtype_float32',
                         'finite_inside', 'inside_unmasked', 'self_contained_tiff', 'range_0_1',
                         'whole_array_finite_range', 'outside_policy_checked', 'outside_null_or_nan',
                         'crs_match', 'shape_match', 'transform_match')}, 'raster_sha256': candidate},
            'raster_sha256': candidate, 'submission_name': 'fixture.tif', 'note': 'synthetic',
        }

    def test_required_witness_matches_pinned_geometry_audit(self):
        audit = json.loads((ROOT / 'evidence/geometry_audit.json').read_text())
        self.assertEqual(KNOWN_WITNESS_SHA256, audit['lattice']['sha256'])

    def test_exact_boundaries_pass_card_screen_only(self):
        result = assess(self.valid())
        self.assertEqual(result['verdict'], 'promote')
        self.assertTrue(result['selector_required'])
        self.assertTrue(result['eligible_for_selector'])
        self.assertTrue(result['technically_eligible'])
        self.assertFalse(result['ok_to_submit'])  # screen alone never authorizes a slot
        self.assertFalse(result['selector_approval'])
        self.assertFalse(result['slot_used'])

    def test_protocol_provenance_same_folds_and_saved_bytes_are_required(self):
        mutations = [
            lambda c: c['holdout'].update(holdout_implementation_sha256='9ce9cf359f4d7b7fa844dd8f208ec00c3e6c15afef5d724d9014320b944d318d'),
            lambda c: c['holdout'].update(shared_template_commit=None),
            lambda c: c['holdout']['protocol_audit'].update(truth_visible_buffer=False),
            lambda c: c['holdout']['protocol_audit'].update(zero_truth_false_positives_conserved=False),
            lambda c: c['holdout']['current_best'].update(fold_assignment_sha256='7' * 64),
            lambda c: c['holdout']['current_best'].update(withheld_positives=100),
            lambda c: c['holdout']['current_best'].update(evidence_class='ORGANIZER-CONFIRMED'),
            lambda c: c['validator'].update(geotiff=False),
            lambda c: c['validator'].update(inside_unmasked=False),
            lambda c: c['validator'].update(self_contained_tiff=False),
            lambda c: c['validator'].update(outside_policy_checked=False),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                card = self.valid(); mutate(card)
                result = assess(card)
                self.assertEqual(result['verdict'], 'negative')
                self.assertFalse(result['ok_to_submit'])

    def test_both_stages_enforce_literal_overlap_without_null_exemptions(self):
        for stage in ('surface', 'final_dots'):
            for value in (.700001, 1., None, float('nan')):
                with self.subTest(stage=stage, value=value):
                    c = self.valid(); r = c['registry'][stage]
                    r['comparisons'][0]['overlap_3px'] = value
                    r['max_overlap_3px'] = value
                    r['comparisons'][0]['null_calibrated_excess_overlap'] = .01
                    self.assertEqual(assess(c)['verdict'], 'negative')

    def test_unrelated_five_pixel_and_calibrated_diagnostics_do_not_trigger_stop(self):
        c = self.valid()
        for stage in ('surface', 'final_dots'):
            row = c['registry'][stage]['comparisons'][0]
            row['literal_5px_calibration_lattice_overlap'] = .99
            row['null_calibrated_excess_overlap'] = .99
        self.assertEqual(assess(c)['verdict'], 'promote')
        self.assertFalse(assess(c)['ok_to_submit'])

    def test_ambiguous_calibrated_primary_rule_is_not_literal(self):
        c = self.valid(); c['registry']['duplicate_rule'] = 'null-calibrated overlap'
        self.assertEqual(assess(c)['verdict'], 'negative')

    def test_cannot_disguise_literal_value_as_excess(self):
        c = self.valid()
        row = c['registry']['final_dots']['comparisons'][0]
        row['overlap_3px'] = .2
        row['literal_overlap_3px'] = .99
        c['registry']['final_dots']['max_overlap_3px'] = .25
        self.assertEqual(assess(c)['verdict'], 'negative')
        c = self.valid(); c['registry']['max_literal_overlap_3px'] = .71
        self.assertEqual(assess(c)['verdict'], 'negative')

    def test_surface_support_and_its_definition_required(self):
        for key, value in [('support_count', 0), ('support_count', None),
                           ('support_definition', ''), ('overlap_metric', 'null-calibrated'),
                           ('complete', False)]:
            with self.subTest(key=key):
                c = self.valid(); c['registry']['surface'][key] = value
                self.assertEqual(assess(c)['verdict'], 'negative')

    def test_rank_extrema_and_registry_inventory_cannot_be_forged(self):
        for key, value in [('abs_spearman', .900001), ('abs_spearman', -0.1),
                           ('abs_spearman', None), ('sha256', 'z' * 64)]:
            with self.subTest(key=key):
                c = self.valid(); c['registry']['surface']['comparisons'][0][key] = value
                self.assertEqual(assess(c)['verdict'], 'negative')
        c = self.valid(); c['registry']['inventory_sha256'].append('b' * 64)
        self.assertEqual(assess(c)['verdict'], 'negative')
        c = self.valid(); c['registry']['final_dots']['max_overlap_3px'] = .69
        self.assertEqual(assess(c)['verdict'], 'negative')

    def test_card_must_have_holdout_canaries_and_saved_byte_checks(self):
        mutations = [
            lambda c: c['holdout'].update(dti=.5),  # estimate outside its claimed CI
            lambda c: c['holdout'].update(paired_delta_ci95=[-.001, .02]),
            lambda c: c['holdout'].update(same_evaluator_current_best=False),
            lambda c: c['holdout'].update(current_best_dti=.21),
            lambda c: c['holdout'].update(buffer_m=0),
            lambda c: c['holdout'].update(withheld_unit='component'),
            lambda c: c['holdout'].update(predictions_fold_local=False),
            lambda c: c['holdout'].update(visible_faults_masked_pixel_exactly=False),
            lambda c: c['holdout'].update(alpha=.8),
            lambda c: c.update(feature_auc=[.91, .5]),
            lambda c: c.update(feature_auc=[.09, .5]),
            lambda c: c.update(feature_auc=[.5]),
            lambda c: c.update(feature_names=['reused', 'reused']),
            lambda c: c.update(experiments_run=4),
            lambda c: c.update(elapsed_seconds=7201),
            lambda c: c['registry']['surface'].update(support_sha256=None),
            lambda c: c['registry']['final_dots'].update(candidate_raster_sha256='a' * 64),
            lambda c: c['registry'].update(inventory_sha256=['b' * 64]),
            lambda c: c['validator'].update(outside_null_or_nan=False),
            lambda c: c['validator'].update(raster_sha256='a' * 64),
            lambda c: c.update(note='x' * 141),
            lambda c: c.update(release_review={'reason': 'superseded'}),
        ]
        for mutate in mutations:
            c = self.valid(); mutate(c)
            self.assertEqual(assess(c)['verdict'], 'negative')

    def test_historical_k3c_is_negative_despite_former_promote(self):
        card = json.loads((ROOT / 'evidence/k3c_run_card.json').read_text())
        self.assertEqual(card['verdict'], 'promote')  # original retained unmodified
        result = assess(card)
        self.assertEqual(result['verdict'], 'negative')
        self.assertFalse(result['ok_to_submit'])
        self.assertTrue(any('literal' in r for r in result['reasons']))

    def test_missing(self): self.assertEqual(assess({})['verdict'],'negative')
    def test_valid_screen_still_requires_independent_selector(self):
        c=self.valid(); c['selector_approval']=True; c['ok_to_submit']=True
        r=assess(c)
        self.assertEqual(r['verdict'],'promote')
        self.assertTrue(r['technically_eligible'])
        self.assertFalse(r['ok_to_submit'])
        self.assertFalse(r['selector_approval'])
        self.assertFalse(r['slot_used'])
        self.assertTrue(r['selector_required'])
    def test_negative_never_ok_to_submit(self):
        c=self.valid(); c['holdout']['paired_delta_ci95']=[-.01,.02]
        r=assess(c); self.assertEqual(r['verdict'],'negative'); self.assertFalse(r['ok_to_submit'])
    def test_incomplete_protocol_or_defective_shared_implementation_stops(self):
        for key in ('whole_fault_segments', 'truth_visible_buffer', 'visible_only_catalogue_features',
                    'visible_pixels_masked_exactly', 'zero_truth_false_positives_conserved'):
            c=self.valid(); c['holdout']['protocol_audit'][key]=False
            self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); c['holdout']['holdout_implementation_sha256']='9ce9cf359f4d7b7fa844dd8f208ec00c3e6c15afef5d724d9014320b944d318d'
        c['holdout']['current_best']['holdout_implementation_sha256']=c['holdout']['holdout_implementation_sha256']
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_baseline_must_be_evidenced_on_the_same_folds(self):
        c=self.valid(); c['holdout']['current_best']['fold_assignment_sha256']='9'*64
        self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); c['holdout']['current_best']['dti']=.21
        self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); del c['holdout']['current_best']
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_mask_and_external_sidecars_are_not_optional(self):
        for key in ('geotiff','dtype_float32','inside_unmasked','self_contained_tiff','outside_policy_checked'):
            c=self.valid(); c['validator'][key]=False
            self.assertEqual(assess(c)['verdict'],'negative')
    def test_null_calibration_never_overrides_literal_failure(self):
        c = self.valid()
        c['registry']['literal_all_rasters_final_passed'] = False
        c['registry']['null_calibrated_all_rasters_final_passed'] = True
        c['registry']['duplicate_rule'] = 'null-calibrated'
        c['registry']['final_dots']['max_literal_overlap_3px'] = .9936
        self.assertEqual(assess(c)['verdict'], 'negative')

    def test_literal_overlap_node_rejected_even_with_calibration(self):
        c = self.valid()
        c['evidence'] = {'within_3px_fraction': .9936, 'p0': .9987, 'excess_overlap_3px': 0}
        self.assertEqual(assess(c)['verdict'], 'negative')

    def test_calibrated_rows_require_literal_values(self):
        c = self.valid()
        c['registry']['duplicate_rule'] = 'null-calibrated'
        self.assertEqual(assess(c)['verdict'], 'negative')
        c['registry']['duplicate_rule'] = 'literal-directional-fraction-within-3px'
        for stage in ('surface', 'final_dots'):
            c['registry'][stage]['comparisons'][0]['literal_overlap_3px'] = .7
        self.assertEqual(assess(c)['verdict'], 'promote')
        c['registry']['surface']['comparisons'][0]['literal_overlap_3px'] = .70001
        self.assertEqual(assess(c)['verdict'], 'negative')

    def test_duplicate(self):
        c=self.valid(); c['registry']['final_dots']['max_overlap_3px']=.70001
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_surface_overlap_and_manifest_required(self):
        c=self.valid(); c['registry']['surface']['comparisons'][0]['overlap_3px']=.70001
        self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); del c['registry']['surface']['comparisons'][0]['overlap_3px']
        self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); del c['registry']['manifest_sha256']
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_boundaries_at_both_stages(self):
        self.assertEqual(assess(self.valid())['verdict'],'promote')
        for stage in ('surface', 'final_dots'):
            c=self.valid(); c['registry'][stage]['comparisons'][0]['abs_spearman']=.90001
            self.assertEqual(assess(c)['verdict'],'negative')
    def test_legacy_excluded_rasters_stop(self):
        c=self.valid(); c['correlation_and_overlap_vs_registry']={'literal_all_rasters_final_passed':False}
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_literal_required(self):
        c=self.valid(); del c['registry']['literal_all_rasters_final_passed']
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_malformed(self):
        self.assertEqual(assess({'holdout': [], 'registry': [], 'validator': []})['verdict'],'negative')
        self.assertEqual(assess([])['verdict'],'negative')
    def test_missing_reference_and_wrong_hash(self):
        c=self.valid(); c['registry']['inventory_sha256'].append('c'*64)
        self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); c['validator']['raster_sha256']='c'*64
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_unhashable_registry_id_fails_closed(self):
        c=self.valid(); c['registry']['surface']['comparisons'][0]['sha256']=[]
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_literal_failure_overrides_filtered_pass(self):
        c=self.valid()
        c['correlation_and_overlap_vs_registry']={'literal_all_rasters_final_passed':False}
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_dense_lattice_is_not_exempt(self):
        c=self.valid()
        c['evidence']={'is_calibration_lattice':True,'within_3px_fraction':.996866}
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_ci_must_contain_estimate(self):
        c=self.valid(); c['holdout']['ci95']=[.3,.4]
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_nan(self):
        c=self.valid(); c['feature_auc']=[float('nan'), .5]
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_whole_array_finite_range_is_required(self):
        for value in (None, False):
            c=self.valid(); c['validator']['whole_array_finite_range']=value
            self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); del c['validator']['whole_array_finite_range']
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_wrong_grid(self):
        c=self.valid(); c['validator']['transform_match']=False
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_missing_ci(self):
        c=self.valid(); c['holdout']['paired_delta_ci95']=[-.01,.02]
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_point_outside_ci_rejected(self):
        c=self.valid(); c['holdout']['dti']=.9
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_reverse_label_leakage_rejected(self):
        c=self.valid(); c['feature_auc']=[.05, .5]
        self.assertEqual(assess(c)['verdict'],'negative')

    def test_ci_must_contain_point(self):
        c=self.valid(); c['holdout']['ci95']=[.01,.1]
        self.assertEqual(assess(c)['verdict'],'negative')

    def test_reverse_discriminator_is_also_a_canary(self):
        c=self.valid(); c['feature_auc']=[.05, .5]
        self.assertEqual(assess(c)['verdict'],'negative')

    def test_superseded_card_cannot_promote(self):
        c=self.valid(); c['release_review']={'reason':'literal registry failure'}
        self.assertEqual(assess(c)['verdict'],'negative')


if __name__ == '__main__':
    unittest.main()
