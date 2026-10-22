"""Provider contract tests use a deterministic server, never pretend to be live AI."""
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
import fitz
from openpyxl import load_workbook
from speccompare.ai import AIConfig,AnalysisError,analyze_ai,decode,infer,cited,supported
from speccompare.document import read_document
from speccompare.excel import export_evidence


def field(key,value,quote,scope='model',code='ACME-A1',page=1):
    return dict(key=key,value=value,page=page,quote=quote,scope=scope,link_page=1,link_quote=code,conditions='',model_ids=[code])


def source(path):
    with fitz.open() as doc:
        page=doc.new_page()
        page.insert_text((30,40),'ACME SSD SERIES\nBrand ACME\nOrdering list\n250GB ACME-A1\n500GB ACME-A2\nSeries sequential read: Up to 5,500 MB/s\nSeries TBW: Up to 2400 TBW\nACME-A1 sequential write 2800 MB/s\nQD 32\nThread 16\nPrice: =HYPERLINK("malicious")')
        doc.save(path)
    models=[]
    for code,cap in [('ACME-A1','250GB'),('ACME-A2','500GB')]:
        models.append(dict(id=code,name=code,category='SSD',page=1,quote=cap+' '+code,fields=[field('용량',cap,cap+' '+code,code=code)]))
    shared=[field('순차읽기 속도','5,500 MB/s','Series sequential read: Up to 5,500 MB/s','family_max'),field('내구성','2400 TBW','Series TBW: Up to 2400 TBW','family_max'),field('제조사','ACME','Brand ACME','family_common')]
    for f in shared:f['model_ids']=['ACME-A1','ACME-A2']
    return dict(models=models,shared=shared)


