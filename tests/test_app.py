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
from urllib.request import Request, urlopen
from app import FIELDS, Store, handler_for, parse_csv, validate
from importers import parse_report


def result(**changes):
    return dict(edition='R23', test='CPU Multi Core', score='12345.5', unit='pts', cpu='Ryzen 9', gpu='', threads='32', os='Linux', measured_at='2026-11-01', notes='test') | changes


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'results.sqlite3')

    def tearDown(self):
        self.tmp.cleanup()

    def test_persistent_result(self):
        self.store.add([result()])
        self.assertEqual(Store(self.store.path).list({})[0]['score'], 12345.5)

    def test_invalid_scores(self):
        for score in ('nan', 'inf', '-1', '0', 'abc'):
            with self.subTest(score=score), self.assertRaises(ValueError):
                validate(result(score=score))

    def test_gpu_requires_device(self):
        with self.assertRaises(ValueError):
            validate(result(test='GPU'))
        self.assertEqual(validate(result(test='GPU', gpu='RTX 4090'))['gpu'], 'RTX 4090')

    def test_batch_is_atomic(self):
        with self.assertRaises(ValueError):
            self.store.add([result(), result(measured_at='2026-02-30')])
        self.assertEqual(self.store.list({}), [])

    def test_filters(self):
        self.store.add([result(), result(edition='2024'), result(test='CPU Single Core')])
        self.assertEqual(len(self.store.list({'edition': 'R23', 'test': 'CPU Multi Core'})), 1)
        self.assertEqual(self.store.list({'edition': "R23' OR 1=1 --"}), [])

    def test_csv_decimal_comma_unicode(self):
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=FIELDS, delimiter=';')
        writer.writeheader()
        writer.writerow(result(score='123,45', notes='Chłodzenie; ciche\nwielowierszowe'))
        self.store.add(parse_csv(output.getvalue().encode('utf-8-sig')))
        self.assertEqual(self.store.list({})[0]['score'], 123.45)

    def test_csv_wrong_columns(self):
        with self.assertRaises(ValueError):
            parse_csv(b'cpu,score\nx,123\n')

    def test_snapshot_delete(self):
        self.store.add([result()])
        conn = sqlite3.connect(':memory:')
        conn.deserialize(self.store.snapshot())
        self.assertEqual(conn.execute('SELECT count(*) FROM results').fetchone()[0], 1)
        conn.close()
        self.assertEqual(self.store.delete(1), 1)
        self.assertEqual(self.store.list({}), [])


class ParserTests(unittest.TestCase):
    def test_text(self):
        rows = parse_report(b'CPU (Multi Core): 30000 pts\nCPU (Single Core): 2000 pts\n')
        self.assertEqual({r['test']: r['score'] for r in rows}, {'CPU Multi Core': 30000, 'CPU Single Core': 2000})

    def test_named(self):
        rows = parse_report(b'cb_cpu1=123.45;\ncb_cpux=456.78;\ncb_ogl=99.8;\n')
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[2]['unit'], 'fps')
        self.assertEqual(rows[0]['unit'], '')

    def test_json(self):
        self.assertEqual(parse_report(json.dumps({'results': [result()]}).encode())[0]['edition'], 'R23')

    def test_unknown(self):
        for body in (b'processor 7950 year 2026', b'\x00\x01\x00\x02', b'[]'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_report(body)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.tmp.name) / 'http.sqlite3')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(cls.store))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def request(self, path, body=None, method='GET', headers=None):
        return urlopen(Request(self.base + path, body, method=method, headers=headers or {}), timeout=5)

    def test_workflow(self):
        with self.request('/') as response:
            self.assertIn('Importuj plik wynikowy', response.read().decode())
        headers = {'X-Cinebench-Client': '1'}
        with self.request('/api/parse', b'CPU (Multi Core): 123 pts', 'POST', headers) as response:
            parsed = json.load(response)
        with self.request('/api/import-results', json.dumps([result(**parsed[0])]).encode(), 'POST', headers) as response:
            self.assertEqual(json.load(response)['added'], 1)
        with self.request('/api/results?edition=R23') as response:
            saved = json.load(response)
            self.assertEqual(saved[0]['score'], 123)
        with self.request('/api/export.csv?edition=R23') as response:
            self.assertEqual(len(parse_csv(response.read())), 1)
        with self.request('/api/database') as response:
            self.assertTrue(response.read().startswith(b'SQLite format 3'))
        with self.request('/api/results/' + str(saved[0]['id']), method='DELETE', headers=headers) as response:
            self.assertEqual(json.load(response)['deleted'], 1)

    def test_cross_origin_form(self):
        with self.assertRaises(HTTPError) as cm:
            self.request('/api/results', json.dumps(result()).encode(), 'POST')
        self.assertEqual(cm.exception.code, 400)

    def test_native_empty_report_and_metadata_roundtrip(self):
        from test_native import fixture
        headers = {'X-Cinebench-Client': '1'}
        with self.request('/api/parse', fixture('2024_').read_bytes(), 'POST', headers) as response:
            self.assertEqual(json.load(response), [])
        path = fixture('15_037_RC83328demo_4C')
        with self.request('/api/parse', path.read_bytes(), 'POST', headers) as response:
            rows = json.load(response)
        for row in rows:
            row['source_file'] = path.name
        with self.request('/api/import-results', json.dumps(rows).encode(), 'POST', headers) as response:
            self.assertEqual(json.load(response)['added'], 3)
        with self.request('/api/results?edition=R15&test=OpenGL') as response:
            saved = json.load(response)
            self.assertEqual(saved[0]['score'], 19.04443)
            self.assertEqual(saved[0]['source_file'], path.name)
            self.assertEqual(saved[0]['threads'], 8)
        with self.request('/api/export.csv?edition=R15') as response:
            self.assertEqual(len(parse_csv(response.read())), 3)
        for row in self.store.list({'edition': 'R15'}):
            self.store.delete(row['id'])
