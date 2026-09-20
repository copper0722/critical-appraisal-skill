"""Source-derived algorithm examples, boundary counterexamples, and identity gates.

These are developer fixtures, not study-level appraisal calibration or human gold.
The independent manual review must separately check algorithm fidelity.
"""
import copy
import hashlib
import itertools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rob2
from rob2 import LOW, SOME, HIGH, propose_domain, overall, assess


class Rob2Algorithms(unittest.TestCase):
    def check(self, domain, answers, expected, **kwargs):
        if domain == 'D2':
            kwargs.setdefault('effect_of_interest', 'assignment')
        r = propose_domain(domain, answers, **kwargs)
        self.assertEqual(r['status'], 'PROPOSED')
        self.assertEqual(r['proposed_judgement'], expected)
        self.assertFalse(r['claim_use_allowed'])
        return r

    def test_randomization_ni_is_question_specific(self):
        self.check('D1', {'1.1': 'NI', '1.2': 'Y', '1.3': 'NI'}, LOW)
        self.check('D1', {'1.1': 'Y', '1.2': 'NI', '1.3': 'NI'}, SOME)
        self.check('D1', {'1.1': 'Y', '1.2': 'NI', '1.3': 'Y'}, HIGH)
        self.check('D1', {'1.1': 'N', '1.2': 'Y', '1.3': 'N'}, SOME)
        self.check('D1', {'1.1': 'Y', '1.2': 'Y', '1.3': 'Y'}, SOME)
        self.check('D1', {'1.1': 'Y', '1.2': 'N', '1.3': 'N'}, HIGH)

    def test_assignment_blinding_does_not_rescue_wrong_analysis(self):
        blinded = {'2.1': 'N', '2.2': 'PN', '2.6': 'Y'}
        self.check('D2', blinded, LOW)
        self.check('D2', {**blinded, '2.6': 'N', '2.7': 'NI'}, HIGH)
        self.check('D2', {**blinded, '2.6': 'N', '2.7': 'N'}, SOME)

    def test_assignment_deviation_branches_and_two_part_combination(self):
        base = {'2.1': 'Y', '2.2': 'N', '2.6': 'Y'}
        self.check('D2', {**base, '2.3': 'N'}, LOW)
        self.check('D2', {**base, '2.3': 'NI'}, SOME)
        self.check('D2', {**base, '2.3': 'Y', '2.4': 'N'}, SOME)
        self.check('D2', {**base, '2.3': 'Y', '2.4': 'NI', '2.5': 'Y'}, SOME)
        self.check('D2', {**base, '2.3': 'Y', '2.4': 'NI', '2.5': 'NI'}, HIGH)
        r = self.check('D2', {**base, '2.3': 'N', '2.6': 'NI', '2.7': 'N'}, SOME)
        self.assertEqual(r['subproposals'], {'deviations': LOW, 'analysis': SOME})

    def test_adhering_selected_types_and_inclusive_deviations(self):
        kw = {'effect_of_interest': 'adhering', 'deviation_types': ['implementation_failures', 'participant_non_adherence']}
        base = {'2.1': 'N', '2.2': 'N', '2.4': 'N', '2.5': 'N'}
        self.check('D2', base, LOW, **kw)
        for failure, adherence in [('Y', 'N'), ('N', 'NI'), ('Y', 'NI')]:
            for analysis, expected in [('Y', SOME), ('NI', HIGH)]:
                self.check('D2', {**base, '2.4': failure, '2.5': adherence, '2.6': analysis}, expected, **kw)

    def test_adhering_balance_has_opposite_polarity_from_assignment_deviation(self):
        kw = {'effect_of_interest': 'adhering', 'deviation_types': ['non_protocol_interventions']}
        base = {'2.1': 'Y', '2.2': 'NI'}
        self.check('D2', {**base, '2.3': 'Y'}, LOW, **kw)
        self.check('D2', {**base, '2.3': 'NI', '2.6': 'Y'}, SOME, **kw)
        self.check('D2', {'2.1': 'N', '2.2': 'N'}, LOW, **kw)
        with self.assertRaises(ValueError):
            propose_domain('D2', {**base, '2.3': 'Y'}, effect_of_interest='adhering')

    def test_missing_data_no_automatic_percentage_rule_or_ni_coercion(self):
        self.check('D3', {'3.1': 'Y'}, LOW)
        self.check('D3', {'3.1': 'NI', '3.2': 'Y'}, LOW)
        self.check('D3', {'3.1': 'N', '3.2': 'N', '3.3': 'N'}, LOW)
        self.check('D3', {'3.1': 'N', '3.2': 'N', '3.3': 'NI', '3.4': 'N'}, SOME)
        self.check('D3', {'3.1': 'N', '3.2': 'N', '3.3': 'NI', '3.4': 'NI'}, HIGH)
        with self.assertRaisesRegex(ValueError, '3.2'):
            propose_domain('D3', {'3.1': 'N', '3.2': 'NI'})
        r = propose_domain('D3', {'3.1': 'N', '3.2': 'NO_INFORMATION'})
        self.assertEqual((r['status'], r['unresolved_question']), ('HOLD', '3.2'))

    def test_measurement_ni_floor_and_later_high(self):
        self.check('D4', {'4.1': 'NI', '4.2': 'N', '4.3': 'N'}, LOW)
        self.check('D4', {'4.1': 'N', '4.2': 'NI', '4.3': 'N'}, SOME)
        for differs, expected in [('N', LOW), ('NI', SOME)]:
            self.check('D4', {'4.1': 'N', '4.2': differs, '4.3': 'Y', '4.4': 'N'}, expected)
        for differs in ['N', 'NI']:
            self.check('D4', {'4.1': 'N', '4.2': differs, '4.3': 'NI', '4.4': 'NI', '4.5': 'N'}, SOME)
            self.check('D4', {'4.1': 'N', '4.2': differs, '4.3': 'NI', '4.4': 'NI', '4.5': 'NI'}, HIGH)
        self.check('D4', {'4.1': 'Y', '4.2': 'NI'}, HIGH)
        self.check('D4', {'4.1': 'N', '4.2': 'Y'}, HIGH)

    def test_selection_one_ni_suffices_for_some_concerns(self):
        for a, b in [('NI', 'N'), ('N', 'NI'), ('NI', 'NI')]:
            self.check('D5', {'5.1': 'Y', '5.2': a, '5.3': b}, SOME)
        self.check('D5', {'5.1': 'Y', '5.2': 'N', '5.3': 'N'}, LOW)
        self.check('D5', {'5.1': 'NI', '5.2': 'N', '5.3': 'N'}, SOME)
        self.check('D5', {'5.1': 'Y', '5.2': 'NI', '5.3': 'PY'}, HIGH)

    def test_probable_answers_same_algorithm_not_same_evidence_strength(self):
        # Exhaust all D1/D5 yes/no/NI combinations; preserve original trace tokens.
        for domain in ['D1', 'D5']:
            for values in itertools.product(('Y', 'N', 'NI'), repeat=3):
                a = {f'{domain[1]}.{i}': v for i, v in enumerate(values, 1)}
                b = {k: {'Y': 'PY', 'N': 'PN'}.get(v, v) for k, v in a.items()}
                x, y = propose_domain(domain, a), propose_domain(domain, b)
                self.assertEqual(x['proposed_judgement'], y['proposed_judgement'])
                self.assertEqual([z['response'] for z in y['trace']], list(b.values()))

    def test_wrong_branch_na_missing_and_technical_abstention(self):
        with self.assertRaisesRegex(ValueError, 'explicit effect'):
            propose_domain('D2', {'2.1': 'N', '2.2': 'N', '2.6': 'Y'})
        for bad in [{'3.1': 'NA'}, {'3.1': 'Y', '3.2': 'Y'}, {'3.1': 'maybe'}, {'3.1': True}, {'8.1': 'Y'}]:
            with self.assertRaises(ValueError):
                propose_domain('D3', bad)
        for unknown in [{}, {'3.1': 'NO_INFORMATION'}]:
            r = propose_domain('D3', unknown)
            self.assertEqual(r['status'], 'HOLD')
            self.assertIsNone(r['proposed_judgement'])

    def test_overall_qualitative_joint_concerns_not_numeric_score(self):
        a = dict.fromkeys(rob2.DOMAINS, LOW)
        self.assertEqual(overall(a)['proposed_judgement'], LOW)
        a['D1'] = SOME
        self.assertEqual(overall(a)['proposed_judgement'], SOME)
        a['D2'] = SOME
        self.assertEqual(overall(a)['status'], 'HOLD')
        for decision, expected in [(True, HIGH), (False, SOME)]:
            r = overall(a, {'substantially_lowers_confidence': decision, 'reason': 'fixture judgement', 'reviewer': 'fixture reviewer'})
            self.assertEqual(r['proposed_judgement'], expected)
            self.assertIsNone(r['numeric_score'])
        a['D5'] = HIGH
        self.assertEqual(overall(a)['proposed_judgement'], HIGH)
        with self.assertRaises(ValueError):
            overall({k: v for k, v in a.items() if k != 'D4'})


