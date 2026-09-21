import hashlib
import base64
import io
import json
import tempfile
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
from unittest.mock import patch
from evaluate_packet import run, source_spans, http_error_evidence, HTTP_ERROR_BODY_LIMIT


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

    def test_http_failure_preserves_wire_body_and_stops_before_next_question(self):
        body = b'{"error":"synthetic allocation failure"}'
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args): pass
            def do_GET(self):
                payload = b'{"loaded_model":"small"}'
                self.send_response(200);self.end_headers();self.wfile.write(payload)
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(500);self.end_headers();self.wfile.write(body)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True);thread.start()
        self.packet['questions'].append({**self.packet['questions'][0], 'id':'second'})
        self.p.write_text(json.dumps(self.packet))
        try:
            with self.assertRaises(urllib.error.HTTPError):
                run(self.p, 'small', f'http://127.0.0.1:{server.server_port}', self.o)
        finally:
            server.shutdown();server.server_close();thread.join()
        self.assertEqual(len(received), 1)
        rows = [json.loads(line) for line in self.o.read_text().splitlines()]
        self.assertEqual([row['state'] for row in rows], ['REQUEST_STARTED','FAILED_HTTP_RESPONSE'])
        self.assertEqual(rows[-1]['question_id'], 'allocation')
        self.assertEqual(rows[-1]['planned_questions'], 2)
        evidence = rows[-1]['http_error']
        self.assertEqual(evidence['status'], 500)
        self.assertEqual(base64.b64decode(evidence['body_base64']), body)
        self.assertEqual(evidence['captured_sha256'], hashlib.sha256(body).hexdigest())
        self.assertFalse(evidence['body_truncated'])
        self.assertFalse(evidence['backend_completion_confirmed'])
        self.assertFalse(rows[-1]['request_resolved'])

    def test_http_error_capture_is_bounded_and_hashes_only_captured_bytes(self):
        body = b'x' * (HTTP_ERROR_BODY_LIMIT + 100)
        error = urllib.error.HTTPError('http://fixture', 503, 'Unavailable', {}, io.BytesIO(body))
        evidence = http_error_evidence(error)
        captured = base64.b64decode(evidence['body_base64'])
        self.assertEqual(captured, body[:HTTP_ERROR_BODY_LIMIT])
        self.assertEqual(evidence['captured_bytes'], HTTP_ERROR_BODY_LIMIT)
        self.assertEqual(evidence['captured_sha256'], hashlib.sha256(captured).hexdigest())
        self.assertTrue(evidence['body_truncated'])

    def test_http_status_is_retained_when_error_body_cannot_be_read(self):
        class BrokenBody(io.BytesIO):
            def read(self, _size=-1): raise TimeoutError('body unavailable')
        error = urllib.error.HTTPError('http://fixture', 500, 'Failure', {}, BrokenBody())
        evidence = http_error_evidence(error)
        self.assertEqual(evidence['status'], 500)
        self.assertEqual(evidence['body_read_error'], 'body unavailable')
        self.assertNotIn('body_base64', evidence)
        self.assertFalse(evidence['backend_completion_confirmed'])

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
