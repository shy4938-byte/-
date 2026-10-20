"""Packaged Windows runtime smoke test, invoked explicitly by --verify-package."""
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from .gui import Window, ROOT
from .parser import analyze
from .excel import export

def verify(pdf, output_folder):
    app = QApplication.instance() or QApplication([])
    window = Window()
    products = analyze(pdf, 'SSD')
    window.tabs.setCurrentIndex(1)
    window.products = products
    window.rebuild_groups()
    window.show()
    app.processEvents()
    if not products or window.table.item(1,1).text() != products[0].name:
        raise RuntimeError('GUI product display verification failed')
    output = Path(output_folder)
    output.mkdir(parents=True, exist_ok=True)
    export(ROOT/'assets/template.xlsx', output/'패키지검증.xlsx', 'SSD', products[:4])
    report = {'products': [dict(model=p.name, values={k: v.text for k,v in p.values.items()}) for p in products], 'gui': 'passed', 'excel': '패키지검증.xlsx'}
    (output/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    window.close()
