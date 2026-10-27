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

class RegressionTests(GateTests):
    def test_malformed_sections_fail_closed(self):
        for field in ('holdout', 'registry', 'validator'):
            for value in (True, 42, 'bad', []):
                with self.subTest(field=field, value=value):
                    card=self.valid(); card[field]=value
                    self.assertEqual(assess(card)['verdict'], 'negative')
    def test_non_object_card(self):
        for value in ([], None, 'bad', 1):
            self.assertEqual(assess(value)['verdict'], 'negative')
    def test_estimate_outside_ci(self):
        card=self.valid(); card['holdout']['ci95']=[.3,.4]
        self.assertEqual(assess(card)['verdict'], 'negative')
    def test_impossible_delta(self):
        card=self.valid(); card['holdout']['paired_delta_ci95']=[.1,2]
        self.assertEqual(assess(card)['verdict'], 'negative')
    def test_whitespace_lane(self):
        card=self.valid(); card['assigned_lane']='  '
        self.assertEqual(assess(card)['verdict'], 'negative')
