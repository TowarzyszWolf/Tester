from pathlib import Path
from tempfile import TemporaryDirectory
import re
import unittest

from app import Store
from importers import parse_report
from rankings import hardware_history
from test_native import fixture


class HardwareInfoTests(unittest.TestCase):
    def test_filled_c4dinfo_is_read_and_trimmed(self):
        text=fixture('2026_100_').read_text().replace('C4DINFO=Dell Pro 15 PV15250','C4DINFO=  Dell Pro 15 PV15250  ')
        self.assertEqual(parse_report(text.encode())[0]['system_name'],'Dell Pro 15 PV15250')

    def test_empty_missing_and_whitespace_c4dinfo_have_default(self):
        text=fixture('23_200_4C').read_text()
        for replacement in ('C4DINFO=','C4DINFO=   \t',''):
            with self.subTest(replacement=replacement):
                body=re.sub(r'(?m)^C4DINFO=.*$',replacement,text)
                self.assertEqual(parse_report(body.encode())[0]['system_name'],'brak informacji')

    def test_report_without_measurements_also_has_default(self):
        row=parse_report(fixture('2024_').read_bytes())[0]
        self.assertEqual(row['system_name'],'brak informacji')

    def test_information_and_default_survive_sqlite_and_model_history(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'db.sqlite3';store=Store(path)
            named=parse_report(fixture('2026_100_').read_bytes())[0]
            empty=parse_report(fixture('23_200_4C').read_bytes())[0]
            store.add([named,empty]);reopened=Store(path)
            self.assertEqual({r['system_name'] for r in reopened.list({})},{'Dell Pro 15 PV15250','brak informacji'})
            history=hardware_history(reopened.list({}),'cpu',empty['cpu'])
            self.assertEqual(history['reports'][0]['system_name'],'brak informacji')

    def test_legacy_tester_information_is_preserved(self):
        row=parse_report(fixture('Acer Nitro').read_bytes())[0]
        self.assertEqual(row['system_name'],'Acer Nitro 5')
