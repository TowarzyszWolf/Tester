from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from urllib.parse import urlencode

from app import Store
from manufacturers import manufacturer, UNKNOWN
from rankings import ranking
from test_app import result
import test_app


class ManufacturerTests(unittest.TestCase):
    def test_cpu_names(self):
        cases=[('Intel(R) Core(TM) i7-3770 CPU','Intel'),('Core i5-5300U','Intel'),('Xeon E3-1505M v6','Intel'),('AMD G-T44R Processor','AMD'),('Ryzen 9 7950X','AMD'),('AMD Athlon(tm) II X2 250 Processor','AMD'),('EPYC 9654','AMD'),('Apple M4 Pro','Apple'),('M1 Max','Apple'),('Qualcomm Snapdragon X Elite','Qualcomm'),('VIA C7','VIA'),('PowerPC G4 (7400)',UNKNOWN),('Unknown CPU',UNKNOWN)]
        for model,expected in cases:
            with self.subTest(model=model):self.assertEqual(manufacturer(model,'cpu'),expected)

    def test_gpu_chip_manufacturer_not_board_partner(self):
        cases=[('ASUS GeForce RTX 4090','NVIDIA'),('GeForce GT 620/PCIe/SSE2','NVIDIA'),('Quadro P2000','NVIDIA'),('Intel(R) HD Graphics P630','Intel'),('Intel Iris Xe','Intel'),('Intel Arc A770','Intel'),('AMD Radeon HD Graphics','AMD'),('Radeon RX 7900 XTX','AMD'),('ATi Rage 128 Pro OpenGL Engine','ATI'),('ATI Mobility Radeon 7500','ATI'),('Apple M4','Apple'),('GDI Generic',UNKNOWN),('Unknown GPU',UNKNOWN)]
        for model,expected in cases:
            with self.subTest(model=model):self.assertEqual(manufacturer(model,'gpu'),expected)

    def test_manufacturer_case_and_whitespace(self):
        self.assertEqual(manufacturer('  aMd   Ryzen 9 ','cpu'),'AMD')
        self.assertEqual(manufacturer('Advanced_Micro_Devices Radeon','gpu'),'AMD')


class ManufacturerRankingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'brands.sqlite3')
    def tearDown(self):self.tmp.cleanup()
    def data(self,**filters):return ranking(self.store.list({}),{'device':'cpu',**filters})

    def test_sort_brand_both_directions_and_unknown_last_preserves_rank(self):
        self.store.add([result(cpu='AMD Ryzen 9',cpu_multi=10),result(cpu='Apple M4',cpu_multi=20),result(cpu='Intel Core i7',cpu_multi=30),result(cpu='Unknown CPU',cpu_multi=99)])
        asc=self.data(sort='manufacturer_asc')
        self.assertEqual([r['manufacturer'] for r in asc['rows']],['AMD','Apple','Intel',UNKNOWN])
        self.assertEqual([r['rank'] for r in asc['rows']],[4,3,2,1])
        desc=self.data(sort='manufacturer_desc')
        self.assertEqual([r['manufacturer'] for r in desc['rows']],['Intel','Apple','AMD',UNKNOWN])

    def test_filter_manufacturer_keeps_global_rank_and_list_of_brands(self):
        self.store.add([result(cpu='AMD Ryzen 9',cpu_multi=100),result(cpu='Intel Core i7',cpu_multi=200)])
        data=self.data(manufacturer='amd')
        self.assertEqual(len(data['rows']),1)
        self.assertEqual(data['rows'][0]['rank'],2)
        self.assertEqual(data['selected']['manufacturer'],'AMD')
        self.assertEqual(data['manufacturers'],['AMD','Intel'])

    def test_same_brand_sorted_by_score(self):
        self.store.add([result(cpu='Intel Core i7',cpu_multi=100),result(cpu='AMD Ryzen 9',cpu_multi=150),result(cpu='Intel Xeon',cpu_multi=200)])
        self.assertEqual([r['model'] for r in self.data(sort='manufacturer')['rows']],['AMD Ryzen 9','Intel Xeon','Intel Core i7'])

    def test_cpu_point_labels_and_builds_share_one_edition_ranking(self):
        for unit,version,score in [('pts','23.105',100),('cb','23.200',200),('CB-CPU','23.300',300)]:
            self.store.add([result(cpu='AMD Ryzen 9',cpu_multi=score,cpu_multi_unit=unit,benchmark_version=version)])
        data=self.data()
        self.assertEqual((data['rows'][0]['score'],data['rows'][0]['count']),(200,3))
        self.assertEqual(data['unit'],'pts')
        self.assertEqual({r['cpu_multi_unit'] for r in self.store.list({})},{'pts','cb','CB-CPU'})

    def test_fixed_cpu_units_for_legacy_and_modern_editions(self):
        self.store.add([result(edition='R15',cpu_multi_unit='pts'),result(edition='2003',cpu_multi_unit='cb'),result(edition='2026',cpu_multi_unit='pts')])
        for edition,unit in [('R15','cb'),('2003','CB-CPU'),('2026','pts')]:
            self.assertEqual(self.data(edition=edition)['unit'],unit)
            self.assertEqual(self.data(edition=edition)['rows'][0]['count'],1)

    def test_gpu_brand_sorting_and_incompatible_units_not_mixed(self):
        self.store.add([result(gpu='GeForce RTX 4090',gpu_score=100,gpu_score_unit='pts'),result(gpu='AMD Radeon RX 7900',gpu_score=200,gpu_score_unit='pts'),result(gpu='Intel Arc',gpu_score=300,gpu_score_unit='fps')])
        data=ranking(self.store.list({}),{'device':'gpu','sort':'manufacturer_asc'})
        self.assertEqual([r['manufacturer'] for r in data['rows']],['AMD','NVIDIA'])
        self.assertEqual(data['excluded_unit_count'],1)


class ManufacturerHTTPTests(unittest.TestCase):
    setUpClass=classmethod(test_app.HTTPTests.setUpClass.__func__)
    tearDownClass=classmethod(test_app.HTTPTests.tearDownClass.__func__)
    request=test_app.HTTPTests.request

    def test_api_edition_ranking_brand_sort_and_exact_history(self):
        self.store.add([result(cpu='Intel Core i7',benchmark_version='23.105',cpu_multi=100),result(cpu='Intel Core i7',benchmark_version='23.200',cpu_multi=300),result(cpu='AMD Ryzen 9',cpu_multi=150)])
        with self.request('/api/rankings?device=cpu&edition=R23&sort=manufacturer_asc') as response:data=json.load(response)
        self.assertEqual([r['manufacturer'] for r in data['rows']],['AMD','Intel'])
        self.assertEqual(data['rows'][1]['score'],200)
        self.assertNotIn('benchmark_version',data['selected'])
        self.assertNotIn('unit',data['selected'])
        with self.request('/api/hardware?'+urlencode({'device':'cpu','model':'Intel Core i7'})) as response:history=json.load(response)
        self.assertEqual((history['manufacturer'],history['record_count']),('Intel',2))
        for row in self.store.list({}):self.store.delete(row['id'])
