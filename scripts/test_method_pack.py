import unittest
from pathlib import Path
from method_pack import bind, summarize_scores


class MethodTests(unittest.TestCase):
    def setUp(self):
        self.path=Path(__file__).resolve().parents[1]/'references/sanra-2019.method.json'

    def test_scope_and_controller_verification(self):
        m=bind(self.path,'narrative_review')
        self.assertFalse(m['scope_verified'])
        self.assertEqual(m['coverage_policy'],'whole_document')
        self.assertEqual(len(m['domains']),6)
        for wrong in ['instrument_validation_study','systematic_review','primary_trial','guideline']:
            with self.assertRaisesRegex(ValueError,'METHOD_SCOPE_MISMATCH'):bind(self.path,wrong)

    def test_no_information_is_not_zero(self):
        answers={k:'2' for k in ['importance','aims','search','referencing','reasoning','data']}
        self.assertEqual(summarize_scores(answers)['sum_score'],12)
        answers['search']='NO_INFORMATION'
        self.assertIsNone(summarize_scores(answers)['sum_score'])
        answers['search']='0'
        r=summarize_scores(answers)
        self.assertEqual(r['sum_score'],10)
        self.assertIsNone(r['quality_category'])
        self.assertFalse(r['claim_use_allowed'])

    def test_missing_and_invalid_items(self):
        with self.assertRaises(ValueError):summarize_scores({'search':'0'})
        answers={k:'2' for k in ['importance','aims','search','referencing','reasoning','data']}
        answers['search']=0
        with self.assertRaises(ValueError):summarize_scores(answers)


if __name__=='__main__':unittest.main()
