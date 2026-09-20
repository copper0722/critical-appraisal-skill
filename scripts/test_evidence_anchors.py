import hashlib
import unittest

from evidence_anchors import locate


class EvidenceAnchorTests(unittest.TestCase):
    def test_unique_quote_has_exact_offsets_and_source_identity(self):
        text='Methods. The reviewers were blinded to each other. Results.'
        quote='The reviewers were blinded to each other.'
        result=locate(text,quote)
        self.assertEqual(result['status'],'LOCATED')
        anchor=result['matches'][0]
        self.assertEqual(text[anchor['start']:anchor['end']],quote)
        self.assertEqual(result['source_sha256'],hashlib.sha256(text.encode()).hexdigest())
        self.assertFalse(result['semantic_acceptance']);self.assertFalse(result['claim_use_allowed'])

    def test_whitespace_only_returns_original_source_bytes_not_a_rewritten_quote(self):
        text='Intro.\nAn average\n measure\t ICC was used.\nEnd.'
        quote='An average measure ICC was used.'
        self.assertEqual(locate(text,quote)['status'],'NOT_FOUND')
        result=locate(text,quote,normalization='whitespace')
        self.assertEqual(result['status'],'LOCATED')
        self.assertEqual(result['matches'][0]['quote'],'An average\n measure\t ICC was used.')

    def test_no_fuzzy_negation_number_or_role_repair(self):
        text='The trial was not randomized. Two assessors scored 0.77.'
        for quote in ('The trial was randomized.','Two participants scored 0.77.','Two assessors scored 0.78.'):
            self.assertEqual(locate(text,quote,normalization='whitespace')['status'],'NOT_FOUND')

    def test_repeated_quote_is_not_silently_assigned_to_the_first_occurrence(self):
        result=locate('Abstract: The study ended. Methods: The study ended.','The study ended.')
        self.assertEqual(result['status'],'AMBIGUOUS');self.assertEqual(len(result['matches']),2)

    def test_literal_match_is_not_entailment_and_keeps_negating_context(self):
        result=locate('The participants were not blinded.','blinded')
        self.assertEqual(result['status'],'LOCATED')
        self.assertIn('not blinded',result['matches'][0]['context'])
        self.assertFalse(result['claim_use_allowed'])

    def test_unicode_offsets_and_source_changes_are_not_hidden(self):
        text='前文。不是隨機分派。後文。'
        result=locate(text,'不是隨機分派。')
        a=result['matches'][0];self.assertEqual(text[a['start']:a['end']],a['quote'])
        with self.assertRaises(ValueError):locate(text+'changed',a['quote'],expected_source_sha256=result['source_sha256'])

    def test_blank_quote_cannot_pass_as_source_evidence(self):
        for q in ('','  ','\n'):
            with self.assertRaises(ValueError):locate('source',q)


if __name__=='__main__':unittest.main()
