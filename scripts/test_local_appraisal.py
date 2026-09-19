"""Synthetic contract tests; not clinical or local-model performance evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from local_appraisal import check, digest, prompts


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = 'Methods\nAllocation was concealed.\n'
        self.manual = 'Synthetic rule: YES needs an explicit supporting sentence.\n'
        (self.root / 'source.txt').write_text(self.source)
        (self.root / 'manual.txt').write_text(self.manual)
        self.packet = {'paper_id': 'fixture-only', 'assessment_unit': 'result1', 'route': 'synthetic',
                       'protocol_id': 'test1', 'fulltext_available': True,
                       'method': {'id': 'synthetic', 'version': '1', 'scope_verified': True,
                                  'manual_path': 'manual.txt', 'manual_sha256': digest(self.manual.encode()),
                                  'domains': [{'id': 'allocation', 'question': 'Was allocation concealed?',
                                               'rule': self.manual, 'allowed_answers': ['YES', 'NO_INFORMATION']}]},
                       'sources': [{'id': 'main', 'path': 'source.txt', 'sha256': digest(self.source.encode())}]}
        self.packet_path = self.root / 'packet.json'
        self.packet_path.write_text(json.dumps(self.packet))
        self.draft = {k: self.packet[k] for k in ('paper_id', 'assessment_unit', 'route', 'protocol_id')}
        self.draft.update(status='DRAFT', packet_sha256=digest(self.packet_path.read_bytes()), limitations=[],
                          domains=[{'id': 'allocation', 'answer': 'YES', 'rationale': 'Explicitly reported.',
                                    'limitations': [], 'evidence': [{'source_id': 'main', 'start_line': 2,
                                    'end_line': 2, 'quote': 'Allocation was concealed.'}]}])

    def validate(self, draft):
        p = self.root / 'draft.json'
        p.write_text(json.dumps(draft))
        return check(self.packet_path, p)

    def test_valid_is_only_draft(self):
        self.assertFalse(self.validate(self.draft)['claim_use_allowed'])
        self.assertEqual(prompts(self.packet_path, 24000)['status'], 'PREPARED_NOT_RUN')

    def test_hash_changed(self):
        (self.root / 'source.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.validate(self.draft)

    def test_reject_invalid_outputs(self):
        mutations = [lambda d: d.update(status='ACCEPTED_APPRAISED'),
                     lambda d: d.update(packet_sha256='0'*64),
                     lambda d: d.update(domains=[]),
                     lambda d: d['domains'].append(copy.deepcopy(d['domains'][0])),
                     lambda d: d['domains'][0].update(answer='LOW'),
                     lambda d: d['domains'][0].update(evidence=[]),
                     lambda d: d['domains'][0]['evidence'][0].update(quote='Not concealed.'),
                     lambda d: d['domains'][0]['evidence'][0].update(start_line=True),
                     lambda d: d['domains'][0]['evidence'][0].update(source_id='missing')]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                d = copy.deepcopy(self.draft)
                mutate(d)
                with self.assertRaises(ValueError):
                    self.validate(d)

    def test_no_information_preserved(self):
        d = copy.deepcopy(self.draft)
        d['domains'][0].update(answer='NO_INFORMATION', evidence=[], limitations=['Required procedure not established.'])
        self.assertEqual(self.validate(d)['status'], 'DRAFT_BINDINGS_VALID')
        d['domains'][0]['limitations'] = []
        with self.assertRaises(ValueError):
            self.validate(d)

    def test_oversize_never_truncated(self):
        with self.assertRaisesRegex(ValueError, 'SPLIT_REQUIRED'):
            prompts(self.packet_path, 10)

    def test_missing_fulltext_and_method_scope(self):
        for key in ('fulltext_available', 'scope_verified'):
            p = copy.deepcopy(self.packet)
            (p if key == 'fulltext_available' else p['method'])[key] = False
            self.packet_path.write_text(json.dumps(p))
            with self.assertRaises(ValueError):
                prompts(self.packet_path, 24000)

    def absence_packet(self, coverage=None):
        self.packet['method']['domains'][0].update(
            allowed_answers=['YES', 'ABSENT', 'NO_INFORMATION'], absence_answers=['ABSENT'])
        if coverage is not None:
            self.packet['coverage'] = coverage
        self.packet_path.write_text(json.dumps(self.packet))
        self.draft['packet_sha256'] = digest(self.packet_path.read_bytes())
        self.draft['domains'][0]['answer'] = 'ABSENT'

    def test_absence_needs_whole_document_coverage(self):
        self.absence_packet()
        with self.assertRaisesRegex(ValueError, 'ABSENCE_NOT_ESTABLISHED'):
            self.validate(self.draft)
        complete = {'whole_document_reviewed': True, 'reviewed_source_ids': ['main'],
                    'unresolved_components': [], 'search_method': 'Read every provided component.'}
        for patch in ({'whole_document_reviewed': False}, {'reviewed_source_ids': []},
                      {'reviewed_source_ids':['main','main']}, {'unresolved_components':['appendix']},
                      {'search_method':''}):
            self.absence_packet({**complete, **patch})
            with self.assertRaisesRegex(ValueError, 'ABSENCE_NOT_ESTABLISHED'):
                self.validate(self.draft)
        self.absence_packet(complete)
        # Binding pass still does not endorse the intentionally contradictory fixture judgment.
        self.assertFalse(self.validate(self.draft)['claim_use_allowed'])

    def test_unknown_remains_available_without_coverage(self):
        self.absence_packet()
        self.draft['domains'][0].update(answer='NO_INFORMATION', evidence=[],
                                      limitations=['Only an excerpt was inspected.'])
        self.assertEqual(self.validate(self.draft)['status'], 'DRAFT_BINDINGS_VALID')


if __name__ == '__main__':
    unittest.main()
