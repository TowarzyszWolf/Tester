import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode

from app import Store
from rankings import ranking, hardware_history
from test_app import result
import test_app
from test_native import fixture


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'rank.sqlite3')
    def tearDown(self):self.tmp.cleanup()
    def reports(self):return self.store.list({})

    def test_cpu_ranking_mean_descending_normalized_name_and_counts(self):
        self.store.add([result(cpu='CPU A',cpu_multi=100),result(cpu='  cpu   a ',cpu_multi=300),result(cpu='CPU B',cpu_multi=250),result(cpu='CPU C',cpu_multi=None)])
        data=ranking(self.reports(),{'device':'cpu','edition':'R23','metric':'cpu_multi'})
        self.assertEqual([(r['model'],r['score'],r['count'],r['rank']) for r in data['rows']], [('CPU B',250,1,1),('CPU A',200,2,2)])
        self.assertEqual((data['rows'][1]['best'],data['rows'][1]['worst']),(300,100))

    def test_full_versions_units_and_metrics_do_not_mix(self):
        self.store.add([result(cpu_multi=100,benchmark_version='23.200'),result(cpu_multi=900,benchmark_version='23.105'),result(cpu_multi=5,cpu_multi_unit='cb',benchmark_version='23.200'),result(cpu_multi=9999,edition='2026',benchmark_version='2026.100')])
        data=ranking(self.reports(),dict(device='cpu',edition='R23',metric='cpu_multi',benchmark_version='23.200',unit='pts'))
        self.assertEqual(data['rows'][0]['score'],100)
        self.assertEqual(data['benchmark_versions'],['23.200','23.105'])
        self.assertEqual(set(data['units']),{'pts','cb'})
        empty=ranking(self.reports(),dict(device='cpu',edition='R23',metric='cpu_single'))
        self.assertEqual(empty['rows'],[])

    def test_gpu_ranking_independent_of_cpu_and_unknown_gpu_excluded(self):
        self.store.add([result(cpu='A',gpu='Card A',gpu_score=100,gpu_score_unit='pts'),result(cpu='B',gpu='card a',gpu_score=200,gpu_score_unit='pts'),result(gpu='',gpu_score=99999,gpu_score_unit='pts'),result(gpu='Card B',gpu_score=200,gpu_score_unit='pts')])
        data=ranking(self.reports(),{'device':'gpu'})
        self.assertEqual([(r['model'],r['score'],r['count']) for r in data['rows']],[('Card B',200,1),('Card A',150,2)])

    def test_tied_scores_have_competition_ranks(self):
        self.store.add([result(cpu='B',cpu_multi=100),result(cpu='A',cpu_multi=100),result(cpu='C',cpu_multi=90)])
        self.assertEqual([(r['model'],r['rank']) for r in ranking(self.reports(),{'device':'cpu'})['rows']],[('A',1),('B',1),('C',3)])

    def test_legacy_gpu_rankings_keep_graphics_tests_distinct(self):
        from importers import parse_report
        self.store.add(parse_report(fixture('Apple Power Mac G4-CR2003').read_bytes()))
        data=ranking(self.reports(),{'device':'gpu','edition':'2003','metric':'opengl_hardware'})
        self.assertEqual(data['selected']['unit'],'CB-GFX')
        self.assertEqual(data['rows'][0]['score'],80)
        self.assertEqual(ranking(self.reports(),{'device':'gpu','metric':'opengl_software'})['rows'][0]['score'],142)

    def test_empty_rankings_and_missing_version(self):
        for device in ('cpu','gpu'):
            self.assertEqual(ranking([],{'device':device})['rows'],[])
        self.store.add([result()])
        self.assertEqual(ranking(self.reports(),{'device':'cpu','edition':'R20'})['rows'],[])
        with self.assertRaises(ValueError):ranking(self.reports(),{'device':'invalid'})
        with self.assertRaises(ValueError):ranking(self.reports(),{'device':'cpu','metric':'gpu_score'})

    def test_default_editions_and_builds_ordered_chronologically(self):
        self.store.add([result(edition='2003'),result(edition='R23'),result(edition='2026',benchmark_version='2026.9'),result(edition='2026',benchmark_version='2026.100')])
        data=ranking(self.reports(),{'device':'cpu'})
        self.assertEqual(data['editions'],['2026','R23','2003'])
        self.assertEqual(data['selected']['benchmark_version'],'2026.100')

    def test_history_includes_all_editions_exact_model_and_original_rows(self):
        self.store.add([result(cpu='CPU A',edition='R20',benchmark_version='20.040',source_file='old.txt'),result(cpu='cpu a',edition='R23',benchmark_version='23.200',source_file='new.txt'),result(cpu='CPU A Plus'),result(cpu='Other',gpu='CPU A')])
        data=hardware_history(self.reports(),'cpu',' CPU   A ')
        self.assertEqual(data['record_count'],2)
        self.assertEqual(data['editions'],['R23','R20'])
        self.assertEqual({r['source_file'] for r in data['reports']},{'old.txt','new.txt'})
        self.assertEqual(len(data['summaries']),2)
        self.assertEqual(hardware_history(self.reports(),'cpu','missing')['reports'],[])

    def test_gpu_history_contains_full_reports_even_without_gpu_measurement(self):
        self.store.add([result(gpu='Card',edition='R15',gpu_score=100,gpu_score_unit='pts'),result(gpu='card',edition='R23',gpu_score=None),result(gpu='Card Plus')])
        data=hardware_history(self.reports(),'gpu','CARD')
        self.assertEqual(data['record_count'],2)
        self.assertEqual(data['editions'],['R23','R15'])
        self.assertTrue(all(r['cpu_multi'] is not None for r in data['reports']))
        self.assertEqual(len(data['summaries']),1)


