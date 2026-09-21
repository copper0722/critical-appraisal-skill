"""Synthetic developer fixtures (invented text, not human gold, not held out).

These test deterministic slot arithmetic with stubbed model output. They cannot
show that a slot is true; a mislabelled slot passes by design.
"""
import copy
import json
import unittest
from pathlib import Path

import awareness_facts as af

SCHEMA = {'version': 'awareness-fact/v1',
          'target': {'actor': 'nurses', 'phase': 'after_allocation', 'information': 'ASSIGNED_INTERVENTION_IDENTITY'},
          'actors': {'nurses': ['ward nurses'], 'pharmacy': ['dispensing unit'], 'participants': []},
          'phases': {'after_allocation': ['during the trial'], 'before_allocation': ['at enrolment']}}
VALUES = ['REPORTED_AWARE', 'REPORTED_UNAWARE', 'NO_INFORMATION']
SPANS = {'1': 'Nurses were told the active inhaler.', '2': 'Second span.'}


def fact(value, proposition, ids=('1',), **slots):
    base = {'source_span_ids': list(ids), 'statement_actor': 'nurses', 'phase': 'after_allocation',
            'information': 'ASSIGNED_INTERVENTION_IDENTITY', 'scope': 'REPORTED_CONDUCT',
            'proposition': proposition, 'rationale': 'Synthetic rationale.', 'fact_value': value}
    base.update(slots)
    return base


def check(answer, schema=SCHEMA):
    evidence, errors = af.check_answer(answer, schema, SPANS, 3)
    return errors, af.row_fields(answer, schema, errors), evidence


