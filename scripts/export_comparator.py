#!/usr/bin/env python3
"""Export synthetic comparator inputs without exposing developer reference answers."""
import json
from evaluate_local import CASES, FIELD_RULES


def packet(cases=CASES, fields=FIELD_RULES):
    if not cases or not fields:
        raise ValueError('empty comparison input')
    ids=[c['id'] for c in cases]
    if len(ids)!=len(set(ids)) or not all(isinstance(c.get('source'),str) and c['source'].strip() for c in cases):
        raise ValueError('duplicate case or missing source')
    return {'cases':[{'id':c['id'],'source':c['source']} for c in cases],
            'fields':{k:{'question':v[0],'allowed_values':v[1]} for k,v in fields.items()}}


if __name__=='__main__':
    print(json.dumps(packet(),ensure_ascii=False,indent=2))
