#!/usr/bin/env python3
"""RoB 2 (22 August 2019, parallel trial) algorithm proposals from explicit answers.

This is decision support, not an automated reading or an official questionnaire.
Use the original manual to answer its signalling questions. Technical abstention
is deliberately distinct from the manual's NI response. No numeric score exists.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


VERSION = '2019-08-22'
MANUAL_SHA256 = 'a9e9c4fdc4be2d29b5c0a1a6b828e09f2014a34f6d5c302a532f6153ea0fd670'
YES = frozenset(('Y', 'PY'))
NO = frozenset(('N', 'PN'))
VALUES = YES | NO | {'NI'}
LOW, SOME, HIGH = 'Low', 'Some concerns', 'High'
LEVELS = (LOW, SOME, HIGH)
DOMAINS = ('D1', 'D2', 'D3', 'D4', 'D5')
DEVIATIONS = frozenset(('non_protocol_interventions', 'implementation_failures',
                        'participant_non_adherence'))
ANCHORS = {'D1': 'Figure 1, Tables 3-4, pp19-20',
           'D2:assignment': 'Figure 2, Tables 5-6, pp30-33',
           'D2:adhering': 'Figure 3, Tables 7-8, pp36-38',
           'D3': 'Figure 4, Tables 9-10, pp47-48',
           'D4': 'Figure 5, Tables 11-12, pp56-57',
           'D5': 'Figure 7, Tables 13-14, pp66-67'}


class Unresolved(ValueError):
    def __init__(self, question):
        self.question = question
        super().__init__('TECHNICAL_ABSTENTION_OR_MISSING_ANSWER: ' + question)


class Responses:
    def __init__(self, answers, ids):
        if not isinstance(answers, dict) or set(answers) - set(ids):
            raise ValueError('unknown question IDs or invalid answers object')
        for value in answers.values():
            if not isinstance(value, str) or value not in VALUES | {'NA', 'NO_INFORMATION'}:
                raise ValueError('invalid signalling response')
        self.answers, self.trace = answers, []

    def ask(self, question, active=True):
        value = self.answers.get(question)
        if not active:
            if value not in (None, 'NA'):
                raise ValueError('inactive question must be absent or NA: ' + question)
            self.trace.append({'question': question, 'response': 'NA', 'active': False})
            return 'NA'
        if value is None or value == 'NO_INFORMATION':
            raise Unresolved(question)
        if value == 'NA':
            raise ValueError('active question cannot be NA: ' + question)
        if question == '3.2' and value == 'NI':
            raise ValueError('NI is not a permitted response to question 3.2')
        self.trace.append({'question': question, 'response': value, 'active': True})
        return value


def propose_domain(domain, answers, *, effect_of_interest=None, deviation_types=()):
    """Return a traced proposal; missing/technical abstention produces HOLD.

    D2 must explicitly namespace its branch at the assessment boundary. Callers
    must not reuse a 2.3-2.6 answer across assignment and adhering assessments.
    """
    if domain == 'D2' and effect_of_interest is None:
        raise ValueError('D2 requires an explicit effect of interest')
    if effect_of_interest is None:
        effect_of_interest = 'assignment'  # no algorithm branching in other domains
    if domain not in DOMAINS or effect_of_interest not in ('assignment', 'adhering'):
        raise ValueError('unsupported domain or effect of interest')
    if not isinstance(deviation_types, (list, tuple)) or any(
            not isinstance(x, str) or x not in DEVIATIONS for x in deviation_types):
        raise ValueError('invalid deviation types')
    if len(set(deviation_types)) != len(deviation_types):
        raise ValueError('duplicate deviation types')
    if effect_of_interest == 'adhering' and not deviation_types:
        raise ValueError('adhering assessment requires selected deviation types')
    if effect_of_interest == 'assignment' and deviation_types:
        raise ValueError('deviation types apply only to adhering assessments')
    count = {'D1': 3, 'D2': 7 if effect_of_interest == 'assignment' else 6,
             'D3': 4, 'D4': 5, 'D5': 3}[domain]
    prefix = domain[1]
    r = Responses(answers, [f'{prefix}.{i}' for i in range(1, count + 1)])
    q = r.ask
    anchor = ANCHORS[domain + ':' + effect_of_interest if domain == 'D2' else domain]
    result = {'domain': domain, 'method_version': VERSION, 'source_anchor': anchor,
              'effect_of_interest': effect_of_interest, 'trace': r.trace,
              'claim_use_allowed': False, 'semantic_acceptance': False}
    try:
        if domain == 'D1':
            sequence, concealment, imbalance = q('1.1'), q('1.2'), q('1.3')
            if concealment in NO:
                proposal = HIGH
            elif concealment == 'NI':
                proposal = HIGH if imbalance in YES else SOME
            else:
                proposal = SOME if sequence in NO or imbalance in YES else LOW
        elif domain == 'D2' and effect_of_interest == 'assignment':
            aware1, aware2 = q('2.1'), q('2.2')
            awareness = aware1 not in NO or aware2 not in NO
            deviation = q('2.3', awareness)
            affects = q('2.4', deviation in YES)
            balanced = q('2.5', affects in YES | {'NI'})
            analysis = q('2.6')
            impact = q('2.7', analysis not in YES)
            if not awareness or deviation in NO:
                part1 = LOW
            elif deviation == 'NI' or affects in NO or balanced in YES:
                part1 = SOME
            else:
                part1 = HIGH
            part2 = LOW if analysis in YES else SOME if impact in NO else HIGH
            proposal = max((part1, part2), key=LEVELS.index)
            result['subproposals'] = {'deviations': part1, 'analysis': part2}
        elif domain == 'D2':
            aware1, aware2 = q('2.1'), q('2.2')
            awareness = aware1 not in NO or aware2 not in NO
            balanced = q('2.3', 'non_protocol_interventions' in deviation_types and awareness)
            implementation = q('2.4', 'implementation_failures' in deviation_types)
            adherence = q('2.5', 'participant_non_adherence' in deviation_types)
            adverse = (balanced in NO | {'NI'} or implementation in YES | {'NI'}
                       or adherence in YES | {'NI'})
            analysis = q('2.6', adverse)
            proposal = LOW if not adverse else SOME if analysis in YES else HIGH
        elif domain == 'D3':
            complete = q('3.1')
            unbiased = q('3.2', complete not in YES)
            could = q('3.3', unbiased in NO)
            likely = q('3.4', could in YES | {'NI'})
            if complete in YES or unbiased in YES or could in NO:
                proposal = LOW
            else:
                proposal = SOME if likely in NO else HIGH
        elif domain == 'D4':
            inappropriate, differs = q('4.1'), q('4.2')
            aware = q('4.3', inappropriate not in YES and differs not in YES)
            could = q('4.4', aware in YES | {'NI'})
            likely = q('4.5', could in YES | {'NI'})
            if inappropriate in YES or differs in YES:
                proposal = HIGH
            elif aware in NO or could in NO:
                proposal = SOME if differs == 'NI' else LOW
            else:
                proposal = SOME if likely in NO else HIGH
        else:
            planned, measurement, analysis = q('5.1'), q('5.2'), q('5.3')
            if measurement in YES or analysis in YES:
                proposal = HIGH
            elif measurement == 'NI' or analysis == 'NI':
                proposal = SOME
            else:
                proposal = LOW if planned in YES else SOME
    except Unresolved as exc:
        result.update(status='HOLD', proposed_judgement=None, unresolved_question=exc.question,
                      reason='No tool response inferred from missing data or model abstention.')
        return result
    result.update(status='PROPOSED', proposed_judgement=proposal)
    return result


def overall(judgements, joint_concerns=None):
    """Combine five domain judgements, preserving the manual's qualitative rule.

    Multiple Some concerns never automatically means High. A reviewer must
    decide whether the combination substantially lowers confidence (p4).
    """
    if not isinstance(judgements, dict) or set(judgements) != set(DOMAINS):
        raise ValueError('all five exact domain judgements required')
    if any(not isinstance(v, str) or v not in LEVELS for v in judgements.values()):
        raise ValueError('invalid domain judgement')
    values = list(judgements.values())
    baseline = max(values, key=LEVELS.index)
    needs_joint = HIGH not in values and values.count(SOME) > 1
    if joint_concerns is not None:
        if not needs_joint or not isinstance(joint_concerns, dict):
            raise ValueError('joint-concerns decision only applies to multiple Some concerns without High')
        if type(joint_concerns.get('substantially_lowers_confidence')) is not bool:
            raise ValueError('explicit boolean joint-concerns judgement required')
        for field in ('reviewer', 'reason'):
            if not isinstance(joint_concerns.get(field), str) or not joint_concerns[field].strip():
                raise ValueError('joint-concerns judgement requires reviewer and reason')
        if joint_concerns['substantially_lowers_confidence']:
            baseline = HIGH
    pending = needs_joint and joint_concerns is None
    return {'status': 'HOLD' if pending else 'PROPOSED', 'minimum_judgement': max(values, key=LEVELS.index),
            'proposed_judgement': None if pending else baseline,
            'joint_concerns_review_required': pending, 'joint_concerns': joint_concerns,
            'source_anchor': 'Table 1, p4', 'claim_use_allowed': False, 'numeric_score': None}


def assess(packet, manual_path):
    """Validate a version-bound result assessment and preserve reasoned overrides.

    Source identities/reasons are required, but their semantic support still
    needs an independent reader. Passing this function is not that truth gate.
    """
    if not isinstance(packet, dict) or packet.get('schema') != 'rob2-assessment/v1':
        raise ValueError('unsupported assessment schema')
    method = packet.get('method', {})
    if not isinstance(method, dict) or method.get('id') != 'rob2-parallel' or method.get('version') != VERSION:
        raise ValueError('method identity/version mismatch')
    manual_hash = hashlib.sha256(Path(manual_path).read_bytes()).hexdigest()
    if (method.get('manual_sha256') != manual_hash or manual_hash != MANUAL_SHA256
            or method.get('scope_verified') is not True):
        raise ValueError('manual hash mismatch or scope not verified')
    unit = packet.get('assessment_unit', {})
    if not isinstance(unit, dict):
        raise ValueError('invalid assessment unit')
    for field in ('study_id', 'experimental', 'comparator', 'outcome', 'timepoint', 'result_id'):
        if not isinstance(unit.get(field), str) or not unit[field].strip():
            raise ValueError('missing result-specific assessment field: ' + field)
    if unit.get('design') != 'individually_randomized_parallel':
        raise ValueError('METHOD_SCOPE_MISMATCH')
    effect = unit.get('effect_of_interest')
    if effect not in ('assignment', 'adhering'):
        raise ValueError('explicit effect of interest required')
    sources = packet.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('source identities required')
    source_ids = set()
    for s in sources:
        if not isinstance(s, dict) or not isinstance(s.get('id'), str) or not s['id'].strip():
            raise ValueError('invalid source identity')
        if s['id'] in source_ids or not isinstance(s.get('sha256'), str) or not re.fullmatch(r'[a-f0-9]{64}', s['sha256']):
            raise ValueError('duplicate source or invalid source hash')
        source_ids.add(s['id'])
    entries = packet.get('domains')
    if not isinstance(entries, dict) or set(entries) != set(DOMAINS):
        raise ValueError('all five domain records required')
    outputs, judgements = {}, {}
    for domain in DOMAINS:
        entry = entries[domain]
        if not isinstance(entry, dict):
            raise ValueError('invalid domain entry')
        if domain == 'D2' and entry.get('effect_of_interest') != effect:
            raise ValueError('D2 branch does not match assessment effect')
        output = propose_domain(domain, entry.get('answers'), effect_of_interest=effect,
                                deviation_types=unit.get('deviation_types', ()))
        support = entry.get('support', {})
        if not isinstance(support, dict):
            raise ValueError('question support must be an object')
        for item in output['trace']:
            if not item['active']:
                continue
            evidence = support.get(item['question'], {})
            if not isinstance(evidence, dict) or not isinstance(evidence.get('reason'), str) or not evidence['reason'].strip():
                raise ValueError('reason required for active answer: ' + item['question'])
            ids = evidence.get('source_ids')
            if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or x not in source_ids for x in ids):
                raise ValueError('bound sources required for active answer: ' + item['question'])
            if not isinstance(evidence.get('locator'), str) or not evidence['locator'].strip():
                raise ValueError('source locator/coverage statement required: ' + item['question'])
        output['support'] = support
        override = entry.get('override')
        if override is not None:
            if output['status'] != 'PROPOSED' or not isinstance(override, dict):
                raise ValueError('override requires a completed proposal')
            if override.get('judgement') not in LEVELS:
                raise ValueError('invalid override judgement')
            for field in ('reviewer', 'reason'):
                if not isinstance(override.get(field), str) or not override[field].strip():
                    raise ValueError('override reviewer and reason required')
            output['override'] = override
        if output['status'] == 'PROPOSED':
            judgements[domain] = override['judgement'] if override else output['proposed_judgement']
        outputs[domain] = output
    combined = (overall(judgements, packet.get('joint_concerns')) if len(judgements) == 5 else
                {'status': 'HOLD', 'proposed_judgement': None, 'reason': 'unresolved domains',
                 'claim_use_allowed': False, 'numeric_score': None})
    return {'schema': 'rob2-proposal/v1', 'method': method, 'assessment_unit': unit,
            'sources': sources, 'domains': outputs, 'overall': combined,
            'status': combined['status'], 'semantic_acceptance': False, 'claim_use_allowed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('assessment', type=Path)
    p.add_argument('--manual', type=Path, required=True, help='operator-supplied unchanged original guidance')
    args = p.parse_args()
    try:
        result = assess(json.loads(args.assessment.read_text()), args.manual)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({'status': 'HOLD', 'reason': str(exc), 'claim_use_allowed': False}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PROPOSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
