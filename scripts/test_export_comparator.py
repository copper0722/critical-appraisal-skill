import json
import unittest
from export_comparator import packet


class ExportTests(unittest.TestCase):
    def test_complete_input_without_reference_answers(self):
        p=packet()
        self.assertEqual(len(p['cases']),4)
        self.assertEqual(len(p['fields']),4)
        self.assertNotIn('expected',json.dumps(p))
        self.assertTrue(all(set(c)=={'id','source'} for c in p['cases']))

    def test_empty_and_duplicate_input_refused(self):
        with self.assertRaises(ValueError):packet([])
        with self.assertRaises(ValueError):packet([{'id':'a','source':'x'}]*2)


if __name__=='__main__':unittest.main()