class DerivationPairs(unittest.TestCase):
    """Each pair varies one thing; the supported member must pass, the confusable must not."""

    def assertPass(self, answer, value, status):
        errors, fields, _ = check(answer)
        self.assertEqual(errors, [])
        self.assertEqual((fields['derived_fact_value'], fields['deterministic_status'], fields['fact_flags']),
                         (value, status, []))

    def assertFlagged(self, answer, flag):
        errors, fields, _ = check(answer)
        self.assertEqual(errors, [])
        self.assertEqual(fields['derived_fact_value'], 'NO_INFORMATION')
        self.assertEqual(fields['deterministic_status'], 'FLAGGED')
        self.assertIn(flag, fields['fact_flags'])

    def test_direct_knowledge_and_nonknowledge_derive_polarity(self):
        self.assertPass(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE'), 'REPORTED_AWARE', 'CONSISTENT_DIRECT')
        self.assertPass(fact('REPORTED_UNAWARE', 'DIRECT_IDENTITY_NONKNOWLEDGE'), 'REPORTED_UNAWARE', 'CONSISTENT_DIRECT')

    def test_access_ability_alone_is_not_actual_knowledge(self):
        aware = fact('REPORTED_AWARE', 'ALLOCATION_KEY_ACCESS_ONLY')
        self.assertEqual(check(aware)[0], ['VALUE_SLOT_CONFLICT'])
        self.assertFlagged(fact('NO_INFORMATION', 'ALLOCATION_KEY_ACCESS_ONLY'), 'NON_DIRECT_PROPOSITION')
        self.assertPass(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE'), 'REPORTED_AWARE', 'CONSISTENT_DIRECT')

    def test_disclosure_rule_alone_does_not_mean_unaware(self):
        self.assertEqual(check(fact('REPORTED_UNAWARE', 'NONDISCLOSURE_RULE_ONLY'))[0], ['VALUE_SLOT_CONFLICT'])
        self.assertFlagged(fact('NO_INFORMATION', 'NONDISCLOSURE_RULE_ONLY', statement_actor='pharmacy'),
                           'NON_DIRECT_PROPOSITION')
        # ...while an explicit statement about the same actor passes.
        self.assertPass(fact('REPORTED_UNAWARE', 'DIRECT_IDENTITY_NONKNOWLEDGE'), 'REPORTED_UNAWARE', 'CONSISTENT_DIRECT')

    def test_coded_label_only_versus_direct_nonknowledge_that_mentions_labels(self):
        self.assertEqual(check(fact('REPORTED_AWARE', 'CODED_LABEL_HANDLING_ONLY'))[0], ['VALUE_SLOT_CONFLICT'])
        self.assertFlagged(fact('NO_INFORMATION', 'CODED_LABEL_HANDLING_ONLY'), 'NON_DIRECT_PROPOSITION')
        self.assertPass(fact('REPORTED_UNAWARE', 'DIRECT_IDENTITY_NONKNOWLEDGE'), 'REPORTED_UNAWARE', 'CONSISTENT_DIRECT')

    def test_planned_versus_actual_conduct(self):
        self.assertFlagged(fact('NO_INFORMATION', 'DIRECT_IDENTITY_KNOWLEDGE', scope='PLANNED'), 'PLAN_ONLY')
        self.assertEqual(check(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE', scope='PLANNED'))[0],
                         ['VALUE_SLOT_CONFLICT'])
        self.assertFlagged(fact('NO_INFORMATION', 'DIRECT_IDENTITY_KNOWLEDGE', scope='NOT_STATED'), 'SCOPE_NOT_STATED')
        self.assertPass(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE'), 'REPORTED_AWARE', 'CONSISTENT_DIRECT')

    def test_same_words_wrong_actor_or_phase(self):
        for actor in ('pharmacy', 'OTHER_ACTOR', 'NOT_STATED'):
            self.assertFlagged(fact('NO_INFORMATION', 'DIRECT_IDENTITY_NONKNOWLEDGE', statement_actor=actor),
                               'ACTOR_MISMATCH')
        self.assertEqual(check(fact('REPORTED_UNAWARE', 'DIRECT_IDENTITY_NONKNOWLEDGE', statement_actor='pharmacy'))[0],
                         ['VALUE_SLOT_CONFLICT'])
        self.assertFlagged(fact('NO_INFORMATION', 'DIRECT_IDENTITY_KNOWLEDGE', phase='before_allocation'), 'PHASE_MISMATCH')
        self.assertPass(fact('REPORTED_UNAWARE', 'DIRECT_IDENTITY_NONKNOWLEDGE'), 'REPORTED_UNAWARE', 'CONSISTENT_DIRECT')

    def test_assigned_versus_received_identity_are_distinct(self):
        received = fact('NO_INFORMATION', 'DIRECT_IDENTITY_KNOWLEDGE', information='RECEIVED_INTERVENTION_IDENTITY')
        self.assertFlagged(received, 'INFORMATION_MISMATCH')
        target_received = copy.deepcopy(SCHEMA)
        target_received['target']['information'] = 'RECEIVED_INTERVENTION_IDENTITY'
        received['fact_value'] = 'REPORTED_AWARE'
        errors, fields, _ = check(received, target_received)
        self.assertEqual((errors, fields['deterministic_status']), ([], 'CONSISTENT_DIRECT'))
        self.assertEqual(check(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE'), target_received)[0],
                         ['VALUE_SLOT_CONFLICT'])

    def test_inference_stays_non_direct_and_is_not_method_ni(self):
        self.assertFlagged(fact('NO_INFORMATION', 'INFERENCE'), 'NON_DIRECT_PROPOSITION')
        self.assertEqual(check(fact('REPORTED_UNAWARE', 'INFERENCE'))[0], ['VALUE_SLOT_CONFLICT'])
        self.assertNotIn(check(fact('NO_INFORMATION', 'INFERENCE'))[1]['derived_fact_value'], ('NI', 'PY', 'PN'))

    def test_non_direct_statements_retain_target_and_plan_flags(self):
        answer = fact('NO_INFORMATION', 'NONDISCLOSURE_RULE_ONLY', statement_actor='pharmacy',
                      phase='before_allocation', information='OTHER_INFORMATION', scope='PLANNED')
        errors, fields, _ = check(answer)
        self.assertEqual(errors, [])
        self.assertEqual(fields['fact_flags'], ['ACTOR_MISMATCH', 'PHASE_MISMATCH',
                                               'INFORMATION_MISMATCH', 'PLAN_ONLY', 'NON_DIRECT_PROPOSITION'])
        self.assertEqual(fields['derived_fact_value'], 'NO_INFORMATION')
        planned_access = check(fact('NO_INFORMATION', 'ALLOCATION_KEY_ACCESS_ONLY', scope='PLANNED'))[1]
        self.assertEqual(planned_access['fact_flags'], ['PLAN_ONLY', 'NON_DIRECT_PROPOSITION'])


class ConsistencyAndRetention(unittest.TestCase):
    def test_contradiction_is_retained_never_rewritten(self):
        answer = fact('REPORTED_AWARE', 'NONDISCLOSURE_RULE_ONLY')
        original = copy.deepcopy(answer)
        errors, fields, evidence = check(answer)
        self.assertEqual(answer, original)
        self.assertEqual(errors, ['VALUE_SLOT_CONFLICT'])
        self.assertEqual((fields['derived_fact_value'], fields['deterministic_status']), ('NO_INFORMATION', 'INCONSISTENT'))
        self.assertEqual(evidence, [{'source_span_id': '1', 'quote': SPANS['1']}])

    def test_unknown_may_keep_contextual_evidence_or_none(self):
        for ids in (('1', '2'), ()):
            errors, fields, _ = check(fact('NO_INFORMATION', 'NOT_STATED', ids=ids, statement_actor='NOT_STATED',
                                           phase='NOT_STATED', information='NOT_STATED', scope='NOT_STATED'))
            self.assertEqual((errors, fields['deterministic_status']), ([], 'CONSISTENT_NO_INFORMATION'))

    def test_direct_facts_require_evidence(self):
        errors, fields, _ = check(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE', ids=()))
        self.assertIn('DIRECT_FACT_WITHOUT_EVIDENCE', errors)
        self.assertEqual(fields['deterministic_status'], 'INVALID')

    def test_unresolvable_or_duplicate_evidence_ids_fail(self):
        for ids in (('9',), ('1', '1'), ('1', '2', '2')):
            self.assertTrue(check(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE', ids=ids))[0])

    def test_model_supplied_review_or_acceptance_fields_are_rejected(self):
        for key, value in (('review_status', 'AI_REVIEWED_INDEPENDENT'), ('semantic_acceptance', True),
                           ('claim_use_allowed', True), ('deterministic_status', 'CONSISTENT_DIRECT')):
            errors, fields, _ = check({**fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE'), key: value})
            self.assertIn('MODEL_REVIEW_FIELD', errors)
            self.assertIn('INVALID_FIELDS', errors)
            self.assertEqual((fields['review_status'], fields['semantic_acceptance'], fields['claim_use_allowed']),
                             ('UNREVIEWED', False, False))

    def test_unknown_slot_vocabulary_and_missing_fields_are_invalid(self):
        self.assertIn('INVALID_SLOT', check(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE', scope='ACTUAL'))[0])
        self.assertIn('INVALID_SLOT', check(fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE', statement_actor='doctors'))[0])
        self.assertIn('INVALID_FACT_VALUE', check(fact('PY', 'DIRECT_IDENTITY_KNOWLEDGE'))[0])
        partial = fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE')
        del partial['phase']
        errors, fields, _ = check(partial)
        self.assertEqual((fields['derived_fact_value'], fields['deterministic_status']), (None, 'INVALID'))
        self.assertIn('INVALID_FIELDS', errors)

    def test_review_fields_are_fixed_by_code_on_every_status(self):
        for answer in (fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE'), fact('REPORTED_AWARE', 'INFERENCE'), {}):
            fields = check(answer)[1]
            self.assertEqual((fields['review_status'], fields['semantic_acceptance'], fields['claim_use_allowed']),
                             ('UNREVIEWED', False, False))

    def test_counts_keep_valid_binding_apart_from_consistent_and_unresolved(self):
        answers = [fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE'),
                   fact('NO_INFORMATION', 'DIRECT_IDENTITY_KNOWLEDGE', scope='PLANNED'),
                   fact('NO_INFORMATION', 'NOT_STATED'),
                   fact('REPORTED_AWARE', 'INFERENCE')]
        rows = []
        for a in answers:
            errors, fields, _ = check(a)
            rows.append({**fields, 'binding_pass': not errors})
        counts = af.summarize(rows)
        self.assertEqual(counts, {'valid_binding': 4, 'slot_consistency_passes': 3,
                                  'consistent_direct': 1, 'consistent_no_information': 1,
                                  'flagged': 1, 'inconsistent': 1, 'invalid': 0, 'unresolved_knowledge': 3})

    def test_source_binding_and_slot_consistency_are_orthogonal(self):
        bound_conflict = fact('REPORTED_AWARE', 'NONDISCLOSURE_RULE_ONLY')
        unbound_consistent = fact('REPORTED_AWARE', 'DIRECT_IDENTITY_KNOWLEDGE', ids=('missing',))
        rows = []
        for answer in (bound_conflict, unbound_consistent):
            errors, fields, _ = check(answer)
            rows.append({**fields, 'binding_pass': not errors})
        self.assertEqual([(x['fact_source_binding_pass'], x['fact_slot_consistency_pass']) for x in rows],
                         [(True, False), (False, True)])
        counts = af.summarize(rows)
        self.assertEqual((counts['valid_binding'], counts['inconsistent'], counts['invalid'],
                          counts['unresolved_knowledge'], counts['slot_consistency_passes']), (1, 1, 1, 1, 1))


class ConfigAndSchema(unittest.TestCase):
    def bad(self, mutate, values=VALUES):
        schema = copy.deepcopy(SCHEMA)
        mutate(schema)
        with self.assertRaises(ValueError):
            af.validate_config(schema, values)

    def test_valid_configuration_and_shipped_example(self):
        af.validate_config(SCHEMA, VALUES)
        packet = json.loads((Path(__file__).parent.parent / 'examples' / 'awareness-fact-packet.json').read_text())
        for q in packet['questions']:
            af.validate_config(q['fact_schema'], q['allowed_values'])

    def test_malformed_or_unsupported_configuration_is_rejected(self):
        self.bad(lambda s: s.update(version='awareness-fact/v2'))
        self.bad(lambda s: s.pop('phases'))
        self.bad(lambda s: s.update(extra=1))
        self.bad(lambda s: s['target'].update(scope='PLANNED'))
        self.bad(lambda s: s['target'].update(actor='missing'))
        self.bad(lambda s: s['target'].update(phase='missing'))
        self.bad(lambda s: s['target'].update(information='OTHER_INFORMATION'))
        self.bad(lambda s: s['actors'].update({'Bad Id': []}))
        self.bad(lambda s: s['actors'].update({'x': 'ward'}))
        self.bad(lambda s: s['phases'].update({'x': ['']}))
        self.bad(lambda s: s.update(target=None))

    def test_method_vocabularies_are_not_fact_vocabularies(self):
        for values in (['Y', 'PY', 'PN', 'N', 'NI', 'NO_INFORMATION'], ['REPORTED_AWARE', 'NO_INFORMATION'],
                       VALUES + ['NI'], 'REPORTED_AWARE'):
            self.bad(lambda s: None, values)

    def test_response_format_is_evidence_first_and_closed(self):
        fmt = af.response_format(SCHEMA, SPANS, 3)['json_schema']['schema']
        self.assertEqual(list(fmt['properties']), ['source_span_ids', 'statement_actor', 'phase', 'information',
                                                    'scope', 'proposition', 'rationale', 'fact_value'])
        self.assertEqual(fmt['required'], list(fmt['properties']))
        self.assertFalse(fmt['additionalProperties'])
        self.assertEqual(fmt['properties']['statement_actor']['enum'],
                         ['nurses', 'pharmacy', 'participants', 'OTHER_ACTOR', 'NOT_STATED'])
        self.assertEqual(fmt['properties']['fact_value']['enum'], VALUES)
        for forbidden in af.MODEL_REVIEW_FIELDS:
            self.assertNotIn(forbidden, fmt['properties'])


if __name__ == '__main__':
    unittest.main()
