from datetime import datetime
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import threading
from PySide6.QtCore import Qt,QThread,Signal,QTimer,QPointF
from PySide6.QtGui import QColor,QPainter,QCursor
from PySide6.QtCharts import QChart,QChartView,QLineSeries,QValueAxis
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QCheckBox,QProgressBar,QTableWidget,QTableWidgetItem,QAbstractItemView,QSplitter,QScrollArea,QFileDialog,QMessageBox,QToolTip)
from .analytics import monthly_rows,daily_rows,cards,required_dates
from .service import collect,cached_snapshot
from .domain import now_kst,KST
from .excel import export_snapshot,RULE,COMPARE_RULE


def number(value,signed=False):
    if value is None:return '—'
    rounded=value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return format(rounded,'+,.2f' if signed else ',.2f')


class Collector(QThread):
    progress=Signal(int,int,str);updated=Signal(object);result=Signal(object)
    def __init__(self,path,today,force=False,client_factory=None):
        super().__init__();self.path=path;self.today=today;self.force=force;self.cancel=threading.Event();self.client_factory=client_factory
    def run(self):
        options={'client_factory':self.client_factory} if self.client_factory else {}
        result=collect(self.path,self.today,self.cancel,self.force,self.progress.emit,self.updated.emit,**options);self.result.emit(result)


class RateChart(QChartView):
    def __init__(self,parent=None):
        super().__init__(QChart(),parent);self.setRenderHint(QPainter.RenderHint.Antialiasing);self.setMinimumHeight(230);self.chart().setAnimationOptions(QChart.AnimationOption.NoAnimation);self.plotted={}
    def set_rows(self,rows,key,year):
        chart=self.chart();chart.removeAllSeries()
        for axis in chart.axes():chart.removeAxis(axis);axis.deleteLater()
        ax=QValueAxis();ax.setRange(1,max(2,len(rows)));ax.setTickCount(min(8,max(2,len(rows))));ax.setLabelFormat('%d');ax.setTitleText('월' if key=='month' else '일')
        ay=QValueAxis();ay.setLabelFormat('%.2f');ay.setTitleText('KRW / USD')
        chart.addAxis(ax,Qt.AlignmentFlag.AlignBottom);chart.addAxis(ay,Qt.AlignmentFlag.AlignLeft)
        values=[];self.plotted={}
        for field,label,color in [('current',str(year),'#078B87'),('previous',str(year-1),'#5875C7')]:
            self.plotted[field]=[(r[key],r[field]) for r in rows if r[field] is not None];segments=[];segment=[]
            for row in rows:
                if row[field] is None:
                    if segment:segments.append(segment);segment=[]
                else:segment.append(row);values.append(float(row[field]))
            if segment:segments.append(segment)
            if not segments:segments=[[]]
            for n,part in enumerate(segments):
                series=QLineSeries();series.setName(label);series.setColor(QColor(color));series.setPointsVisible(True)
                for row in part:series.append(QPointF(row[key],float(row[field])))
                details={r[key]:r.get(field+'_status','') for r in part}
                series.hovered.connect(lambda p,on,y=label,d=details:QToolTip.showText(QCursor.pos(),f'{y}년 {int(round(p.x()))}{"월" if key=="month" else "일"}: {p.y():,.2f}원\n{d.get(int(round(p.x())),"")}') if on else QToolTip.hideText())
                chart.addSeries(series);series.attachAxis(ax);series.attachAxis(ay)
                if n:
                    for marker in chart.legend().markers(series):marker.setVisible(False)
        if values:
            low,high=min(values),max(values);padding=max(1,(high-low)*.15);ay.setRange(low-padding,high+padding)
        else:ay.setRange(0,1)
        chart.setTitle('' if values else '고시 데이터 없음 / 미수집')
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)


