import csv
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from app import FIELDS,Store,handler_for,parse_csv,validate
from records import METRICS
from importers import parse_report


def result(**changes):
    return dict(edition='R23',cpu_multi='12345.5',cpu_multi_unit='pts',cpu='Ryzen 9',gpu='',threads='32',os='Linux',measured_at='2026-11-01',notes='test') | changes


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'results.sqlite3')
    def tearDown(self):
        self.tmp.cleanup()
    def test_persistent_whole_report(self):
        self.store.add([result(cpu_single=100,cpu_single_unit='pts',gpu_score=200,gpu_score_unit='pts')])
        rows=Store(self.store.path).list({})
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['cpu_single'],rows[0]['cpu_multi'],rows[0]['gpu_score']),(100,12345.5,200))
    def test_invalid_scores(self):
        for score in ('nan','inf','-1','0','abc'):
            with self.subTest(score=score),self.assertRaises(ValueError):
                validate(result(cpu_multi=score))
    def test_gpu_optional(self):
        self.assertEqual(validate(result(gpu_score=20,gpu_score_unit='pts'))['gpu'],'')
    def test_missing_is_null_and_empty_report_valid(self):
        row=validate(result(cpu_multi=''))
        self.assertTrue(all(row[key] is None for key in METRICS))
    def test_atomic_batch(self):
        with self.assertRaises(ValueError):
            self.store.add([result(),result(measured_at='2026-02-30')])
        self.assertEqual(self.store.list({}),[])
    def test_filters_sorting_and_injection(self):
        self.store.add([result(cpu='Zen Z'),result(cpu='Alpha',gpu='ZZZ'),result(cpu='Beta',gpu='AAA',edition='2024')])
        self.assertEqual([r['cpu'] for r in self.store.list({'sort':'cpu'})],['Alpha','Beta','Zen Z'])
        self.assertEqual([r['gpu'] for r in self.store.list({'sort':'gpu','direction':'desc'})],['ZZZ','AAA',''])
        self.assertEqual(len(self.store.list({'edition':'R23'})),2)
        self.assertEqual(self.store.list({'edition':"R23' OR 1=1 --"}),[])
        self.assertEqual(len(self.store.list({'sort':'cpu; DROP TABLE results'})),3)
    def test_csv_roundtrip_unicode_and_decimal_comma(self):
        output=io.StringIO(newline='')
        writer=csv.DictWriter(output,fieldnames=FIELDS,delimiter=';')
        writer.writeheader();writer.writerow(result(cpu_multi='123,45',notes='Chłodzenie; ciche\nwielowierszowe'))
        self.store.add(parse_csv(output.getvalue().encode('utf-8-sig')))
        self.assertEqual(self.store.list({})[0]['cpu_multi'],123.45)
    def test_csv_rejects_old_split_rows(self):
        with self.assertRaises(ValueError):
            parse_csv(b'edition,cpu,test,score,unit\nR23,CPU,CPU Multi Core,123,pts\n')
    def test_snapshot_delete_whole_report(self):
        self.store.add([result(cpu_single=10,cpu_single_unit='pts')])
        with sqlite3.connect(':memory:') as conn:
            conn.deserialize(self.store.snapshot())
            self.assertEqual(conn.execute('SELECT count(*) FROM results').fetchone()[0],1)
        self.assertEqual(self.store.delete(1),1)
        self.assertEqual(self.store.list({}),[])
    def test_average_cpu_independent_of_gpu_and_nulls(self):
        self.store.add([result(cpu='  Ryzen   9 ',cpu_single=10,cpu_single_unit='pts',cpu_multi=100,gpu='A',gpu_score=1000,gpu_score_unit='pts'),result(cpu='ryzen 9',cpu_single=None,cpu_multi=200,gpu='B',gpu_score=3000,gpu_score_unit='pts')])
        rows=self.store.list({'group_by':'cpu'})
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['cpu_single'],rows[0]['cpu_multi']),(10,150))
        self.assertEqual((rows[0]['counts']['cpu_single'],rows[0]['counts']['cpu_multi']),(1,2))
        self.assertIsNone(rows[0]['gpu_score'])
        self.assertEqual(len(self.store.list({'group_by':'hardware'})),2)
    def test_average_gpu_across_cpus_no_unknown_gpu_group(self):
        self.store.add([result(cpu='A',gpu='RTX 4090',gpu_score=100,gpu_score_unit='pts'),result(cpu='B',gpu='rtx 4090',gpu_score=200,gpu_score_unit='pts'),result(gpu='',gpu_score=900,gpu_score_unit='pts')])
        rows=self.store.list({'group_by':'gpu'})
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['gpu_score'],rows[0]['report_count']),(150,2))
        self.assertIsNone(rows[0]['cpu_multi'])
    def test_average_never_mixes_versions_or_units(self):
        self.store.add([result(cpu_multi=10,benchmark_version='23.200'),result(cpu_multi=20,benchmark_version='23.105'),result(cpu_multi=30,benchmark_version='23.200',cpu_multi_unit='cb'),result(cpu_multi=40,edition='2024',benchmark_version='2024.100')])
        self.assertEqual(len(self.store.list({'group_by':'cpu'})),4)
    def test_unit_conflicts_do_not_double_count(self):
        self.store.add([result(cpu_single=1,cpu_single_unit='cb'),result(cpu_single=2,cpu_single_unit='pts'),result(cpu_single=None)])
        groups=self.store.list({'group_by':'cpu'})
        self.assertEqual(sum(r['report_count'] for r in groups),3)
        self.assertEqual(sum(r['counts']['cpu_multi'] for r in groups),3)
    def test_hardware_average_preserves_original_reports(self):
        self.store.add([result(gpu='A',cpu_multi=100),result(gpu='a',cpu_multi=200)])
        rows=self.store.list({'group_by':'hardware'})
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['cpu_multi'],150)
        self.assertEqual(len(self.store.list({})),2)


