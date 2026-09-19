#!/usr/bin/env python3
"""Bind an explicitly selected method pack; never infer document type from its title."""
import argparse
import hashlib
import json
from pathlib import Path


def bind(path, document_type):
    raw = Path(path).read_bytes()
    pack = json.loads(raw)
    if pack.get('schema') != 'appraisal-method-pack/v1':
        raise ValueError('unsupported method pack schema')
    if document_type not in pack['scope']['document_types']:
        raise ValueError('METHOD_SCOPE_MISMATCH')
    domains = pack['domains']
    if not domains or len({d['id'] for d in domains}) != len(domains):
        raise ValueError('missing/duplicate method domains')
    for d in domains:
        if not d.get('question') or not d.get('rule') or 'NO_INFORMATION' not in d['allowed_answers']:
            raise ValueError('invalid method domain')
    return {'id':pack['id'], 'version':pack['version'], 'manual_path':str(Path(path).resolve()),
            'manual_sha256':hashlib.sha256(raw).hexdigest(), 'scope_verified':False,
            'document_type':document_type, 'coverage_policy':pack['coverage_policy'],
            'domains':domains, 'limitations':pack['limitations'],
            'required_before_use':'Controller verifies actual document methods and original authority; then sets scope_verified.'}


def summarize_scores(answers):
    expected={'importance','aims','search','referencing','reasoning','data'}
    if not isinstance(answers,dict) or set(answers)!=expected:
        raise ValueError('six exact SANRA item IDs required')
    if any(v not in ('0','1','2','NO_INFORMATION') for v in answers.values()):
        raise ValueError('invalid SANRA answer')
    unresolved=[k for k,v in answers.items() if v=='NO_INFORMATION']
    return {'item_scores':answers, 'unresolved_items':unresolved,
            'sum_score':None if unresolved else sum(int(v) for v in answers.values()),
            'maximum':12, 'quality_category':None, 'claim_use_allowed':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pack');p.add_argument('--document-type',required=True)
    args=p.parse_args()
    try:print(json.dumps(bind(args.pack,args.document_type),ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'status':'HOLD','reason':str(exc)}));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