class Rob2Bindings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manual = Path(self.tmp.name) / 'synthetic-manual.txt'
        self.manual.write_text('Synthetic binding fixture; not an official source.')
        sha = hashlib.sha256(self.manual.read_bytes()).hexdigest()
        self.patch = patch.object(rob2, 'MANUAL_SHA256', sha)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        answers = {'D1': {'1.1': 'Y', '1.2': 'Y', '1.3': 'N'},
                   'D2': {'2.1': 'N', '2.2': 'N', '2.6': 'Y'},
                   'D3': {'3.1': 'Y'}, 'D4': {'4.1': 'N', '4.2': 'N', '4.3': 'N'},
                   'D5': {'5.1': 'Y', '5.2': 'N', '5.3': 'N'}}
        self.packet = {'schema': 'rob2-assessment/v1',
                       'method': {'id': 'rob2-parallel', 'version': rob2.VERSION, 'manual_sha256': sha, 'scope_verified': True},
                       'assessment_unit': dict(study_id='fixture', experimental='A', comparator='B', outcome='O', timepoint='T', result_id='R', design='individually_randomized_parallel', effect_of_interest='assignment'),
                       'sources': [{'id': 'trial', 'sha256': 'a' * 64}], 'domains': {}}
        for d, a in answers.items():
            self.packet['domains'][d] = {'answers': a, 'support': {q: {'reason': 'synthetic fixture reason', 'source_ids': ['trial'], 'locator': 'fixture paragraph1'} for q in a}}
        self.packet['domains']['D2']['effect_of_interest'] = 'assignment'

    def test_full_bound_proposal_is_not_semantic_acceptance(self):
        r = assess(self.packet, self.manual)
        self.assertEqual(r['overall']['proposed_judgement'], LOW)
        self.assertFalse(r['semantic_acceptance'])
        self.assertFalse(r['claim_use_allowed'])

    def test_manual_source_result_and_branch_identity(self):
        edits = [('method', 'version', '2021'), ('method', 'manual_sha256', 'b' * 64),
                 ('method', 'scope_verified', False), ('assessment_unit', 'design', 'cluster_randomized'),
                 ('assessment_unit', 'result_id', ''), ('assessment_unit', 'effect_of_interest', None)]
        for group, key, value in edits:
            bad = copy.deepcopy(self.packet); bad[group][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                assess(bad, self.manual)
        bad = copy.deepcopy(self.packet); bad['domains']['D2']['effect_of_interest'] = 'adhering'
        with self.assertRaisesRegex(ValueError, 'D2 branch'):
            assess(bad, self.manual)
        # A file cannot authenticate itself merely by reporting its own hash.
        with patch.object(rob2, 'MANUAL_SHA256', 'c' * 64), self.assertRaises(ValueError):
            assess(self.packet, self.manual)

    def test_no_silent_override_or_unbound_support(self):
        entry = self.packet['domains']['D1']
        entry['override'] = {'judgement': HIGH}
        with self.assertRaises(ValueError):
            assess(self.packet, self.manual)
        entry['override'].update(reviewer='fixture', reason='independent contextual judgement')
        r = assess(self.packet, self.manual)
        self.assertEqual(r['domains']['D1']['proposed_judgement'], LOW)
        self.assertEqual(r['domains']['D1']['override']['judgement'], HIGH)
        self.assertEqual(r['overall']['proposed_judgement'], HIGH)
        entry['support']['1.1']['source_ids'] = ['not-in-packet']
        with self.assertRaises(ValueError):
            assess(self.packet, self.manual)

    def test_unresolved_domain_preserved_and_prevents_overall(self):
        self.packet['domains']['D3']['answers'] = {'3.1': 'NO_INFORMATION'}
        r = assess(self.packet, self.manual)
        self.assertEqual(r['status'], 'HOLD')
        self.assertIsNone(r['overall']['proposed_judgement'])
        self.assertEqual(r['domains']['D1']['status'], 'PROPOSED')
        self.assertEqual(r['domains']['D3']['unresolved_question'], '3.1')


if __name__ == '__main__':
    unittest.main()