class AI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'다른 양식.pdf';self.reply=source(self.path);self.doc=read_document(self.path)
    def tearDown(self):self.tmp.cleanup()
    def test_models_and_common_max_stay_separate(self):
        products=decode(self.doc,[self.reply]);self.assertEqual(len(products),2)
        for p in products:
            self.assertEqual(p.values['순차읽기 속도'].text,'확인 필요')
            self.assertEqual(p.values['내구성'].text,'확인 필요')
            self.assertEqual(p.values['제조사'].text,'ACME')
            self.assertEqual(p.values['제조사'].scope,'family_common')
            self.assertTrue(any(v.text=='2400 TBW' and v.scope=='family_max' for v in p.shared.values()))
    def test_hallucinated_quote_value_page_and_units_rejected(self):
        reply=copy.deepcopy(self.reply)
        for f in [field('순차쓰기 속도','9800 MB/s','ACME-A1 sequential write 2800 MB/s'),field('순차쓰기 속도','2800 MB/s','not in the PDF'),field('순차쓰기 속도','2800 MB/s','ACME-A1 sequential write 2800 MB/s',page=999),field('순차쓰기 속도','2800','ACME-A1 sequential write 2800 MB/s')]:reply['models'][0]['fields'].append(f)
        p=decode(self.doc,[reply])[0];self.assertEqual(p.values['순차쓰기 속도'].text,'확인 필요')
        self.assertFalse(supported('400 TBW','2400 TBW'));self.assertFalse(supported('1TB','11TB'))
        self.assertFalse(cited(self.doc,True,'ACME'))
    def test_model_link_does_not_convert_family_max_to_model_spec(self):
        reply=copy.deepcopy(self.reply);reply['models'][0]['fields'].append(field('순차읽기 속도','5,500 MB/s','Series sequential read: Up to 5,500 MB/s'))
        p=decode(self.doc,[reply])[0]
        self.assertEqual(p.values['순차읽기 속도'].text,'확인 필요')
        self.assertTrue(any(v.scope=='unknown' for v in p.shared.values()))
    def test_direct_model_statement_and_measurement_conditions(self):
        reply=copy.deepcopy(self.reply);f=field('순차쓰기 속도','2800 MB/s','ACME-A1 sequential write 2800 MB/s');f['conditions']='QD 32\nThread 16';reply['models'][0]['fields'].append(f)
        p=decode(self.doc,[reply])[0];self.assertEqual(p.values['순차쓰기 속도'].text,'2800 MB/s');self.assertIn('Thread 16',p.values['순차쓰기 속도'].conditions)
    def test_shared_scope_targets_only_named_models(self):
        self.reply['shared'][0]['model_ids']=['ACME-A1']
        products=decode(self.doc,[self.reply]);self.assertTrue(any('순차읽기' in k for k in products[0].shared));self.assertFalse(any('순차읽기' in k for k in products[1].shared))
    def test_no_silent_fallback_or_online_without_consent(self):
        with self.assertRaises(AnalysisError):AIConfig(provider='openai',api_key='test-only').validate()
        for endpoint in ['https://example.com','http://127.0.0.1.evil','http://user@localhost:11434','http://localhost/path']:
            with self.assertRaises(AnalysisError):AIConfig(endpoint=endpoint).validate()
        with patch('speccompare.ai.request_json',return_value={'message':{'content':'not json'}}):
            with self.assertRaises(AnalysisError):infer(AIConfig(),'test')
    def test_paid_online_api_and_cloud_models_are_blocked(self):
        from speccompare.ai import validate_local_model
        with patch('speccompare.ai.request_json') as call:
            with self.assertRaises(AnalysisError):infer(AIConfig('openai','gpt-4.1-mini',api_key='test-only',online_consent=True),'sample')
            call.assert_not_called()
        with self.assertRaises(AnalysisError):AIConfig(model='example-cloud').validate()
        with self.assertRaises(AnalysisError):validate_local_model({'remote_host':'https://cloud.example','capabilities':['vision']})
        with self.assertRaises(AnalysisError):validate_local_model({'capabilities':['completion']})
    def test_local_http_provider_complete_pipeline(self):
        calls=[];reply=self.reply
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append((self.path,data))
                raw=json.dumps({'capabilities':['vision','completion']} if self.path=='/api/show' else {'message':{'content':json.dumps(reply)}}).encode();self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:products=analyze_ai(self.path,'SSD',AIConfig(endpoint='http://127.0.0.1:'+str(server.server_port)))
        finally:server.shutdown();server.server_close();thread.join()
        self.assertEqual(len(products),2);self.assertEqual(len(calls),3)
        self.assertTrue(calls[2][1]['messages'][1]['images']);self.assertEqual(calls[0][0],'/api/show')
        self.assertEqual(products[0].values['순차읽기 속도'].text,'확인 필요')
    def test_ocr_scan_english_and_packaged_language_data(self):
        image=None
        with fitz.open() as doc:
            page=doc.new_page();page.insert_text((40,80),'SSD MODEL ACME-SCAN-1\nCapacity 2 TB\nRead 6200 MB/s',fontsize=22);image=page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png')
        scan=Path(self.tmp.name)/'스캔.pdf'
        with fitz.open() as doc:page=doc.new_page();page.insert_image(page.rect,stream=image);doc.save(scan)
        parsed=read_document(scan,ocr=True);self.assertIn('ACME-SCAN-1',parsed.text);self.assertIn('6200',parsed.text);self.assertTrue(any('OCR' in w for w in parsed.warnings))
    def test_audit_workbook_preserves_scopes_and_never_formulas(self):
        products=decode(self.doc,[self.reply]);products[0].warnings.append('test');products[0].values['가격'].text='=HYPERLINK("bad")'
        target=Path(self.tmp.name)/'근거.xlsx';export_evidence(target,products);wb=load_workbook(target)
        self.assertTrue(any('family_max' in row for row in wb['제품군 공통·미확정'].values))
        self.assertFalse(any(c.data_type=='f' for sheet in wb for row in sheet for c in row));wb.close()

    def test_qd_variants_do_not_conflict_and_conditions_remain(self):
        reply=copy.deepcopy(self.reply)
        # Each direct statement is explicitly tied to a model in its own quote.
        with fitz.open() as pdf:
            page=pdf.new_page();page.insert_text((40,40),'250GB ACME-A1\nACME-A1 Random read 22K IOPS QD 1\nACME-A1 Random read 500K IOPS QD 32')
            path=Path(self.tmp.name)/'QD.pdf';pdf.save(path)
        doc=read_document(path)
        reply['models']=reply['models'][:1];reply['shared']=[]
        for value,qd in [('22K IOPS','1'),('500K IOPS','32')]:
            f=field('랜덤읽기 속도',value,f'ACME-A1 Random read {value} QD {qd}');f['conditions']='QD '+qd;reply['models'][0]['fields'].append(f)
        p=decode(doc,[reply])[0]
        self.assertEqual(p.values['랜덤읽기 속도'].text,'500K IOPS');self.assertEqual(p.values['랜덤읽기 속도 · QD1'].text,'22K IOPS')
        self.assertEqual(p.values['랜덤읽기 속도'].conditions,'QD 32')

    def test_matrix_binding_accepts_correct_column_and_rejects_swapped_column(self):
        from speccompare.fixtures import create_capacity_fixture
        create_capacity_fixture(self.path);doc=read_document(self.path)
        models=[]
        for i in [1,2]:
            code=f'ACME-X{i}';cap=f'{i}TB';model=dict(id=code,name=code,category='SSD',page=2,quote=code,fields=[])
            f=field('용량',cap,cap,code=code,page=2);f.update(link_page=2,link_quote=code);model['fields'].append(f)
            value=['1,100K IOPS','1300K IOPS'][i-1];f=field('랜덤읽기 속도',value,value,code=code,page=1);f.update(link_page=1,link_quote=cap,conditions='QD 32\nThread 16');model['fields'].append(f);models.append(model)
        result=decode(doc,[dict(models=models,shared=[])])
        self.assertEqual(result[0].values['랜덤읽기 속도'].text,'1,100K IOPS');self.assertEqual(result[1].values['랜덤읽기 속도'].text,'1300K IOPS')
        models[0]['fields'][-1].update(value='1300K IOPS',quote='1300K IOPS')
        result=decode(doc,[dict(models=models,shared=[])])
        self.assertEqual(result[0].values['랜덤읽기 속도'].text,'확인 필요')

    def test_distinct_identifiers_with_punctuation_do_not_merge(self):
        with fitz.open() as pdf:
            page=pdf.new_page();page.insert_text((40,40),'SSD ACME-A1\nSSD ACMEA1');path=Path(self.tmp.name)/'codes.pdf';pdf.save(path)
        models=[dict(id=code,name=code,category='SSD',page=1,quote=code,fields=[]) for code in ['ACME-A1','ACMEA1']]
        self.assertEqual(len(decode(read_document(path),[dict(models=models,shared=[])])),2)

    def test_malformed_candidate_types_do_not_crash_validation(self):
        reply=copy.deepcopy(self.reply)
        reply['models'][0]['fields'] += [dict(key=[],value='x'),dict(key='가격',value='x',scope=[],page=1,quote='ACME')]
        self.assertEqual(len(decode(self.doc,[reply])),2)

    def test_long_inventory_is_split_without_omitting_pages(self):
        from speccompare.ai import inventory_blocks
        from speccompare.document import Document,Page
        text='한글 테스트 ABC 123\n'*3000
        doc=Document('sample',[Page(1,text,[]),Page(2,'TAIL-SECOND-PAGE',[])],[],[])
        blocks=inventory_blocks(doc,limit=2000)
        self.assertGreater(len(blocks),2);self.assertTrue(all(len(b.encode('utf-8'))<=2001 for b in blocks))
        combined=''.join(blocks);self.assertEqual(combined.count('한글'),3000);self.assertIn('TAIL-SECOND-PAGE',combined)
    def test_local_context_overflow_and_truncated_output_are_explicit_errors(self):
        with patch('speccompare.ai.request_json') as request:
            with self.assertRaises(AnalysisError):infer(AIConfig(),'x'*19000)
            request.assert_not_called()
        with patch('speccompare.ai.request_json',return_value={'done_reason':'length','message':{'content':json.dumps(self.reply)}}):
            with self.assertRaises(AnalysisError):infer(AIConfig(),'short')
    def test_unicode_ocr_data_is_cached_with_verified_content(self):
        from speccompare.ocr import data_path
        directory=Path(self.tmp.name)/'한글 OCR';directory.mkdir()
        for name in ['eng.traineddata','kor.traineddata']:(directory/name).write_bytes(name.encode())
        with patch('speccompare.ocr.sys.platform','win32'):
            result=data_path(directory)
        self.assertTrue(result.isascii());self.assertEqual((Path(result)/'eng.traineddata').read_bytes(),b'eng.traineddata')

    def test_cloud_backend_blocked_before_any_pdf_is_sent(self):
        with patch('speccompare.ai.request_json',return_value={'capabilities':['vision'],'remote_model':'paid'}) as call:
            with self.assertRaises(AnalysisError):analyze_ai('not-opened.pdf','SSD',AIConfig())
        self.assertEqual(call.call_count,1);self.assertEqual(call.call_args.args[1],{'model':'qwen2.5vl:3b'})
