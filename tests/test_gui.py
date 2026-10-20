import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QSignalSpy
from speccompare.gui import Window, Worker
from speccompare.schema import Product, Value, FIELDS
from speccompare.excel import export
from openpyxl import load_workbook
from test_workflow import pdf, ROOT
app=QApplication.instance() or QApplication([])
class Gui(unittest.TestCase):
    def test_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'샘플.pdf'; pdf(path,['Model: GUI-SAMPLE','Capacity: 16 GB'])
            worker=Worker([str(path)],'MEMORY'); spy=QSignalSpy(worker.result); worker.start()
            # Pump the Qt event loop while the Python worker runs.
            import time
            deadline=time.monotonic()+15
            while spy.count()==0 and time.monotonic()<deadline:
                app.processEvents(); time.sleep(.01)
            worker.wait(15000); self.assertEqual(spy.count(),1)
            products,errors=spy.at(0); self.assertEqual(errors,[]); self.assertEqual(products[0].name,'GUI-SAMPLE')
    def test_groups_edit_move_save(self):
        window=Window(); window.show(); app.processEvents()
        window.products=[Product(str(i),'MEMORY',{k:Value(str(i)) for k in FIELDS['MEMORY']}) for i in range(5)]
        window.rebuild_groups(); self.assertEqual(window.groups.count(),2)
        window.table.item(0,1).setText('사용자 수정'); self.assertEqual(window.products[0].values['제조사'].text,'사용자 수정')
        window.table.setCurrentCell(0,1); window.move(1); self.assertEqual(window.products[1].values['제조사'].text,'사용자 수정')
        window.groups.setCurrentIndex(1); self.assertEqual(len(window.visible()),1)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'저장.xlsx'; export(ROOT/'assets/template.xlsx',path,'MEMORY',window.visible()); w=load_workbook(path); self.assertEqual(w['메모리']['C5'].value,'4'); w.close()
        window.close()

    def test_model_selection_dialog_and_center_alignment(self):
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtWidgets import QDialog, QListWidget
        window=Window()
        products=[Product('same.pdf','MEMORY',{k:Value(str(i)) for k in FIELDS['MEMORY']}) for i in range(2)]
        def choose():
            dialog=app.activeModalWidget()
            if isinstance(dialog,QDialog):
                dialog.findChild(QListWidget).selectAll();dialog.accept()
        QTimer.singleShot(30,choose)
        window.analysis_result(products,[])
        self.assertEqual(len(window.products),2)
        self.assertTrue(window.table.item(0,1).textAlignment() & Qt.AlignmentFlag.AlignHCenter)
        window.close()

    def test_ssd_uploaded_on_memory_tab_switches_result_and_export(self):
        from unittest.mock import patch
        from speccompare.fixtures import create_fixtures
        import time
        with tempfile.TemporaryDirectory() as directory:
            paths=create_fixtures(Path(directory)/'샘플')
            window=Window(); window.add_paths([str(paths['SSD'])])
            self.assertEqual(window.category,'MEMORY')
            window.run_analysis()
            deadline=time.monotonic()+20
            while (window.worker.isRunning() or not window.products) and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            window.worker.wait(20000);app.processEvents()
            self.assertEqual(window.category,'SSD')
            self.assertEqual(window.products[0].category,'SSD')
            keys=[window.table.item(r,0).text() for r in range(window.table.rowCount())]
            self.assertIn('순차읽기 속도',keys);self.assertNotIn('메모리 규격',keys)
            self.assertEqual(window.products[0].values['순차읽기 속도'].text,'7400 MB/s')
            destination=Path(directory)/'SSD 저장.xlsx'
            with patch('speccompare.gui.QFileDialog.getSaveFileName',return_value=(str(destination),'')), patch.object(window,'message'):
                window.save()
            wb=load_workbook(destination);self.assertEqual(wb['SSD']['C5'].value,window.products[0].values['제조사'].text);wb.close()
            window.tabs.setCurrentIndex(0);self.assertEqual(window.products,[])
            window.close()

    def test_mixed_categories_rejected_by_worker(self):
        from speccompare.fixtures import create_fixtures
        import time
        with tempfile.TemporaryDirectory() as directory:
            paths=create_fixtures(Path(directory))
            worker=Worker([str(paths['SSD']),str(paths['MEMORY'])],'MEMORY')
            spy=QSignalSpy(worker.result);worker.start();deadline=time.monotonic()+20
            while not spy.count() and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            worker.wait(20000)
            products,errors=spy.at(0);self.assertEqual(products,[]);self.assertIn('제품군',errors[-1])
