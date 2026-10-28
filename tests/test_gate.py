import unittest
from scripts.promotion_gate import assess
class GateTests(unittest.TestCase):
    def valid(self):
        return dict(assigned_lane='test',holdout=dict(evidence_class='HOLDOUT-DTI',evaluator_version='test-v1',withheld_positives=1,dti=.2,ci95=[.1,.3],paired_delta_ci95=[.01,.02],same_evaluator_current_best=True),feature_auc=[.6],registry={**{s:dict(complete=True,max_abs_spearman=.9,max_overlap_3px=.7, comparisons=[dict(sha256='b'*64,abs_spearman=.9,overlap_3px=.7)]) for s in ['surface','final_dots']}, 'inventory_sha256':['b'*64], 'manifest_sha256':'d'*64, 'literal_all_rasters_final_passed':True},validator={**{k:True for k in ['saved_bytes_checked','single_band','finite_inside','range_0_1','whole_array_finite_range','crs_match','shape_match','transform_match']}, 'raster_sha256':'a'*64},raster_sha256='a'*64,submission_name='test',note='test only')
    def test_missing(self): self.assertEqual(assess({})['verdict'],'negative')
    def test_valid_promotes_and_clears_for_selector(self):
        r=assess(self.valid()); self.assertEqual(r['verdict'],'promote'); self.assertTrue(r['ok_to_submit']); self.assertTrue(r['selector_required'])
    def test_negative_never_ok_to_submit(self):
        c=self.valid(); c['holdout']['paired_delta_ci95']=[-.01,.02]
        r=assess(c); self.assertEqual(r['verdict'],'negative'); self.assertFalse(r['ok_to_submit'])
    def test_null_calibrated_rule_v3(self):
        # v3: literal failure vs a space-filling lattice is allowed only with the null-calibrated audit declared
        c=self.valid(); c['registry']['literal_all_rasters_final_passed']=False
        self.assertEqual(assess(c)['verdict'],'negative')            # legacy card: literal rule binds
        c['registry']['null_calibrated_all_rasters_final_passed']=True
        c['registry']['duplicate_rule']='null-calibrated excess overlap (obs-p0)/(1-p0) <= 0.70'
        self.assertEqual(assess(c)['verdict'],'negative')            # literal failure must be disclosed
        c['registry']['final_dots']['max_literal_overlap_3px']=.9936
        self.assertEqual(assess(c)['verdict'],'promote')
        c['registry']['null_calibrated_all_rasters_final_passed']=False
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_literal_over70_node_needs_p0_and_excess(self):
        c=self.valid(); c['registry']['literal_all_rasters_final_passed']=True
        c['evidence']={'within_3px_fraction':.9936,'footprint_3px_coverage_p0':.9987,'null_calibrated_excess_overlap':0.0}
        self.assertEqual(assess(c)['verdict'],'promote')
        c['evidence']={'within_3px_fraction':.9936,'footprint_3px_coverage_p0':.5,'null_calibrated_excess_overlap':.98}
        self.assertEqual(assess(c)['verdict'],'negative')
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