class RankingHTTPTests(unittest.TestCase):
    setUpClass=classmethod(test_app.HTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(test_app.HTTPTests.tearDownClass.__func__)
    request=test_app.HTTPTests.request

    def test_import_automatically_updates_rankings_and_model_history(self):
        headers={'X-Cinebench-Client':'1'}
        with self.request('/api/rankings?device=cpu') as response:self.assertEqual(json.load(response)['rows'],[])
        path=fixture('15_037_RC83328demo_4C')
        with self.request('/api/parse',path.read_bytes(),'POST',headers) as response:report=json.load(response)[0]
        report['source_file']=path.name
        with self.request('/api/import-batch',json.dumps([{'token':'ranking-real-report','record':report}]).encode(),'POST',headers) as response:saved=json.load(response)
        self.assertEqual(saved['added'],1)
        with self.request('/api/rankings?device=cpu&edition=R15') as response:cpu=json.load(response)
        self.assertEqual(cpu['rows'][0]['score'],661.868123)
        with self.request('/api/rankings?device=gpu&edition=R15') as response:gpu=json.load(response)
        self.assertEqual(gpu['selected']['metric'],'opengl')
        self.assertEqual(gpu['rows'][0]['score'],19.04443)
        model=cpu['rows'][0]['model']
        self.store.add([result(cpu=model,edition='R23',benchmark_version='23.200',source_file='second.txt')])
        with self.request('/api/hardware?'+urlencode({'device':'cpu','model':model})) as response:history=json.load(response)
        self.assertEqual((history['record_count'],history['editions']),(2,['R23','R15']))
        self.store.delete(saved['items'][0]['id'])
        with self.request('/api/rankings?device=gpu&edition=R15') as response:self.assertEqual(json.load(response)['rows'],[])
        for row in self.store.list({}):self.store.delete(row['id'])

    def test_api_rejects_invalid_device_or_missing_model(self):
        for path in ('/api/rankings?device=bad','/api/rankings?device=cpu&metric=gpu_score','/api/hardware?device=cpu','/api/hardware?device=bad&model=CPU'):
            with self.subTest(path=path),self.assertRaises(HTTPError) as error:self.request(path)
            self.assertEqual(error.exception.code,400)
