import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from evaluate_packet import run, source_spans


class PacketRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.p=self.root/'packet.json';self.o=self.root/'out.jsonl'
        self.source='No participants were allocated.'
        self.packet={'id':'fixture','source_text':self.source,
                     'source_text_sha256':hashlib.sha256(self.source.encode()).hexdigest(),
                     'assessment_unit':'study1','questions':[{'id':'allocation','question':'Allocation?',
                     'allowed_values':['NO','NO_INFORMATION']}]}
        self.p.write_text(json.dumps(self.packet));self.sent=0;self.health_reads=0

    def response(self,obj):return io.BytesIO(json.dumps(obj).encode())

    def transport(self,request,timeout=None):
        if isinstance(request,str):
            self.health_reads+=1
            return self.response({'loaded_model':'small'})
        self.sent+=1
        return self.response({'model':'small','choices':[{'finish_reason':'stop',
             'message':{'content':json.dumps({'value':'NO','quote':self.source,'rationale':'Explicit negative.'})}}]})

    def test_actual_contract_and_no_replay(self):
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=self.transport):
            result=run(self.p,'small','http://localhost',self.o)
            self.assertEqual(result['binding_passes'],1);self.assertFalse(result['semantic_acceptance'])
            with self.assertRaises(FileExistsError):run(self.p,'small','http://localhost',self.o)
        self.assertEqual(self.sent,1)
        states=[json.loads(l)['state'] for l in self.o.read_text().splitlines()]
        self.assertEqual(states,['REQUEST_STARTED','RESPONSE_RECEIVED','COMPLETE'])

    def test_stop_arriving_during_preflight(self):
        stop=self.root/'STOP'
        def transport(req,timeout=None):
            answer=self.transport(req,timeout)
            if self.health_reads==2:stop.write_text('stop')
            return answer
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            with self.assertRaisesRegex(RuntimeError,'STOP during preflight'):
                run(self.p,'small','http://localhost',self.o,stop)
        self.assertEqual(self.sent,0)
        self.assertEqual(json.loads(self.o.read_text().splitlines()[-1])['state'],'STOPPED_BEFORE_SEND')

    def test_bad_source_refused_before_network(self):
        self.packet['source_text']='changed';self.p.write_text(json.dumps(self.packet))
        with patch('evaluate_packet.urllib.request.urlopen') as net:
            with self.assertRaises(ValueError):run(self.p,'small','http://localhost',self.o)
            net.assert_not_called()

    def test_span_ids_resolve_from_source(self):
        def transport(req,timeout=None):
            if isinstance(req,str):return self.response({'loaded_model':'small'})
            return self.response({'model':'small','choices':[{'finish_reason':'stop','message':{
                'content':json.dumps({'value':'NO','source_span_ids':['1'],'rationale':'Explicit negative.'})}}]})
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            result=run(self.p,'small','http://localhost',self.o,evidence_mode='span_ids')
        self.assertEqual(result['binding_passes'],1)
        row=json.loads(self.o.read_text().splitlines()[1])
        self.assertEqual(row['resolved_evidence'][0]['quote'],self.source)
        self.assertFalse(result['semantic_acceptance'])

    def test_fake_duplicate_empty_span_ids_fail_binding(self):
        for i, ids in enumerate([['999'],['1','1'],[]]):
            def transport(req,timeout=None):
                if isinstance(req,str):return self.response({'loaded_model':'small'})
                return self.response({'model':'small','choices':[{'finish_reason':'stop','message':{
                    'content':json.dumps({'value':'NO','source_span_ids':ids,'rationale':'Claim.'})}}]})
            with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
                r=run(self.p,'small','http://localhost',self.root/f'bad-{i}.jsonl',evidence_mode='span_ids')
            self.assertEqual(r['binding_passes'],0)

    def test_truncated_output_is_preserved_and_not_retried(self):
        def transport(req,timeout=None):
            if isinstance(req,str):return self.response({'loaded_model':'small'})
            self.sent+=1
            return self.response({'model':'small','choices':[{'finish_reason':'length',
                                  'message':{'content':'{"value":"NO'}}]})
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            summary=run(self.p,'small','http://localhost',self.o)
        row=json.loads(self.o.read_text().splitlines()[-2])
        self.assertEqual(row['state'],'RESPONSE_INVALID')
        self.assertTrue(row['request_resolved'])
        self.assertIn('INVALID_JSON',row['validation_errors'])
        self.assertEqual(row['response']['choices'][0]['finish_reason'],'length')
        self.assertEqual(self.sent,1)
        self.assertEqual(summary['planned_questions'],1)
        self.assertEqual(summary['binding_passes'],0)

    def test_received_invalid_answer_does_not_hide_later_planned_questions(self):
        self.packet['questions'].append({**self.packet['questions'][0],'id':'second'})
        self.p.write_text(json.dumps(self.packet))
        def transport(req,timeout=None):
            if isinstance(req,str):return self.response({'loaded_model':'small'})
            if self.sent==0:
                self.sent+=1
                return self.response({'model':'small','choices':[{'finish_reason':'length','message':{'content':'{'}}]})
            return self.transport(req,timeout)
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            summary=run(self.p,'small','http://localhost',self.o)
        self.assertEqual(self.sent,2)
        self.assertEqual(summary['planned_questions'],2)
        self.assertEqual(summary['questions'],2)
        self.assertEqual(summary['binding_passes'],1)
        self.assertEqual(summary['invalid_responses'],1)

    def test_span_inventory_is_rejected_even_when_all_ids_exist(self):
        self.packet['source_text']='One\nTwo\nThree\nFour'
        self.packet['source_text_sha256']=hashlib.sha256(self.packet['source_text'].encode()).hexdigest()
        self.p.write_text(json.dumps(self.packet))
        def transport(req,timeout=None):
            if isinstance(req,str):return self.response({'loaded_model':'small'})
            prompt=json.loads(req.data)['messages'][0]['content']
            self.assertIn('one to 3 span IDs',prompt)
            return self.response({'model':'small','choices':[{'finish_reason':'stop','message':{
                'content':json.dumps({'value':'NO','source_span_ids':['1','2','3','4'],'rationale':'All lines.'})}}]})
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            result=run(self.p,'small','http://localhost',self.o,evidence_mode='span_ids')
        self.assertEqual(result['binding_passes'],0)
        self.assertIn('INVALID_SPAN_COUNT',json.loads(self.o.read_text().splitlines()[-2])['validation_errors'])

    def test_transport_timeout_still_stops_without_retry_or_next_question(self):
        self.packet['questions'].append({**self.packet['questions'][0],'id':'second'})
        self.p.write_text(json.dumps(self.packet))
        def transport(req,timeout=None):
            if isinstance(req,str):return self.response({'loaded_model':'small'})
            self.sent+=1
            raise TimeoutError('Unknown server completion state')
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            with self.assertRaises(TimeoutError):run(self.p,'small','http://localhost',self.o)
        self.assertEqual(self.sent,1)
        self.assertEqual(json.loads(self.o.read_text().splitlines()[-1])['state'],'FAILED_OR_UNRESOLVED')

    def test_structured_output_is_explicit_and_bound_to_this_question_and_source(self):
        def transport(req,timeout=None):
            if isinstance(req,str):return self.response({'loaded_model':'small'})
            payload=json.loads(req.data)
            schema=payload['response_format']['json_schema']['schema']
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(schema['properties']['value']['enum'],['NO','NO_INFORMATION'])
            self.assertEqual(schema['properties']['source_span_ids']['items']['enum'],['1'])
            self.assertEqual(schema['properties']['source_span_ids']['maxItems'],3)
            return self.response({'model':'small','choices':[{'finish_reason':'stop','message':{
                'content':json.dumps({'value':'NO','source_span_ids':['1'],'rationale':'Explicit statement.'})}}]})
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            result=run(self.p,'small','http://localhost',self.o,evidence_mode='span_ids',structured_output=True)
        self.assertEqual(result['binding_passes'],1)
        self.assertFalse(result['semantic_acceptance'])

    def test_block_spans_preserve_every_source_character_and_disambiguate_ids(self):
        text='Study heading\nInter-rater consistency\nF\n4.3\n'+('Long sentence '*150)+'\nEnd.'
        spans=source_spans(text,'blocks',120)
        self.assertEqual(''.join(spans.values()),text)
        self.assertTrue(all(k.startswith('b') and len(v)<=120 for k,v in spans.items()))
        self.assertEqual(spans,source_spans(text,'blocks',120))
        self.assertIn('consistency\nF\n4.3',spans['b0001'])

    def test_block_evidence_is_resolved_from_the_bound_source_view(self):
        def transport(req,timeout=None):
            if isinstance(req,str):return self.response({'loaded_model':'small'})
            return self.response({'model':'small','choices':[{'finish_reason':'stop','message':{
                'content':json.dumps({'value':'NO','source_span_ids':['b0001'],'rationale':'Explicit negative.'})}}]})
        with patch('evaluate_packet.urllib.request.urlopen',side_effect=transport):
            summary=run(self.p,'small','http://localhost',self.o,evidence_mode='span_ids',span_layout='blocks')
        self.assertEqual(summary['binding_passes'],1)
        row=json.loads(self.o.read_text().splitlines()[-2])
        self.assertEqual(row['resolved_evidence'][0]['quote'],self.source)
        self.assertEqual(row['span_layout'],'blocks')
        self.assertEqual(len(row['source_view_sha256']),64)


if __name__=='__main__':unittest.main()
