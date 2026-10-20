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
