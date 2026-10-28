import unittest
from scripts.promotion_gate import assess
class GateTests(unittest.TestCase):
    def valid(self):
        # Fully synthetic evidence exercises the screen, not a real evaluation.
        shared = dict(evaluator_version='test-v1', evaluator_sha256='e'*64,
                      holdout_implementation_sha256='c'*64, fold_assignment_sha256='f'*64,
                      withheld_positives=1)
        baseline = dict(evidence_class='HOLDOUT-DTI', **shared, dti=.18, ci95=[.1,.2])
        holdout = dict(evidence_class='HOLDOUT-DTI', **shared, shared_template_commit='1'*40,
                       dti=.2, ci95=[.1,.3], paired_delta_ci95=[.01,.02],
                       same_evaluator_current_best=True, current_best=baseline,
                       protocol_audit={**{k: True for k in ('whole_fault_segments', 'truth_visible_buffer',
                           'visible_only_catalogue_features', 'visible_pixels_masked_exactly',
                           'zero_truth_false_positives_conserved')}, 'report_sha256':'2'*64})
        stages = {s:dict(complete=True,max_abs_spearman=.9,max_overlap_3px=.7,
                         comparisons=[dict(sha256='b'*64,abs_spearman=.9,overlap_3px=.7)])
                  for s in ('surface','final_dots')}
        registry = {**stages, 'inventory_sha256':['b'*64], 'manifest_sha256':'d'*64,
                    'literal_all_rasters_final_passed':True}
        validator = {**{k:True for k in ('saved_bytes_checked','geotiff','single_band','float32','finite_inside','inside_unmasked',
                        'self_contained_tiff','range_0_1','whole_array_finite_range','outside_policy_checked',
                        'crs_match','shape_match','transform_match')}, 'raster_sha256':'a'*64}
        return dict(assigned_lane='test', mechanism='test mechanism', named_non_fault_mimic='test mimic',
                    holdout=holdout, feature_auc=[.6], registry=registry, validator=validator,
                    raster_sha256='a'*64, submission_name='test', note='test only')
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
        for key in ('geotiff','float32','inside_unmasked','self_contained_tiff','outside_policy_checked'):
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
        c=self.valid(); c['feature_auc']=[float('nan')]
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
        c=self.valid(); c['feature_auc']=[.05]
        self.assertEqual(assess(c)['verdict'],'negative')
if __name__=='__main__': unittest.main()

class GateRegressionTests(GateTests):
    def test_ci_must_contain_point(self):
        c=self.valid(); c['holdout']['ci95']=[.01,.1]
        self.assertEqual(assess(c)['verdict'],'negative')

    def test_reverse_discriminator_is_also_a_canary(self):
        c=self.valid(); c['feature_auc']=[.05]
        self.assertEqual(assess(c)['verdict'],'negative')

    def test_superseded_card_cannot_promote(self):
        c=self.valid(); c['release_review']={'reason':'literal registry failure'}
        self.assertEqual(assess(c)['verdict'],'negative')
