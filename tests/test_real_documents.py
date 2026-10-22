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

    @unittest.skipUnless(os.environ.get('SPECCOMPARE_990PRO_PDF'),'Real 990 PRO PDF not supplied')
    def test_990pro(self):
        products=analyze(os.environ['SPECCOMPARE_990PRO_PDF'],'SSD')
        self.assertEqual(len(products),2)
        for i,p in enumerate(products,1):
            self.assertEqual(p.name,f'Samsung 990 PRO {i}TB')
            self.assertEqual(p.values['부품번호'].text,f'MZ-V9P{i}T0')
            self.assertEqual(p.values['판매 코드'].text,f'MZ-V9P{i}T0BW\nMZ-V9P{i}T0B/AM')
            self.assertEqual(p.values['순차읽기 속도'].text,'7,450 MB/s')
            self.assertEqual(p.values['순차쓰기 속도'].text,'6,900 MB/s')
            self.assertEqual(p.values['랜덤읽기 속도'].text,['1,200K IOPS','1400K IOPS'][i-1])
            self.assertEqual(p.values['랜덤쓰기 속도'].text,'1,550K IOPS')
            self.assertEqual(p.values['내구성'].text,['600 TB','1,200 TB'][i-1])
            self.assertEqual(p.values['DRAM'].text,f'{i}GB LPDDR4')
            self.assertEqual(p.values['인터페이스'].text,'PCIe Gen 4.0 x4, NVMe 2.0')
            self.assertEqual(p.values['랜덤읽기 속도 · QD1'].text,'22K IOPS')
            self.assertEqual(p.values['랜덤쓰기 속도 · QD1'].text,'80K IOPS')
            self.assertIn('Thread 16',p.values['랜덤읽기 속도'].evidence)
            for key in ['순차읽기 속도','순차쓰기 속도','랜덤읽기 속도','랜덤쓰기 속도','내구성']:
                self.assertEqual(p.values[key].page,3)
                self.assertTrue(p.values[key].evidence)
            self.assertEqual(p.values['가격'].text,'확인 필요')

    @unittest.skipUnless(os.environ.get('SPECCOMPARE_TRANSCEND_PDF'),'Real Transcend PDF not supplied')
    def test_transcend_reference_evidence_scope_not_live_ai(self):
        # Curated reference payload tests source validation/scope only, not AI accuracy.
        from speccompare.ai import decode
        from speccompare.document import read_document
        doc=read_document(os.environ['SPECCOMPARE_TRANSCEND_PDF'])
        models=[]
        for cap,code in [('250GB','TS250GMTE245S'),('500GB','TS500GMTE245S'),('1TB','TS1TMTE245S'),('2TB','TS2TMTE245S'),('4TB','TS4TMTE245S')]:
            models.append(dict(id=code,name=code,category='SSD',page=2,quote=code,fields=[dict(key='용량',value=cap,scope='model',page=2,quote=cap,link_page=2,link_quote=code,conditions='',model_ids=[code])]))
        shared=[]
        for key,value,quote in [('순차읽기 속도','5,300 MB/s','Read: Up to 5,300 MB/s'),('순차쓰기 속도','4,600 MB/s','Write: Up to 4,600 MB/s'),('랜덤읽기 속도','500,000 IOPS','Read: Up to 500,000 IOPS'),('랜덤쓰기 속도','630,000 IOPS','Write: Up to 630,000 IOPS'),('내구성','2400 TBW','Up to 2400 TBW')]:
            shared.append(dict(key=key,value=value,quote=quote,scope='family_max',page=2,link_page=2,link_quote=quote,conditions='',model_ids=[m['id'] for m in models]))
        ps=decode(doc,[dict(models=models,shared=shared)]);self.assertEqual(len(ps),5)
        for p in ps:
            self.assertEqual(p.values['순차읽기 속도'].text,'확인 필요');self.assertEqual(p.values['내구성'].text,'확인 필요')
            self.assertEqual(len(p.shared),5)
