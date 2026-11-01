import re
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import Store, validate
from importers import parse_report
from test_native import fixture


def report(edition, mhz, estimate):
    prefix='2024_' if edition=='2024' else '2026_100_'
    text=fixture(prefix).read_text()
    text='\n'.join(line for line in text.splitlines() if not line.startswith(('MHZ=','MHZ_ESTIMATE=')))
    if mhz is not None:
        text+='\nMHZ='+mhz
    if estimate is not None:
        text+='\nMHZ_ESTIMATE='+estimate
    return parse_report(text.encode())[0]


class ClockTests(unittest.TestCase):
    def test_valid_mhz_has_priority(self):
        for edition in ('2024','2026'):
            with self.subTest(edition=edition):
                row=validate(report(edition,'3000.000000','3900.50'))
                self.assertEqual(row['clock_mhz'],3000)
                self.assertNotIn('Taktowanie szacowane',row['notes'])

    def test_invalid_or_missing_mhz_uses_estimate(self):
        for edition in ('2024','2026'):
            for bad in (None,'','0','-1','nan','NaN','inf','-inf','1e309','unknown'):
                with self.subTest(edition=edition,mhz=bad):
                    row=validate(report(edition,bad,'3456.78'))
                    self.assertEqual(row['clock_mhz'],3456.78)
                    self.assertIn('Taktowanie szacowane: MHZ_ESTIMATE=',row['notes'])

    def test_both_invalid_remain_unknown_without_rejecting_report(self):
        for edition in ('2024','2026'):
            for bad in (None,'','0','-1','nan','inf','-inf','1e309','unknown'):
                with self.subTest(edition=edition,estimate=bad):
                    row=validate(report(edition,'0',bad))
                    self.assertIsNone(row['clock_mhz'])
                    self.assertIn('Brak prawidłowego taktowania',row['notes'])

    def test_valid_mhz_ignores_invalid_estimate(self):
        for edition in ('2024','2026'):
            row=validate(report(edition,'2310','inf'))
            self.assertEqual(row['clock_mhz'],2310)

    def test_decimal_comma_and_empty_report(self):
        row=validate(report('2024','0','2456,75'))
        self.assertEqual(row['clock_mhz'],2456.75)
        self.assertIsNone(row['cpu_multi'])
        self.assertIn('MHZ_ESTIMATE=',row['notes'])

    def test_older_cinebench_does_not_use_estimate(self):
        text=fixture('23_200_4C').read_text()
        text=re.sub(r'(?m)^MHZ=.*$', 'MHZ=0',text)
        text=re.sub(r'(?m)^MHZ_ESTIMATE=.*$', 'MHZ_ESTIMATE=3500',text)
        with self.assertRaises(ValueError):validate(parse_report(text.encode())[0])

    def test_estimated_clock_survives_database_roundtrip(self):
        row=report('2026','nan','3278.25')
        with TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'results.sqlite3')
            self.assertEqual(store.add([row]),1)
            saved=Store(store.path).list({})[0]
            self.assertEqual(saved['clock_mhz'],3278.25)
            self.assertEqual(saved['cpu_multi'],1510.767420)
            self.assertIn('Taktowanie szacowane',saved['notes'])
