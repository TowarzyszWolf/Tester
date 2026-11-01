import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import Store, validate
from records import METRICS
from importers import parse_report

FIXTURES = Path(__file__).parent / 'fixtures'
# Independently transcribed from the supplied reports, not computed by the parser.
CASES = [
    ('11_529_CB25720demo_1C_1T', 'R11.5', [0.222723, 0.222723, 4.366930]),
    ('11_529_CB25720demo_1C_2T', 'R11.5', [0.223569]),
    ('15_037_RC83328demo_2C', 'R15', [128.585114]),
    ('15_037_RC83328demo_4C', 'R15', [138.354208, 661.868123, 19.044430]),
    ('15_038_', 'R15', [18.031371, 18.031371, 3.631861]),
    ('2024_', '2024', []),
    ('2026_100_', '2026', [417.697903, 1510.767420]),
    ('2026_103_', '2026', [385.863225]),
    ('20_030_12C', 'R20', [191.293524, 2704.755553]),
    ('20_030_2C', 'R20', [280.163109, 540.734733]),
    ('20_040_10C', 'R20', [647.807770, 2163.443728]),
    ('20_040_2C_1600', 'R20', [49.256796, 72.734447]),
    ('20_040_2C_4T', 'R20', [227.617307, 567.140060]),
    ('23_105_', 'R23', [750.488513, 3891.028230]),
    ('23_200_2C', 'R23', [734.509280]),
    ('23_200_4C', 'R23', [3669.154145]),
    ('Acer Nitro', 'R10', [10737, 57586, 13705]),
    ('Apple MacBook 13 Aluminum', 'R9.5', [336, 622, 433, 1663, 3231]),
    ('Apple MacBook 13 Early', 'R9.5', [199, 276, 247, 724, 1252]),
    ('Apple Power Mac G4 (AGP', 'R9.5', [45, 54, 149, 94]),
    ('Apple Power Mac G4-CR2003', '2003', [42, 55, 142, 80]),
    ('Apple PowerMac G4 (AGP Graphics) PowerPC G4.txt', 'R9.5', [52, 61, 166, 106]),
    ('Apple PowerMac G4 (AGP Graphics) PowerPC G4_CB', 'R10', [307, 41]),
    ('Apple iBook', 'R9.5', [73, 78, 177, 124]),
    ('Dell ChromeBook', 'R10', [1218, 1837, 1536]),
]


