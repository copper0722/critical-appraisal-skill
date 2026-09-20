"""Locate quoted evidence in unchanged source text; never judge claim support."""
import argparse
import hashlib
import json
from pathlib import Path


def _view(text, whitespace):
    chars=[];starts=[];ends=[]
    for i,char in enumerate(text):
        if whitespace and char.isspace():
            if chars and chars[-1]==' ':
                ends[-1]=i+1
                continue
            char=' '
        chars.append(char);starts.append(i);ends.append(i+1)
    return ''.join(chars),starts,ends


def locate(source, quote, *, normalization='exact', expected_source_sha256=None):
    if normalization not in ('exact','whitespace'):
        raise ValueError('unsupported quote normalization')
    digest=hashlib.sha256(source.encode()).hexdigest()
    if expected_source_sha256 is not None and digest!=expected_source_sha256:
        raise ValueError('source hash mismatch')
    if not isinstance(quote,str) or not quote.strip():
        raise ValueError('nonempty quoted evidence required')
    text,starts,ends=_view(source,normalization=='whitespace')
    needle,_,_=_view(quote,normalization=='whitespace')
    if normalization=='whitespace':needle=needle.strip()
    matches=[];offset=0
    while True:
        index=text.find(needle,offset)
        if index<0:break
        start,end=starts[index],ends[index+len(needle)-1]
        matches.append({'start':start,'end':end,'quote':source[start:end],
                        'context_start':max(0,start-160),'context_end':min(len(source),end+160),
                        'context':source[max(0,start-160):min(len(source),end+160)]})
        offset=index+1
    return {'status':'LOCATED' if len(matches)==1 else 'AMBIGUOUS' if matches else 'NOT_FOUND',
            'source_sha256':digest,'candidate_quote_sha256':hashlib.sha256(quote.encode()).hexdigest(),
            'normalization':normalization,'matches':matches,'semantic_acceptance':False,
            'claim_use_allowed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('quote_file');parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--normalization',choices=['exact','whitespace'],default='exact')
    args=parser.parse_args()
    print(json.dumps(locate(Path(args.source).read_bytes().decode('utf-8'),Path(args.quote_file).read_bytes().decode('utf-8'),
                           normalization=args.normalization,expected_source_sha256=args.source_sha256),ensure_ascii=False,indent=2))
