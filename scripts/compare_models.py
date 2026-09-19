#!/usr/bin/env python3
"""Compare paired appraisal answers without treating either model as truth."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def index_rows(rows, key, label):
    require(isinstance(rows, list), f'{label} must be a list')
    out = {}
    for row in rows:
        require(isinstance(row, dict) and nonempty(row.get(key)), f'invalid {label} row')
        require(row[key] not in out, f'duplicate {label}: {row[key]}')
        out[row[key]] = row
    return out


def compare(protocol, small, large):
    require(nonempty(protocol.get('id')), 'protocol id missing')
    require(protocol.get('split') in ('development', 'held_out'), 'evaluation split missing')
    cases = index_rows(protocol.get('cases'), 'id', 'cases')
    require(bool(cases), 'empty evaluation set')
    for case in cases.values():
        require(sha(case.get('source_package_sha256')), 'source hash missing')
        require(nonempty(case.get('assessment_unit')) and nonempty(case.get('route')), 'case identity missing')
        require(sha(case.get('method_sha256')), 'method hash missing')
        questions = case.get('questions')
        require(isinstance(questions, dict) and bool(questions), 'questions missing')
        for q, spec in questions.items():
            require(nonempty(q) and isinstance(spec, dict), 'invalid question')
            values = spec.get('allowed_answers')
            require(isinstance(values, list) and values and all(nonempty(v) for v in values)
                    and len(values)==len(set(values)), 'answer vocabulary missing/duplicated')
            weight = spec.get('weight', 1)
            require(type(weight) in (int, float) and math.isfinite(weight) and weight > 0, 'invalid weight')
    arms = []
    for label, run in [('small', small), ('high_end', large)]:
        require(run.get('protocol_id') == protocol['id'], f'{label} protocol mismatch')
        require(nonempty(run.get('model_id')) and nonempty(run.get('run_id')), f'{label} model/run identity missing')
        require(sha(run.get('raw_output_sha256')), f'{label} output hash missing')
        rows = index_rows(run.get('cases'), 'id', label)
        require(set(rows) <= set(cases), f'{label} has unplanned case')
        for cid, row in rows.items():
            expected = cases[cid]
            for key in ('source_package_sha256', 'method_sha256', 'assessment_unit', 'route'):
                require(row.get(key) == expected[key], f'{label}/{cid} {key} mismatch')
            require(row.get('status') in ('complete','failed','abstained'), f'{label}/{cid} unknown status')
            answers = row.get('answers', {})
            require(isinstance(answers, dict) and set(answers) <= set(expected['questions']), 'unplanned answers')
            for q, answer in answers.items():
                require(answer in expected['questions'][q]['allowed_answers'], f'{label}/{cid}/{q} invalid answer')
        arms.append(rows)
    require(small['run_id'] != large['run_id'], 'same run cannot be two comparators')
    require(small['model_id'] != large['model_id'], 'same model is not a small-versus-high-end comparison')
    comparisons = []
    total_weight = matched_weight = 0
    for cid, case in cases.items():
        for q, spec in case['questions'].items():
            values = []
            for arm in arms:
                row = arm.get(cid, {})
                values.append(row.get('answers', {}).get(q) if row.get('status') == 'complete' else None)
            matched = None not in values and values[0] == values[1]
            weight = spec.get('weight', 1)
            total_weight += weight
            matched_weight += weight if matched else 0
            comparisons.append({'case_id':cid, 'question_id':q, 'small':values[0], 'high_end':values[1],
                                'paired':None not in values, 'agreement':matched, 'weight':weight})
    paired = sum(r['paired'] for r in comparisons)
    matched = sum(r['agreement'] for r in comparisons)
    return {'status':'COMPARISON_RECORDED_NOT_ADJUDICATED', 'protocol_id':protocol['id'],
            'split':protocol['split'], 'planned_questions':len(comparisons), 'paired_questions':paired,
            'missing_or_failed_questions':len(comparisons)-paired,
            'agreements':matched, 'agreement_over_planned':matched/len(comparisons),
            'agreement_over_paired':matched/paired if paired else None,
            'weighted_agreement_over_planned':matched_weight/total_weight,
            'comparisons':comparisons, 'equivalence_established':False,
            'remaining':['verify raw output and source bindings', 'source-grounded adjudication',
                         'material omissions and false reassurance', 'prespecified equivalence criterion',
                         'held-out cross-type coverage and uncertainty'],
            'note':'Matching unknown answers count as categorical agreement, not demonstrated ability.'}


def load(path):
    data = Path(path).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('protocol'); p.add_argument('small_run'); p.add_argument('high_end_run')
    args = p.parse_args()
    try:
        protocol, ph = load(args.protocol); small, sh = load(args.small_run); large, lh = load(args.high_end_run)
        result = compare(protocol, small, large)
        result['input_receipt_sha256'] = {'protocol':ph, 'small':sh, 'high_end':lh}
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        print(json.dumps({'status':'HOLD','reason':str(exc)})); return 1
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
