import copy
import unittest
from compare_models import compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.case = {'id':'case1','source_package_sha256':'a'*64,'method_sha256':'b'*64,
                     'assessment_unit':'result1','route':'synthetic',
                     'questions':{'q1':{'allowed_answers':['YES','NO','NO_INFORMATION'], 'weight':2},
                                  'q2':{'allowed_answers':['YES','NO','NO_INFORMATION'], 'weight':1}}}
        self.protocol={'id':'fixed1','split':'development','cases':[self.case]}
        row={k:v for k,v in self.case.items() if k!='questions'}
        row.update(status='complete', answers={'q1':'YES','q2':'NO_INFORMATION'})
        self.small={'protocol_id':'fixed1','model_id':'small','run_id':'s1',
                    'raw_output_sha256':'c'*64,'cases':[row]}
        self.large=copy.deepcopy(self.small);self.large.update(model_id='high',run_id='h1')

    def test_matching_is_not_truth(self):
        r=compare(self.protocol,self.small,self.large)
        self.assertEqual(r['agreement_over_planned'],1)
        self.assertFalse(r['equivalence_established'])

    def test_missing_answers_stay_in_denominator(self):
        del self.small['cases'][0]['answers']['q2']
        r=compare(self.protocol,self.small,self.large)
        self.assertEqual(r['planned_questions'],2)
        self.assertEqual(r['agreement_over_planned'],0.5)
        self.assertEqual(r['agreement_over_paired'],1)
        self.assertEqual(r['weighted_agreement_over_planned'],2/3)

    def test_absent_failed_and_abstained_cases(self):
        for status in ['failed','abstained']:
            self.small['cases'][0]['status']=status
            self.assertEqual(compare(self.protocol,self.small,self.large)['paired_questions'],0)
        self.small['cases']=[]
        self.assertEqual(compare(self.protocol,self.small,self.large)['missing_or_failed_questions'],2)

    def test_wrong_identity_and_duplicate_refused(self):
        for key in ['source_package_sha256','method_sha256','assessment_unit','route']:
            run=copy.deepcopy(self.small);run['cases'][0][key]='wrong'
            with self.assertRaises(ValueError):compare(self.protocol,run,self.large)
        run=copy.deepcopy(self.small);run['cases']*=2
        with self.assertRaises(ValueError):compare(self.protocol,run,self.large)

    def test_same_model_and_unplanned_answer_refused(self):
        run=copy.deepcopy(self.large);run['model_id']='small'
        with self.assertRaises(ValueError):compare(self.protocol,self.small,run)
        run=copy.deepcopy(self.small);run['cases'][0]['answers']['extra']='YES'
        with self.assertRaises(ValueError):compare(self.protocol,run,self.large)

    def test_invalid_weight_refused(self):
        for weight in [True, '1', 0, -1, float('inf'), float('nan')]:
            self.case['questions']['q1']['weight']=weight
            with self.assertRaises(ValueError):compare(self.protocol,self.small,self.large)


if __name__=='__main__':unittest.main()
