import json
from pathlib import Path
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest

from app import Store
from test_app import result
import test_app


class FirstStartTests(unittest.TestCase):
    def test_missing_database_and_directories_created_and_restart_preserves_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'new'/'nested'/'cinebench.sqlite3'
            self.assertFalse(path.exists())
            store=Store(path)
            self.assertTrue(store.created)
            self.assertEqual(store.status()['record_count'],0)
            self.assertEqual(store.list({}),[])
            with sqlite3.connect(':memory:') as snapshot:
                snapshot.deserialize(store.snapshot())
                self.assertEqual(snapshot.execute('SELECT count(*) FROM results').fetchone()[0],0)
            store.add([result()])
            reopened=Store(path)
            self.assertFalse(reopened.created)
            self.assertEqual(reopened.status()['record_count'],1)

    def test_zero_byte_database_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'empty.sqlite3';path.touch()
            self.assertTrue(Store(path).created)
            self.assertEqual(Store(path).status()['record_count'],0)

    def test_corrupted_database_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'broken.sqlite3';path.write_bytes(b'Not a database')
            with self.assertRaises(sqlite3.DatabaseError):Store(path)
            self.assertEqual(path.read_bytes(),b'Not a database')


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'db.sqlite3')
    def tearDown(self):self.tmp.cleanup()

    def test_valid_reports_saved_despite_invalid_file(self):
        response=self.store.import_batch([
            {'token':'file-1','record':result(source_file='a.txt')},
            {'token':'file-2','record':result(cpu='',source_file='bad.txt')},
            {'token':'file-3','record':result(source_file='c.txt')},
        ])
        self.assertEqual((response['added'],response['failed']),(2,1))
        self.assertEqual([r['token'] for r in response['items']],['file-1','file-2','file-3'])
        self.assertEqual(self.store.status()['record_count'],2)
        fixed=self.store.import_batch([{'token':'file-2','record':result(source_file='bad.txt')}])
        self.assertEqual(fixed['added'],1)

    def test_retry_after_lost_response_does_not_duplicate(self):
        payload=[{'token':'file-1','record':result(cpu_single=100,cpu_single_unit='pts')}]
        self.assertEqual(self.store.import_batch(payload)['added'],1)
        response=Store(self.store.path).import_batch(payload)
        self.assertEqual((response['added'],response['already_saved']),(0,1))
        self.assertEqual(self.store.status()['record_count'],1)

    def test_token_conflict_rejected(self):
        self.store.import_batch([{'token':'file-1','record':result()}])
        response=self.store.import_batch([{'token':'file-1','record':result(cpu='Different CPU')}])
        self.assertEqual(response['failed'],1)
        self.assertEqual(self.store.status()['record_count'],1)

    def test_concurrent_retry_is_idempotent(self):
        payload=[{'token':'concurrent-1','record':result()}]
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda _:self.store.import_batch(payload),range(2)))
        self.assertEqual(sum(r['added'] for r in outcomes),1)
        self.assertEqual(sum(r['already_saved'] for r in outcomes),1)
        self.assertEqual(self.store.status()['record_count'],1)

    def test_delete_and_receipt_foreign_key(self):
        payload=[{'token':'file-1','record':result()}]
        saved=self.store.import_batch(payload)
        self.store.delete(saved['items'][0]['id'])
        self.assertEqual(self.store.import_batch(payload)['already_saved'],1)
        self.assertEqual(self.store.status()['record_count'],0)

    def test_invalid_batch_and_items(self):
        for payload in (None,{},[],[{}]*101):
            with self.subTest(payload=type(payload)),self.assertRaises(ValueError):self.store.import_batch(payload)
        response=self.store.import_batch([None,{'token':[], 'record':result()},{'token':'ok','record':None}])
        self.assertEqual(response['failed'],3)


class BatchHTTPTests(unittest.TestCase):
    setUpClass = classmethod(test_app.HTTPTests.setUpClass.__func__)
    tearDownClass = classmethod(test_app.HTTPTests.tearDownClass.__func__)
    request = test_app.HTTPTests.request

    def test_batch_api_and_empty_status(self):
        with self.request('/api/status') as response:
            initial=json.load(response)['record_count']
        payload=[{'token':'http-1','record':result(source_file='one.txt')},{'token':'http-2','record':result(cpu='',source_file='invalid.txt')}]
        headers={'X-Cinebench-Client':'1'}
        with self.request('/api/import-batch',json.dumps(payload).encode(),'POST',headers) as response:
            saved=json.load(response)
        self.assertEqual((saved['added'],saved['failed']),(1,1))
        with self.request('/api/import-batch',json.dumps(payload).encode(),'POST',headers) as response:
            self.assertEqual(json.load(response)['already_saved'],1)
        with self.request('/api/status') as response:
            self.assertEqual(json.load(response)['record_count'],initial+1)
        self.store.delete(saved['items'][0]['id'])
