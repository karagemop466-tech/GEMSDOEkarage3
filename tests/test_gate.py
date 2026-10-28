import json
from pathlib import Path
import unittest
from scripts.promotion_gate import assess

class GateTests(unittest.TestCase):
    def valid(self):
        sha = 'a' * 64
        reference = 'b' * 64
        stage = lambda: dict(complete=True, comparisons=[dict(sha256=reference, abs_spearman=.9, overlap_3px=.7)])
        return dict(assigned_lane='test', holdout=dict(evidence_class='HOLDOUT-DTI', evaluator_version='test-v1', withheld_positives=1, dti=.2, ci95=[.1,.3], paired_delta_ci95=[.01,.02], same_evaluator_current_best=True), feature_auc=[.6], registry=dict(manifest_sha256='c'*64, inventory=[reference], surface=stage(), final_dots=stage()), validator=dict(sha256=sha, **{k:True for k in ['saved_bytes_checked','single_band','finite_inside','range_0_1','crs_match','shape_match','transform_match']}), raster_sha256=sha, submission_name='test', note='test only')
    def test_missing(self): self.assertEqual(assess({})['verdict'], 'negative')
    def test_malformed_fails_closed(self):
        for c in [None, {'holdout': 7}, {'registry': {'inventory': [True]}}]: self.assertEqual(assess(c)['verdict'], 'negative')
    def test_valid_is_not_upload_authorization(self):
        r=assess(self.valid()); self.assertEqual(r['verdict'],'promote'); self.assertFalse(r['ok_to_submit'])
    def test_duplicate_and_missing_comparison(self):
        for stage in ['surface', 'final_dots']:
            c=self.valid(); c['registry'][stage]['comparisons'][0]['overlap_3px']=.70001
            self.assertEqual(assess(c)['verdict'],'negative')
            c=self.valid(); c['registry'][stage]['comparisons']=[]
            self.assertEqual(assess(c)['verdict'],'negative')
    def test_prior_filtered_card_does_not_pass(self):
        card=json.loads((Path(__file__).resolve().parents[1]/'evidence/hk3_smgc_run_card.json').read_text())
        self.assertEqual(assess(card)['verdict'], 'negative')
    def test_nan(self):
        c=self.valid(); c['feature_auc']=[float('nan')]; self.assertEqual(assess(c)['verdict'],'negative')
    def test_wrong_grid_or_hash(self):
        for field, val in [('transform_match',False), ('sha256','b'*64)]:
            c=self.valid(); c['validator'][field]=val; self.assertEqual(assess(c)['verdict'],'negative')
    def test_missing_or_invalid_ci(self):
        c=self.valid(); c['holdout']['paired_delta_ci95']=[-.01,.02]; self.assertEqual(assess(c)['verdict'],'negative')
        c=self.valid(); c['holdout']['ci95']=[.3,.4]; self.assertEqual(assess(c)['verdict'],'negative')
if __name__=='__main__': unittest.main()
