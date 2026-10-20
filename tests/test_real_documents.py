"""Private user PDFs stay local. CI explicitly skips missing real fixtures."""
import os
import unittest
from speccompare.parser import analyze

class RealDocuments(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('SPECCOMPARE_PM9A1_PDF'),'Real PM9A1 PDF not supplied')
    def test_pm9a1(self):
        products=analyze(os.environ['SPECCOMPARE_PM9A1_PDF'],'MEMORY',auto_detect=True)
        self.assertEqual(len(products),4)
        self.assertTrue(all(p.category=='SSD' for p in products))
        for i,p in enumerate(products):
            self.assertEqual(p.name,'Samsung PM9A1 '+['256GB','512GB','1024GB','2048GB'][i])
            self.assertEqual(p.values['순차읽기 속도'].text,['6,400 MB/s','6,900 MB/s','7,000 MB/s','7,000 MB/s'][i])
            self.assertEqual(p.values['순차쓰기 속도'].text,['2,700 MB/s','5,000 MB/s','5,100 MB/s','5,200 MB/s'][i])
            self.assertEqual(p.values['랜덤읽기 속도 · 측정 QD'].text,'QD32')
            self.assertEqual(p.values['랜덤읽기 속도 · QD1'].text,'18K IOPS')
            self.assertEqual(p.values['가격'].text,'확인 필요')
    @unittest.skipUnless(os.environ.get('SPECCOMPARE_ESSENCORE_PDF'),'Real ESSENCORE PDF not supplied')
    def test_essencore(self):
        products=analyze(os.environ['SPECCOMPARE_ESSENCORE_PDF'],'MEMORY');self.assertEqual(len(products),1)
        p=products[0];self.assertEqual(p.values['용량'].text,'16GB');self.assertEqual(p.values['메모리 규격'].text,'DDR5 SO-DIMM');self.assertEqual(p.values['동작속도'].text,'5600 MT/s');self.assertEqual(p.values['지연시간'].text,'CL46');self.assertEqual(p.values['ECC'].text,'확인 필요')
    @unittest.skipUnless(os.environ.get('SPECCOMPARE_SAMSUNG_DDR5_PDF'),'Real Samsung DDR5 PDF not supplied')
    def test_samsung_memory(self):
        products=analyze(os.environ['SPECCOMPARE_SAMSUNG_DDR5_PDF'],'MEMORY');self.assertEqual(len(products),2)
        for i,p in enumerate(products):
            self.assertEqual(p.values['용량'].text,['16GB','32GB'][i]);self.assertEqual(p.values['동작속도'].text,'5600 MT/s');self.assertEqual(p.values['지연시간'].text,'CL46');self.assertEqual(p.values['Rank'].text,['1 Rank','2 Rank'][i]);self.assertIn('WM',p.values['동작속도'].evidence)