class ParserTests(unittest.TestCase):
    def test_text_one_file_one_record(self):
        rows=parse_report(b'CPU (Multi Core): 30000 pts\nCPU (Single Core): 2000 pts\nGPU: 100 pts\n')
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['cpu_multi'],rows[0]['cpu_single'],rows[0]['gpu_score']),(30000,2000,100))
    def test_json_wide_and_reject_ambiguous_files(self):
        self.assertEqual(parse_report(json.dumps(result()).encode())[0]['edition'],'R23')
        with self.assertRaises(ValueError):
            parse_report(json.dumps([result(),result()]).encode())
    def test_unknown(self):
        for body in (b'processor 7950 year 2026',b'\x00\x01\x00\x02',b'[]'):
            with self.subTest(body=body),self.assertRaises(ValueError):parse_report(body)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.store=Store(Path(cls.tmp.name)/'http.sqlite3')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(cls.store))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def request(self,path,body=None,method='GET',headers=None):
        return urlopen(Request(self.base+path,body,method=method,headers=headers or {}),timeout=5)
    def test_native_whole_record_and_csv_two_decimals(self):
        from test_native import fixture
        headers={'X-Cinebench-Client':'1'}
        path=fixture('15_037_RC83328demo_4C')
        with self.request('/api/parse',path.read_bytes(),'POST',headers) as response:rows=json.load(response)
        self.assertEqual(len(rows),1);rows[0]['source_file']=path.name
        with self.request('/api/import-results',json.dumps(rows).encode(),'POST',headers) as response:self.assertEqual(json.load(response)['added'],1)
        with self.request('/api/results?edition=R15') as response:saved=json.load(response)
        self.assertEqual(len(saved),1)
        self.assertEqual((saved[0]['cpu_single'],saved[0]['cpu_multi'],saved[0]['opengl']),(138.354208,661.868123,19.04443))
        with self.request('/api/export.csv?edition=R15') as response:
            content=response.read();self.assertIn(b'138.35',content);self.assertIn(b'661.87',content)
            self.assertEqual(len(parse_csv(content)),1)
        with self.request('/api/database') as response:self.assertTrue(response.read().startswith(b'SQLite format 3'))
        with self.request('/api/results/'+str(saved[0]['id']),method='DELETE',headers=headers) as response:self.assertEqual(json.load(response)['deleted'],1)
    def test_empty_native_report_still_one_record(self):
        from test_native import fixture
        with self.request('/api/parse',fixture('2024_').read_bytes(),'POST',{'X-Cinebench-Client':'1'}) as response:rows=json.load(response)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['edition'],'2024')
        self.assertFalse(any(rows[0].get(key) for key in METRICS))
    def test_average_api_and_export(self):
        self.store.add([result(cpu='Unique Average',cpu_multi=100.123),result(cpu='Unique Average',cpu_multi=200.456)])
        with self.request('/api/results?group_by=cpu&q=Unique%20Average&sort=cpu_multi&direction=desc') as response:rows=json.load(response)
        self.assertEqual(len(rows),1);self.assertAlmostEqual(rows[0]['cpu_multi'],150.2895)
        with self.request('/api/export.csv?group_by=cpu&q=Unique%20Average') as response:
            content=response.read().decode('utf-8-sig');self.assertIn('150.29',content);self.assertIn('cpu_multi_count',content)
        for r in self.store.list({'q':'Unique Average'}):self.store.delete(r['id'])
    def test_cross_origin_form(self):
        with self.assertRaises(HTTPError) as cm:self.request('/api/results',json.dumps(result()).encode(),'POST')
        self.assertEqual(cm.exception.code,400)