def fixture(prefix):
    matches = [p for p in FIXTURES.glob('*.txt') if p.name.startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError(f'Ambiguous fixture {prefix}: {matches}')
    return matches[0]


class NativeTests(unittest.TestCase):
    def test_all_25_files_are_25_records_with_62_measurements(self):
        seen,all_rows=set(),[]
        for prefix,edition,scores in CASES:
            with self.subTest(prefix=prefix):
                path=fixture(prefix);seen.add(path)
                records=parse_report(path.read_bytes())
                self.assertEqual(len(records),1)
                row=validate(records[0] | {'source_file':path.name})
                self.assertEqual([row[k] for k in METRICS if row[k] is not None],scores)
                self.assertEqual(row['edition'],edition)
                self.assertEqual(row['measured_at'],'')
                all_rows.append(row)
        self.assertEqual(seen,set(FIXTURES.glob('*.txt')))
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'native.sqlite3');self.assertEqual(store.add(all_rows),25)
            rows=Store(store.path).list({})
            self.assertEqual(len(rows),25)
            self.assertEqual(sum(r[k] is not None for r in rows for k in METRICS),62)
            self.assertEqual(len(store.list({'edition':'2024'})),1)

    def test_legacy_shading_is_columns_not_rows(self):
        row=parse_report(fixture('Apple Power Mac G4-CR2003').read_bytes())[0]
        self.assertEqual([row[k] for k in ('cpu_single','shading','opengl_software','opengl_hardware')],[42,55,142,80])
        self.assertEqual(row['cpu_single_unit'],'CB-CPU')
        self.assertEqual(row['shading_unit'],'CB-GFX')
        self.assertEqual(row['clock_mhz'],400)

    def test_threads_precision_and_versions(self):
        row=validate(parse_report(fixture('15_037_RC83328demo_4C').read_bytes())[0])
        self.assertEqual((row['threads'],row['cores'],row['cpu_multi']),(8,4,661.868123))
        self.assertEqual(row['benchmark_version'],'15.037')
        self.assertEqual(row['cpu_multi_unit'],'cb')
        self.assertEqual(row['cpu'],'Intel Core i7-3770 CPU')

    def test_peaks_not_extra_records(self):
        rows=parse_report(fixture('23_200_4C').read_bytes())
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['cpu_multi'],3669.154145)
        self.assertIn('CBCPUXPEAK=3671.255383',rows[0]['notes'])

    def test_gpu_rendering_not_opengl(self):
        text=fixture('2026_100_').read_text().replace('CBGPU=0.000000','CBGPU=123.45')
        row=parse_report(text.encode())[0]
        self.assertEqual(row['gpu_score'],123.45)
        self.assertEqual(row['gpu_score_unit'],'pts')
        self.assertNotIn('opengl',row)

    def test_line_endings_and_utf16(self):
        text=fixture('Apple Power Mac G4-CR2003').read_text()
        for ending in ('\r','\n','\r\n','\r\r\n'):
            self.assertEqual(parse_report(text.replace('\n',ending).encode())[0]['opengl_hardware'],80)
        self.assertEqual(parse_report(text.encode('utf-16'))[0]['cpu_single'],42)
        self.assertEqual(parse_report(fixture('Dell ChromeBook').read_bytes())[0]['clock_mhz'],1600)

    def test_invalid_native_score_rejected(self):
        body=fixture('23_200_4C').read_bytes().replace(b'CBCPUX=3669.154145',b'CBCPUX=nan')
        with self.assertRaises(ValueError):parse_report(body)

    def test_legacy_migration_backup_and_repeated_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.sqlite3'
            with sqlite3.connect(path) as conn:
                conn.execute('CREATE TABLE results(id INTEGER PRIMARY KEY, edition TEXT,test TEXT,score REAL,unit TEXT,cpu TEXT,gpu TEXT,source_file TEXT,benchmark_version TEXT,notes TEXT,created_at TEXT)')
                for i,(mode,score,unit) in enumerate([('CPU Single Core',100,'pts'),('CPU Multi Core',200,'pts'),('GPU',300,'pts')]*2,1):
                    conn.execute('INSERT INTO results VALUES(?,?,?,?,?,?,?,?,?,?,?)',(i,'R23',mode,score,unit,'CPU','GPU','same.txt','23.200',mode,'2026-01-01T01:01:01Z'))
                conn.execute("INSERT INTO results VALUES(77,'R23','CPU Multi Core',99,'pts','Existing CPU','','','','Keep me','timestamp')")
            store=Store(path);rows=store.list({})
            self.assertEqual(len(rows),3)
            reports=[r for r in rows if r['source_file']=='same.txt']
            self.assertEqual(len(reports),2)
            self.assertEqual([r['id'] for r in reports],[1,4])
            self.assertEqual(reports[0]['gpu_score'],300)
            kept=next(r for r in rows if r['id']==77)
            self.assertEqual((kept['notes'],kept['created_at']),('Keep me','timestamp'))
            self.assertTrue(store.backup_path.exists())
            with sqlite3.connect(store.backup_path) as backup:
                self.assertEqual(backup.execute('SELECT count(*) FROM results').fetchone()[0],7)
            self.assertIsNone(Store(path).backup_path)

    def test_failed_migration_leaves_original_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.sqlite3'
            with sqlite3.connect(path) as conn:
                conn.executescript("CREATE TABLE results(id INTEGER PRIMARY KEY,edition TEXT,test TEXT,score REAL,unit TEXT,cpu TEXT); INSERT INTO results VALUES(1,'R23','UNKNOWN',100,'pts','CPU');")
            with self.assertRaises(ValueError):Store(path)
            with sqlite3.connect(path) as conn:
                self.assertEqual(conn.execute('SELECT test FROM results').fetchone()[0],'UNKNOWN')
