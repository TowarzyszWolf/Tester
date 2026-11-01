import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import Store, validate
from importers import parse_report
from metadata import cinebench_edition, operating_system
from test_app import result
from test_native import fixture


class MetadataTests(unittest.TestCase):
    def test_os_versions(self):
        cases = [
            ('Windows 10, 64 Bit, Professional Edition (build 19045)', ('Windows', '10', '19045')),
            ('Windows 11, 64 Bit, Professional Edition (build 26100)', ('Windows', '11', '26100')),
            ('Windows 10, 64 Bit (build 26100)', ('Windows', '10', '26100')),
            ('WINDOWS 64 BIT 6.2.9200', ('Windows', '6.2.9200', '9200')),
            ('macOS: Version 10.14.6 (Build 18G6032)', ('macOS', '10.14.6', '18G6032')),
            ('OS X: Version 10.12.6 (Build 16G1815)', ('macOS', '10.12.6', '16G1815')),
            ('Mac OS X 10.4.11', ('macOS', '10.4.11', '')),
            ('OS X 32 BIT 10.4.11', ('macOS', '10.4.11', '')),
            ('64 Bit, Unknown Edition (101) (build 9200)', ('', '', '9200')),
            ('', ('', '', '')),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(tuple(operating_system(raw).values()), expected)

    def test_edition_from_full_version(self):
        for version, expected in [('2026.100','2026'), ('2024.100','2024'), ('23.200','R23'), ('20.040','R20'), ('15.037','R15'), ('11.529','R11.5'), ('9.5','R9.5'), ('R10','R10'), ('2003 v1','2003')]:
            with self.subTest(version=version):
                self.assertEqual(cinebench_edition(version), expected)
        self.assertEqual(cinebench_edition('123.400'), '')

    def test_native_without_comment_uses_c4dversion(self):
        text = fixture('23_200_4C').read_text()
        text = '\n'.join(line for line in text.splitlines() if not line.startswith('COMMENT='))
        row = parse_report(text.encode())[0]
        self.assertEqual((row['edition'], row['benchmark_version']), ('R23','23.200'))
        self.assertEqual((row['os_name'],row['os_version'],row['os_build']), ('Windows','10','19045'))

    def test_conflicting_native_versions_rejected(self):
        body = fixture('23_200_4C').read_bytes().replace(b'C4DVERSION=23.200', b'C4DVERSION=2026.100')
        with self.assertRaises(ValueError):
            parse_report(body)

    def test_manual_and_json_infer_versions(self):
        row = validate(result(edition='', benchmark_version='2026.100', os='Windows 11 (build 26100)', test='GPU', gpu=''))
        self.assertEqual(row['edition'], '2026')
        self.assertEqual(row['os_build'], '26100')
        row = validate(result(edition='2026.100'))
        self.assertEqual((row['edition'],row['benchmark_version']), ('2026','2026.100'))
        row = parse_report(json.dumps(result(edition='',benchmark_version='2026.100',os='Mac OS X 10.4.11')).encode())[0]
        self.assertEqual((row['edition'],row['os_version']), ('2026','10.4.11'))
        with self.assertRaises(ValueError):
            validate(result(edition='R23',benchmark_version='2026.100'))

    def test_v2_database_upgrade_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.sqlite3'
            with sqlite3.connect(path) as conn:
                conn.executescript('CREATE TABLE results (id INTEGER PRIMARY KEY, edition TEXT, test TEXT, score REAL, unit TEXT, cpu TEXT, gpu TEXT, threads INTEGER, os TEXT, measured_at TEXT, notes TEXT, cores INTEGER, clock_mhz REAL, benchmark_version TEXT, system_name TEXT, architecture TEXT, source_file TEXT, created_at TEXT);')
                conn.execute("INSERT INTO results (id,edition,test,score,unit,cpu,gpu,os,notes,created_at) VALUES(1,'R23','CPU Multi Core',100,'pts','CPU','','Windows 10 (build 19045)','Keep','original')")
            store=Store(path)
            row=store.list({})[0]
            self.assertEqual((row['id'],row['os_version'],row['os_build'],row['notes'],row['created_at']), (1,'10','19045','Keep','original'))
            store.add([result(test='GPU',gpu='',os='macOS: Version 10.14.6 (Build 18G6032)')])
            rows=Store(path).list({})
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]['os_version'],'10.14.6')
