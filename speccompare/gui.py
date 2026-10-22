import sys
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QTabBar,QPushButton,QListWidget,QAbstractItemView,QTableWidget,QTableWidgetItem,QProgressBar,QLabel,QFileDialog,QMessageBox,QInputDialog,QTextEdit,QDialog)
from .schema import FIELDS
from .parser import analyze
from .excel import export
from .resources import ROOT, template_path


class Worker(QThread):
    progress = Signal(int)
    result = Signal(object, object)
    def __init__(self, paths, category):
        super().__init__(); self.paths=paths; self.category=category
    def run(self):
        products, errors = [], []
        for i,path in enumerate(self.paths):
            try:
                result=analyze(path,self.category,auto_detect=True)
                usable=[p for p in result if any(p.values[k].text!='확인 필요' for k in FIELDS[p.category])]
                if not usable: raise ValueError('모델별 사양을 식별하지 못했습니다. 원문 검토가 필요합니다.')
                products.extend(usable)
            except Exception as exc: errors.append(f'{Path(path).name}: {exc}')
            self.progress.emit(int((i+1)/len(self.paths)*100))
        if len({p.category for p in products})>1:
            products=[]
            errors.append('서로 다른 제품군의 PDF가 섞여 있습니다. MEMORY / SSD / VGA별로 나누어 분석하세요.')
        self.result.emit(products,errors)

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('SpecCompare 1.0.2'); self.resize(1150,800)
        self.setWindowIcon(QIcon(str(ROOT/'assets/icon.ico')))
        self.products=[]; self.saved=None; self.worker=None; self.refreshing=False
        self.setAcceptDrops(True)
        central=QWidget(); self.setCentralWidget(central); layout=QVBoxLayout(central)
        title=QLabel('SpecCompare  |  PC 부품 데이터시트 비교'); title.setStyleSheet('font-size:24px;font-weight:700;padding:14px'); layout.addWidget(title)
        self.tabs=QTabBar()
        for name in FIELDS: self.tabs.addTab(name)
        self.tabs.currentChanged.connect(self.category_changed); layout.addWidget(self.tabs)
        layout.addWidget(QLabel('PDF를 끌어 놓거나 추가하세요. 추출값은 원문 검토 후 확인 완료로 표시하세요.'))
        self.files=QListWidget(); self.files.setMaximumHeight(130); self.files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection); layout.addWidget(self.files)
        row=QHBoxLayout(); layout.addLayout(row)
        self.actions=[]
        for label,callback in [('PDF 추가',self.add_dialog),('선택 삭제',self.remove_files),('전체 삭제',self.clear_files),('스펙 분석',self.run_analysis),('분석 결과 초기화',self.reset)]:
            button=QPushButton(label); button.clicked.connect(callback); row.addWidget(button); self.actions.append(button)
        self.progress=QProgressBar(); layout.addWidget(self.progress)
        self.groups=QTabBar(); self.groups.currentChanged.connect(self.render); layout.addWidget(self.groups)
        self.table=QTableWidget(); self.table.cellChanged.connect(self.edited); self.table.cellClicked.connect(self.evidence); layout.addWidget(self.table,1)
        self.detail=QTextEdit(); self.detail.setReadOnly(True); self.detail.setMaximumHeight(150); layout.addWidget(self.detail)
        row=QHBoxLayout(); layout.addLayout(row)
        for label,callback in [('제품 왼쪽 이동',lambda:self.move(-1)),('제품 오른쪽 이동',lambda:self.move(1)),('제품 상세정보',self.show_details),('원문 PDF 열기',self.open_source),('선택값 확인 완료',self.confirm),('엑셀 저장',self.save),('저장 파일 열기',self.open_saved)]:
            button=QPushButton(label); button.clicked.connect(callback); row.addWidget(button)
        self.setStyleSheet('QMainWindow{background:#f3f5fa} QTableWidget,QListWidget,QTextEdit{background:white;border:1px solid #d5dce8} QPushButton{padding:9px;background:#e1eafb;border:1px solid #bbcbe5;border-radius:4px} QTabBar::tab{padding:10px 26px} QTabBar::tab:selected{background:#c9dcfa}')
        self.render()
    @property
    def category(self): return self.tabs.tabText(self.tabs.currentIndex())
    def category_changed(self): self.reset()
    def reset(self): self.products=[]; self.rebuild_groups(); self.detail.clear(); self.progress.setValue(0)
    def add_dialog(self):
        paths,_=QFileDialog.getOpenFileNames(self,'PDF 추가','','PDF (*.pdf)'); self.add_paths(paths)
    def add_paths(self,paths):
        existing={self.files.item(i).text() for i in range(self.files.count())}
        for path in paths:
            if Path(path).suffix.lower()=='.pdf' and str(Path(path).resolve()) not in existing:
                full=str(Path(path).resolve()); self.files.addItem(full); existing.add(full)
    def dragEnterEvent(self,event):
        if (not self.worker or not self.worker.isRunning()) and event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self,event): self.add_paths([u.toLocalFile() for u in event.mimeData().urls()])
    def remove_files(self):
        for item in self.files.selectedItems(): self.files.takeItem(self.files.row(item))
    def clear_files(self): self.files.clear()
    def run_analysis(self):
        if not self.files.count(): return self.message('PDF를 먼저 추가하세요.')
        if self.worker and self.worker.isRunning(): return
        self.worker=Worker([self.files.item(i).text() for i in range(self.files.count())],self.category)
        self.tabs.setEnabled(False);self.table.setEnabled(False)
        for b in self.actions: b.setEnabled(False)
        self.worker.progress.connect(self.progress.setValue); self.worker.result.connect(self.analysis_result); self.worker.finished.connect(self.analysis_finished); self.worker.start()
    def analysis_finished(self):
        self.tabs.setEnabled(True);self.table.setEnabled(True)
        for b in self.actions: b.setEnabled(True)
    def analysis_result(self,products,errors):
        products=[p for p in products if any(p.values[k].text!='확인 필요' for k in FIELDS[p.category])]
        categories={p.category for p in products}
        if len(categories)>1:
            self.products=[]; self.rebuild_groups()
            return self.message('서로 다른 제품군은 함께 비교할 수 없습니다. 제품군별로 나누어 분석하세요.')
        if categories:
            category=next(iter(categories))
            if category!=self.category:
                self.tabs.setCurrentIndex(list(FIELDS).index(category))
        selected=[]
        for source in dict.fromkeys(p.source for p in products):
            candidates=[p for p in products if p.source==source]
            if len(candidates)>1:
                dialog=QDialog(self); dialog.setWindowTitle('비교할 모델 선택'); box=QVBoxLayout(dialog); choices=QListWidget(); choices.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
                choices.addItems([p.name+' · '+p.values.get('용량',p.values.get('VRAM 용량')).text for p in candidates]); choices.selectAll(); box.addWidget(choices); ok=QPushButton('선택 완료'); ok.clicked.connect(dialog.accept); box.addWidget(ok)
                if dialog.exec(): selected.extend(candidates[i.row()] for i in choices.selectedIndexes())
            else: selected.extend(candidates)
        self.products=selected; self.rebuild_groups()
        if errors: self.message('\n'.join(errors))
    def rebuild_groups(self):
        self.groups.blockSignals(True)
        while self.groups.count(): self.groups.removeTab(0)
        for i in range(max(1,(len(self.products)+3)//4)): self.groups.addTab(f'비교 그룹 {i+1}')
        self.groups.setCurrentIndex(0); self.groups.blockSignals(False); self.render()
    def visible(self):
        start=max(0,self.groups.currentIndex())*4
        return self.products[start:start+4]
    def render(self,*args):
        self.refreshing=True; fields=FIELDS[self.category]; products=self.visible()
        self.table.clear(); self.table.setRowCount(len(fields)); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(['스펙 항목']+[products[i].name if i<len(products) else '제품 '+chr(65+i) for i in range(4)])
        for r,key in enumerate(fields):
            item=QTableWidgetItem(key); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable); self.table.setItem(r,0,item)
            different=len({p.values[key].text for p in products if p.values[key].text!='확인 필요'})>1
            for c in range(1,5):
                item=QTableWidgetItem(products[c-1].values[key].text if c<=len(products) else '')
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c>len(products): item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    value=products[c-1].values[key]; item.setToolTip(value.status)
                    item.setBackground(QColor('#ffe4df' if value.text=='확인 필요' else '#fff3c4' if different else '#e4f3ee' if value.status=='확인 완료' else '#ffffff'))
                self.table.setItem(r,c,item)
        self.table.resizeColumnsToContents(); self.table.horizontalHeader().setStretchLastSection(True); self.refreshing=False
    def edited(self,r,c):
        if self.refreshing or c<1 or c>len(self.visible()): return
        value=self.visible()[c-1].values[FIELDS[self.category][r]]; value.text=self.table.item(r,c).text(); value.status='검토 필요'; self.table.item(r,c).setToolTip('검토 필요 · 수동 수정'); self.evidence(r,c)
    def current(self):
        r,c=self.table.currentRow(),self.table.currentColumn()
        return (self.visible()[c-1],FIELDS[self.category][r]) if r>=0 and 1<=c<=len(self.visible()) else (None,None)
    def evidence(self,r,c):
        if not 1<=c<=len(self.visible()): return
        product=self.visible()[c-1]; value=product.values[FIELDS[self.category][r]]
        self.detail.setPlainText(f'{product.source}\n페이지: {value.page or "없음"} | 상태: {value.status} | 규칙 일치도: {value.confidence:.0%}\n원문 근거: {value.evidence or "없음 — 수동 확인 필요"}\n'+'\n'.join(product.warnings))
    def confirm(self):
        product,key=self.current()
        if product and product.values[key].text.strip() and product.values[key].text!='확인 필요': product.values[key].status='확인 완료'; self.render()
    def show_details(self):
        product,_=self.current()
        if product:
            self.detail.setPlainText('\n'.join(f'{k}: {v.text} [{v.status}] p.{v.page or "-"}\n{v.evidence}' for k,v in product.values.items())+'\n'+'\n'.join(product.warnings))
    def open_source(self):
        product,key=self.current()
        if product:
            url=QUrl.fromLocalFile(product.source)
            if product.values[key].page: url.setFragment('page='+str(product.values[key].page))
            QDesktopServices.openUrl(url)
    def move(self,delta):
        product,_=self.current()
        if product:
            i=self.products.index(product); j=i+delta
            if 0<=j<len(self.products): self.products[i],self.products[j]=self.products[j],self.products[i]; self.render()
    def save(self):
        if not self.visible(): return self.message('분석 결과가 없습니다.')
        destination,_=QFileDialog.getSaveFileName(self,'엑셀 저장',f'{self.category}_SpecCompare_{datetime.now():%Y%m%d}.xlsx','Excel (*.xlsx)')
        if not destination: return
        if not destination.lower().endswith('.xlsx'): destination+='.xlsx'
        try:
            export(template_path(),destination,self.category,self.visible()); self.saved=destination; self.message('현재 비교 그룹을 원본 양식으로 저장했습니다.')
        except Exception as exc: self.message(f'저장 실패: {exc}\n파일 잠금과 폴더 쓰기 권한을 확인하세요.')
    def open_saved(self):
        if self.saved and Path(self.saved).exists(): QDesktopServices.openUrl(QUrl.fromLocalFile(self.saved))
    def message(self,text): QMessageBox.information(self,'SpecCompare',text)
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning(): self.message('분석 완료 후 종료하세요.'); event.ignore()
        else: event.accept()

def main():
    app=QApplication(sys.argv); window=Window(); window.show(); sys.exit(app.exec())
