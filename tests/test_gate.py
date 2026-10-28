import unittest
from scripts.promotion_gate import assess
class GateTests(unittest.TestCase):
    def valid(self):
        return dict(assigned_lane='test',holdout=dict(evidence_class='HOLDOUT-DTI',evaluator_version='test-v1',withheld_positives=1,dti=.2,ci95=[.1,.3],paired_delta_ci95=[.01,.02],same_evaluator_current_best=True),feature_auc=[.6],registry={s:dict(complete=True,max_abs_spearman=.9,max_overlap_3px=.7) for s in ['surface','final_dots']},validator={k:True for k in ['saved_bytes_checked','single_band','finite_inside','range_0_1','crs_match','shape_match','transform_match']},raster_sha256='a'*64,submission_name='test',note='test only')
    def test_missing(self): self.assertEqual(assess({})['verdict'],'negative')
    def test_valid_is_not_upload_authorization(self):
        r=assess(self.valid()); self.assertEqual(r['verdict'],'promote'); self.assertFalse(r['ok_to_submit'])
    def test_duplicate(self):
        c=self.valid(); c['registry']['surface']['max_overlap_3px']=.70001
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_nan(self):
        c=self.valid(); c['feature_auc']=[float('nan')]
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_wrong_grid(self):
        c=self.valid(); c['validator']['transform_match']=False
        self.assertEqual(assess(c)['verdict'],'negative')
    def test_missing_ci(self):
        c=self.valid(); c['holdout']['paired_delta_ci95']=[-.01,.02]
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
