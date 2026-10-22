"""Unseen layout variants and safety checks, separate from vendor PDF fixtures."""
import unittest
import tempfile
from pathlib import Path
import fitz
from speccompare.parser import analyze, assign
from speccompare.schema import Product, Value


def table_pdf(path,rows,xs=None,y=60):
    xs=xs or [30+i*(530/len(rows[0])) for i in range(len(rows[0])+1)]
    doc=fitz.open();page=doc.new_page()
    height=30
    for x in xs:page.draw_line((x,y),(x,y+height*len(rows)))
    for r in range(len(rows)+1):page.draw_line((xs[0],y+height*r),(xs[-1],y+height*r))
    for r,row in enumerate(rows):
        for c,value in enumerate(row):
            if value:page.insert_text((xs[c]+3,y+height*r+18),str(value),fontsize=8)
    doc.save(path);doc.close()

class Layouts(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'다른 양식.pdf'
    def tearDown(self):self.tmp.cleanup()
    def test_row_oriented_synonyms_and_header_units(self):
        table_pdf(self.path,[['Product Code','Module Size (GB)','Brand','Rated Speed (MT/s)'],['ACME-16',16,'Acme',5600],['ACME-32',32,'Acme',4800]])
        products=analyze(self.path,'MEMORY')
        self.assertEqual(len(products),2)
        self.assertEqual([p.values['용량'].text for p in products],['16GB','32GB'])
        self.assertEqual([p.values['동작속도'].text for p in products],['5600 MT/s','4800 MT/s'])
        self.assertEqual(products[0].values['제조사'].text,'Acme')
    def test_vga_horizontal_table(self):
        table_pdf(self.path,[['Model','ACME-G1','ACME-G2'],['Memory Size','8 GB','16 GB'],['Memory Type','GDDR6','GDDR6X'],['TGP','100 W','200 W'],['Memory Bandwidth','256 GB/s','512 GB/s']])
        products=analyze(self.path,'VGA')
        self.assertEqual(len(products),2);self.assertEqual(products[1].values['VRAM 용량'].text,'16 GB')
        self.assertEqual(products[1].values['메모리 대역폭'].text,'512000 MB/s')
    def test_same_capacity_different_models_no_speed_guess(self):
        doc=fitz.open();p=doc.new_page();p.insert_text((40,40),'Model: A\nCapacity: 1 TB\nModel: B\nCapacity: 1 TB');doc.save(self.path);doc.close()
        products=analyze(self.path,'SSD');self.assertEqual(products[0].values['순차읽기 속도'].text,'확인 필요')
    def test_conflict_remains_missing_after_repeated_candidate(self):
        p=Product('sample','SSD',{'용량':Value()})
        assign(p,'용량','1 TB',1,'first');assign(p,'용량','2 TB',2,'conflicting');assign(p,'용량','2 TB',3,'repeat')
        self.assertEqual(p.values['용량'].text,'확인 필요');self.assertTrue(p.values['용량'].conflict)
    def test_bits_not_mistaken_for_module_bytes(self):
        p=Product('sample','MEMORY',{'용량':Value()});assign(p,'용량','16Gb',1,'chip density')
        self.assertEqual(p.values['용량'].text,'확인 필요')
    def test_prose_without_colons(self):
        doc=fitz.open();p=doc.new_page();p.insert_text((40,40),'Brand ACME\nModel Number ACME-NEW\nSequential Read Speed up to 7.4 GB/s\nRandom Read IOPS 500K IOPS');doc.save(self.path);doc.close()
        result=analyze(self.path,'SSD')[0]
        self.assertEqual(result.name,'ACME-NEW');self.assertEqual(result.values['순차읽기 속도'].text,'7400 MB/s');self.assertEqual(result.values['랜덤읽기 속도'].text,'500K IOPS')

    def test_open_capacity_columns_multiline_qd_and_separate_skus(self):
        from speccompare.fixtures import create_capacity_fixture
        create_capacity_fixture(self.path)
        products=analyze(self.path,'SSD')
        self.assertEqual(len(products),2)
        self.assertEqual([p.name for p in products],['ACME-X1','ACME-X2'])
        self.assertEqual([p.values['순차읽기 속도'].text for p in products],['7,100 MB/s','7,200 MB/s'])
        self.assertEqual([p.values['순차쓰기 속도'].text for p in products],['6,100 MB/s','6,200 MB/s'])
        self.assertEqual([p.values['랜덤읽기 속도'].text for p in products],['1,100K IOPS','1300K IOPS'])
        self.assertEqual([p.values['랜덤쓰기 속도'].text for p in products],['1,500K IOPS','1,600K IOPS'])
        self.assertEqual([p.values['내구성'].text for p in products],['600 TB','1,200 TB'])
        self.assertEqual([p.values['DRAM'].text for p in products],['1GB LPDDR4','2GB LPDDR4'])
        for i,p in enumerate(products,1):
            self.assertEqual(p.values['판매 코드'].text,f'ACME-X{i}BW\nACME-X{i}B/AM')
            self.assertEqual(p.values['랜덤읽기 속도 · 측정 QD'].text,'QD32')
            self.assertIn('Thread 16',p.values['랜덤읽기 속도'].evidence)
            self.assertEqual(p.values['랜덤쓰기 속도 · QD1'].text,['70K IOPS','71K IOPS'][i-1])

    def test_capacity_coordinates_do_not_join_ambiguous_models(self):
        from speccompare.fixtures import create_capacity_fixture
        from speccompare.document import read_document
        from speccompare.parser import performance_tables
        from speccompare.schema import FIELDS, EXTRAS
        create_capacity_fixture(self.path);doc=read_document(self.path)
        products=[Product('same.pdf','SSD',{k:Value() for k in FIELDS['SSD']+EXTRAS['SSD']}) for _ in range(2)]
        for p in products:p.values['용량']=Value('1TB',2,'capacity')
        performance_tables(doc,products)
        for p in products:
            self.assertEqual(p.values['순차읽기 속도'].text,'확인 필요')
            self.assertEqual(p.values['랜덤읽기 속도'].text,'확인 필요')
            self.assertTrue(any('동일 용량' in w for w in p.warnings))