class Window(QMainWindow):
    def __init__(self,db_path,clock=now_kst,auto_start=True,client_factory=None):
        super().__init__();self.db_path=Path(db_path);self.clock=clock;self.effective_day=clock().date();self.worker=None;self.snapshot=None;self.pending_refresh=False;self.closing=False;self.client_factory=client_factory
        self.resize(1240,960);self.setWindowTitle('HanaFX · USD 최초 고시 환율')
        central=QWidget();self.setCentralWidget(central);outer=QVBoxLayout(central)
        self.heading=QLabel();self.heading.setStyleSheet('font-size:24px;font-weight:700;color:#123F46');outer.addWidget(self.heading)
        actions=QHBoxLayout();outer.addLayout(actions)
        self.refresh=QPushButton('조회 · 최신 데이터 갱신');self.refresh.clicked.connect(self.start_refresh);actions.addWidget(self.refresh)
        self.cancel_button=QPushButton('수집 취소');self.cancel_button.clicked.connect(self.cancel);self.cancel_button.setEnabled(False);actions.addWidget(self.cancel_button)
        self.force=QCheckBox('과거 자료도 재확인 (최초 수준의 요청·시간 필요)');actions.addWidget(self.force)
        self.export_button=QPushButton('Excel 저장');self.export_button.clicked.connect(self.save);actions.addWidget(self.export_button)
        self.progress=QProgressBar();outer.addWidget(self.progress)
        self.status=QLabel('저장된 데이터 확인 중');self.status.setWordWrap(True);outer.addWidget(self.status)
        scroll=QScrollArea();scroll.setWidgetResizable(True);outer.addWidget(scroll,1);body=QWidget();scroll.setWidget(body);layout=QVBoxLayout(body)
        cardrow=QHBoxLayout();layout.addLayout(cardrow);self.card_labels=[]
        for _ in range(3):
            label=QLabel('—');label.setWordWrap(True);label.setMinimumHeight(115);label.setStyleSheet('background:#E8F4F2;border:1px solid #C7E4DF;border-radius:8px;padding:14px;font-size:16px');cardrow.addWidget(label,1);self.card_labels.append(label)
        self.month_title=QLabel();layout.addWidget(self.month_title)
        self.month_table=self.make_table();self.month_chart=RateChart();split=QSplitter(Qt.Orientation.Horizontal);split.addWidget(self.month_table);split.addWidget(self.month_chart);split.setSizes([590,590]);layout.addWidget(split)
        self.day_title=QLabel();layout.addWidget(self.day_title)
        self.day_table=self.make_table();self.day_chart=RateChart();split=QSplitter(Qt.Orientation.Horizontal);split.addWidget(self.day_table);split.addWidget(self.day_chart);split.setSizes([590,590]);layout.addWidget(split)
        note=QLabel(RULE+'\n'+COMPARE_RULE+'\n노란색은 부분 자료 평균이며 조회가 완료되면 달라질 수 있습니다. 빈 날짜는 선을 연결하지 않습니다.');note.setWordWrap(True);layout.addWidget(note)
        self.setStyleSheet('QMainWindow{background:#F4F8F9} QPushButton{padding:9px 13px} QTableWidget{background:white} QHeaderView::section{background:#E6F1F3;padding:5px} QProgressBar{min-height:16px}')
        self.timer=QTimer(self);self.timer.timeout.connect(self.check_date);self.timer.start(30000)
        self.load_cache()
        if auto_start:QTimer.singleShot(0,self.start_refresh)
    def make_table(self):
        table=QTableWidget();table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);table.setMinimumHeight(250);table.setMaximumHeight(360);table.verticalHeader().setVisible(False);return table
    def load_cache(self):
        try:
            self.apply_snapshot(cached_snapshot(self.db_path,self.effective_day));self.status.setText('저장된 데이터 표시 · 최초 수집은 수 분 이상 걸릴 수 있습니다. 진행 중 취소할 수 있습니다.')
        except Exception as exc:self.status.setText('로컬 DB를 읽지 못했습니다: '+str(exc))
    def start_refresh(self):
        if self.worker and self.worker.isRunning():return
        self.check_date(start=False)
        self.worker=Collector(self.db_path,self.effective_day,self.force.isChecked(),self.client_factory)
        self.worker.progress.connect(self.on_progress);self.worker.updated.connect(self.apply_snapshot);self.worker.result.connect(self.completed);self.worker.finished.connect(self.finished)
        self.refresh.setEnabled(False);self.force.setEnabled(False);self.cancel_button.setEnabled(True);self.status.setText('공식 사이트 정책·세션 확인 중 · 요청 간격 최소 1.2초, 처음에는 수 분 이상 걸립니다.');self.worker.start()
    def on_progress(self,done,total,message):
        if self.worker.today!=self.effective_day:return
        self.progress.setRange(0,max(1,total));self.progress.setValue(done);self.status.setText(f'{message} · {done}/{total} · 새 조회와 저장된 자료를 함께 표시합니다.')
    def cancel(self):
        if self.worker and self.worker.isRunning():self.worker.cancel.set();self.status.setText('취소 요청됨 · 현재 요청이 끝나면 중단합니다. 수집한 자료는 보존합니다.')
    def completed(self,snapshot):
        if snapshot.asof!=self.effective_day:return
        self.apply_snapshot(snapshot)
        if snapshot.error:self.status.setText('조회 오류 · 저장된 데이터/수집된 자료 표시: '+snapshot.error)
        elif snapshot.cancelled:self.status.setText(f'수집 취소 · {snapshot.done}/{snapshot.total} 확인. 부분 자료·저장된 데이터 표시.')
        else:
            wanted=required_dates(snapshot.asof)
            failed=sum(snapshot.coverage[d].status=='error' for d in wanted if d in snapshot.coverage)
            pending=sum(d not in snapshot.coverage for d in wanted)
            self.status.setText(f'조회 종료 · 새 검증 {len(snapshot.fresh)}일 · 저장된 자료 포함 · 오류 {failed}일 / 미수집 {pending}일 · {snapshot.retrieved_at.astimezone(KST).isoformat(timespec="seconds")}')
    def finished(self):
        self.refresh.setEnabled(True);self.force.setEnabled(True);self.cancel_button.setEnabled(False)
        if self.closing:self.close();return
        if self.pending_refresh:self.pending_refresh=False;QTimer.singleShot(0,self.start_refresh)
    def check_date(self,start=True):
        today=self.clock().date()
        if today==self.effective_day:return
        self.effective_day=today;self.load_cache()
        if self.worker and self.worker.isRunning():self.pending_refresh=True;self.cancel()
        elif start:self.start_refresh()
    def apply_snapshot(self,snapshot):
        if snapshot.asof!=self.effective_day:return
        self.snapshot=snapshot;day=snapshot.asof
        self.heading.setText(f'HanaFX · {day.year}년 {day.month:02d}월 {day.day:02d}일 · USD 최초 고시 매매기준율')
        self.month_title.setText(f'월평균 비교 · {day.year}/{day.year-1}년 1~{day.month-1}월' if day.month>1 else f'{day.year}년 월평균 · 아직 완료된 월 없음')
        self.day_title.setText(f'당월 일별 비교 · {day.year}/{day.year-1}년 {day.month}월 1~{day.day}일')
        top=cards(snapshot);current=top['current'];previous=top['previous']
        if current:
            name='오늘 최초 고시' if top['is_today'] else '최근 유효 고시 · 오늘 값 아님'
            origin='저장된 데이터' if top['cached'] else '새 조회'
            self.card_labels[0].setText(f'{name}\n{number(current.rate)} 원 / USD\n{current.day} {current.announced_at:%H:%M:%S} · {current.round}회차 · {origin}')
        else:self.card_labels[0].setText('오늘/최근 14일 내 검증된 고시 데이터 없음\n미수집·조회 오류 여부는 진행 상태를 확인하세요.')
        target=top['comparison_date']
        self.card_labels[1].setText(f'전년 동일일 · {target or "대응 날짜 없음"}\n'+(f'{number(previous.rate)} 원 / USD\n실제 고시일 {previous.day}' if previous else '비교 불가 · 고시 없음/미수집'))
        direction='상승' if top['delta'] is not None and top['delta']>0 else '하락' if top['delta'] is not None and top['delta']<0 else '동일' if top['delta']==0 else '비교 불가'
        self.card_labels[2].setText(f'전년 대비 · {direction}\n{number(top["delta"],True)} 원\n{number(top["percent"],True)} %')
        monthly=monthly_rows(snapshot);daily=daily_rows(snapshot)
        self.fill(self.month_table,monthly,'month',day.year);self.fill(self.day_table,daily,'day',day.year)
        self.month_chart.set_rows(monthly,'month',day.year);self.day_chart.set_rows(daily,'day',day.year)
    def fill(self,table,rows,key,year):
        table.setRowCount(len(rows));table.setColumnCount(5);table.setHorizontalHeaderLabels(['월' if key=='month' else '일',str(year),str(year-1),'차이(원)','변동률'])
        for r,row in enumerate(rows):
            texts=[str(row[key]),number(row['current']),number(row['previous']),number(row['delta'],True),number(row['percent'],True)+'%' if row['percent'] is not None else '—']
            tip=f'{year}: {row["current_status"]}\n{year-1}: {row["previous_status"]}'
            for c,text in enumerate(texts):
                item=QTableWidgetItem(text);item.setTextAlignment(Qt.AlignmentFlag.AlignCenter);item.setToolTip(tip)
                if key=='month' and not row.get('complete',True):item.setBackground(QColor('#FFF0CF'))
                table.setItem(r,c,item)
        table.resizeColumnsToContents();table.horizontalHeader().setStretchLastSection(True)
    def save(self):
        if not self.snapshot:return
        path,_=QFileDialog.getSaveFileName(self,'환율 비교 Excel 저장',f'HanaFX_{self.effective_day:%Y%m%d}.xlsx','Excel (*.xlsx)')
        if not path:return
        if not path.lower().endswith('.xlsx'):path+='.xlsx'
        try:export_snapshot(self.snapshot,path);self.status.setText('Excel 저장 완료: '+path)
        except Exception as exc:QMessageBox.warning(self,'저장 오류',str(exc))
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():self.closing=True;self.cancel();event.ignore()
        else:self.timer.stop();event.accept()
