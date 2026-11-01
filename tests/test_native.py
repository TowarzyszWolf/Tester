import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import Store, validate
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
    def test_all_25_reports_exact_scores_and_database_roundtrip(self):
        seen, all_rows = set(), []
        for prefix, edition, scores in CASES:
            with self.subTest(prefix=prefix):
                path = fixture(prefix)
                seen.add(path)
                rows = parse_report(path.read_bytes())
                self.assertEqual([r['score'] for r in rows], scores)
                for row in rows:
                    self.assertEqual(row['edition'], edition)
                    row = validate(row | {'source_file': path.name})
                    self.assertEqual(row['measured_at'], '')
                    all_rows.append(row)
        self.assertEqual(seen, set(FIXTURES.glob('*.txt')))
        self.assertEqual(len(all_rows), 62)
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'native.sqlite3')
            store.add(all_rows)
            restored = Store(store.path).list({})
            self.assertEqual(len(restored), 62)
            self.assertEqual(len({r['source_file'] for r in restored}), 24)
            self.assertEqual(len(store.list({'edition': '2024'})), 0)

    def test_old_shading_modes_and_units_stay_distinct(self):
        rows = parse_report(fixture('Apple Power Mac G4-CR2003').read_bytes())
        self.assertEqual([r['test'] for r in rows], ['CPU Single Core', 'Shading (CINEMA 4D)', 'OpenGL Software Lighting', 'OpenGL Hardware Lighting'])
        self.assertEqual([r['unit'] for r in rows], ['CB-CPU', 'CB-GFX', 'CB-GFX', 'CB-GFX'])
        self.assertEqual(rows[0]['clock_mhz'], 400)
        self.assertNotIn('cores', rows[0])

    def test_logical_threads_and_precision(self):
        row = parse_report(fixture('15_037_RC83328demo_4C').read_bytes())[1]
        self.assertEqual(validate(row)['threads'], 8)
        self.assertEqual(validate(row)['cores'], 4)
        self.assertEqual(row['score'], 661.868123)
        self.assertEqual(row['benchmark_version'], '15.037')
        self.assertEqual(row['unit'], 'cb')
        self.assertEqual(row['cpu'], 'Intel Core i7-3770 CPU')

    def test_peak_and_arrays_are_metadata_only(self):
        rows = parse_report(fixture('23_200_4C').read_bytes())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['score'], 3669.154145)
        self.assertIn('CBCPUXPEAK=3671.255383', rows[0]['notes'])
        self.assertNotIn('MHZ_ESTIMATE', rows[0]['notes'])

    def test_native_gpu_rendering_is_not_opengl(self):
        text = fixture('2026_100_').read_text().replace('CBGPU=0.000000', 'CBGPU=123.45')
        rows = parse_report(text.encode())
        self.assertEqual(rows[-1]['test'], 'GPU')
        self.assertEqual(rows[-1]['unit'], 'pts')

    def test_mac_line_endings_and_ghz_comma(self):
        rows = parse_report(fixture('Dell ChromeBook').read_bytes())
        self.assertEqual(rows[0]['clock_mhz'], 1600)
        text = fixture('Apple Power Mac G4-CR2003').read_text()
        for ending in ('\r', '\n', '\r\n', '\r\r\n'):
            self.assertEqual(len(parse_report(text.replace('\n', ending).encode())), 4)
        self.assertEqual(len(parse_report(text.encode('utf-16'))), 4)

    def test_invalid_native_score_rejected(self):
        body = fixture('23_200_4C').read_bytes().replace(b'CBCPUX=3669.154145', b'CBCPUX=nan')
        with self.assertRaises(ValueError):
            parse_report(body)

    def test_old_database_migration_preserves_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'old.sqlite3'
            with sqlite3.connect(path) as conn:
                conn.executescript("""
                CREATE TABLE results(id INTEGER PRIMARY KEY, edition TEXT, test TEXT CHECK(test IN ('CPU Single Core','CPU Multi Core','GPU')), score REAL, unit TEXT CHECK(unit IN ('pts','cb','fps')), cpu TEXT, gpu TEXT, threads INTEGER, os TEXT, measured_at TEXT, notes TEXT, created_at TEXT);
                CREATE INDEX idx_results_group ON results(edition,test,unit);
                INSERT INTO results VALUES(77,'R23','CPU Multi Core',100,'pts','Existing CPU','',4,'Linux','2026-01-01','Keep me','timestamp');
                """)
            store = Store(path)
            row = store.list({})[0]
            self.assertEqual((row['id'], row['notes'], row['created_at']), (77, 'Keep me', 'timestamp'))
            store.add(parse_report(fixture('Apple Power Mac G4-CR2003').read_bytes()))
            self.assertEqual(len(Store(path).list({})), 5)
