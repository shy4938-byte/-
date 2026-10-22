"""Synthetic runtime checks and live bank checks have separate reports."""
from dataclasses import asdict
from datetime import date,datetime,time,timedelta
from decimal import Decimal
from pathlib import Path
import json,sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop,QTimer
from openpyxl import load_workbook
from .domain import Fixing,KST,NoPublication,now_kst,now_utc
from .analytics import Snapshot,required_dates,month_dates,monthly_rows,daily_rows,prior_day
from .hana_client import HanaClient
from .database import Database
from .service import collect
from .dashboard import Window,number
from .excel import export_snapshot


def save_json(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')


def live_check(output,full_month=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);today=now_kst().date();client=HanaClient();records={};statuses={}
    report={'kind':'live official bank HTTP','status':'failed','observed_at':now_kst().isoformat(),'queries':[],'full_month_requested':full_month}
    try:
        client.initialize();report['policy']=client.policy
        def fetch(day):
            if day in statuses:return
            try:
                f=client.fetch(day);records[day]=f;statuses[day]='ok'
                report['queries'].append({'requested':str(day),'rate':str(f.rate),'currency':f.currency,'round':f.round,'announced_at':f.announced_at.isoformat(),'response_sha256':f.response_sha256,'status':'verified'})
            except NoPublication as exc:
                statuses[day]='no_data';report['queries'].append({'requested':str(day),'status':'no_publication','detail':str(exc)})
        anchor=None
        for offset in range(15):
            day=today-timedelta(days=offset);fetch(day)
            if day in records:anchor=day;break
        if anchor is None:raise RuntimeError('최근 14일 내 실제 최초 고시값을 확인하지 못했습니다.')
        if prior_day(anchor):fetch(prior_day(anchor))
        fetch(today-timedelta(days=(today.weekday()+1)%7))  # Sunday may be no data; never assume a rate.
        if full_month and today.month>1:
            for year in [today.year,today.year-1]:
                for day in month_dates(year,1):fetch(day)
            from .database import Coverage
            snap=Snapshot(today,dict(records),{d:Coverage(d,status,now_utc()) for d,status in statuses.items()})
            first=monthly_rows(snap)[0]
            for year,key in [(today.year,'current'),(today.year-1,'previous')]:
                valid=[f.rate for d,f in records.items() if d.year==year and d.month==1]
                if not valid:raise RuntimeError('실제 1월 고시 데이터를 확인하지 못했습니다.')
                expected=sum(valid,Decimal(0))/len(valid)
                if first[key]!=expected:raise RuntimeError('실제 월평균 계산 불일치')
            report['monthly_check']={'month':1,'current_mean':str(first['current']),'previous_mean':str(first['previous']),'complete':first['complete']}
        with Database(output/'실제_환율.sqlite3') as db:
            for f in records.values():db.put(f)
            for d,status in statuses.items():
                if status=='no_data':db.mark(d,'no_data','실제 서버: 해당 날짜 고시 없음')
            loaded,coverage=db.load(today)
        snap=Snapshot(today,loaded,coverage,set(loaded));export_snapshot(snap,output/'실제_환율_비교.xlsx')
        refresh_dates=[]
        class TrackedClient(HanaClient):
            def fetch(self,day):
                refresh_dates.append(day)
                return super().fetch(day)
        app=QApplication.instance() or QApplication([]);window=Window(output/'실제_환율.sqlite3',auto_start=False,client_factory=TrackedClient);window.apply_snapshot(snap);window.show();app.processEvents()
        expected=[(r['day'],r['current']) for r in daily_rows(snap) if r['current'] is not None]
        if window.day_chart.plotted['current']!=expected:raise RuntimeError('실제 일별 표/그래프 불일치')
        window.status.setText('실제 하나은행 HTTP 검증 데이터 · 1월 완료 월 및 최신 고시 표본 · 나머지 기간은 미수집')
        window.grab().save(str(output/'live-dashboard.png'))
        # Exercise the actual UI refresh worker, then cancel without bulk traffic.
        loop=QEventLoop();timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit)
        window.refresh.click()
        def stop_after_verified(snapshot):
            if snapshot.fresh:window.cancel()
        window.worker.updated.connect(stop_after_verified);window.worker.finished.connect(loop.quit)
        timer.start(150000);loop.exec();timer.stop()
        if window.worker.isRunning():window.cancel();window.worker.wait(60000)
        if window.worker.isRunning():raise RuntimeError('Live refresh worker did not stop')
        app.processEvents()
        if not window.snapshot.fresh or window.snapshot.error:raise RuntimeError('Actual refresh worker failed: '+window.snapshot.error)
        if refresh_dates!=[today]:raise RuntimeError('Routine refresh queried historical dates: '+str(refresh_dates))
        report['quick_refresh_query_dates']=[str(d) for d in refresh_dates]
        report['refresh_button_worker']='passed (real verified response, then cancelled)'
        window.close();report['table_chart_excel']='passed';report['status']='passed'
    except Exception as exc:report['error']=str(exc)
    finally:client.close();save_json(output/'live-report.json',report)
    return report


def self_test(output,live=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);today=date(2026,10,22)
    records={}
    for day,rate in [(today,'1340.12'),(date(2025,10,22),'1320.34'),(date(2026,1,2),'1300.00'),(date(2025,1,2),'1250.00')]:
        records[day]=Fixing(day,Decimal(rate),datetime.combine(day,time(8,24,7),KST),now_utc())
    class FixtureClient:
        def __init__(self,cancel=None):pass
        def fetch(self,day):
            if day not in records:raise NoPublication('Synthetic fixture: no data')
            return records[day]
        def close(self):pass
    path=output/'합성_검증.sqlite3';snap=collect(path,today,client_factory=FixtureClient,history=True)
    if snap.error:raise RuntimeError(snap.error)
    app=QApplication.instance() or QApplication([])
    window=Window(path,clock=lambda:datetime(2026,10,22,tzinfo=KST),auto_start=False);window.apply_snapshot(snap);window.show();app.processEvents()
    if window.day_table.item(21,1).text()!=number(records[today].rate):raise RuntimeError('GUI rate mismatch')
    if window.day_chart.plotted['current']!=[(22,records[today].rate)]:raise RuntimeError('Chart mismatch')
    export_snapshot(snap,output/'합성_환율_비교.xlsx');wb=load_workbook(output/'합성_환율_비교.xlsx')
    if wb.sheetnames!=['월평균_비교','당월_일별_비교','환율_원본데이터'] or wb.worksheets[1]['B29'].value!=1340.12:raise RuntimeError('Excel export mismatch')
    wb.close();window.status.setText('합성 실행 검증용 데이터 · 실제 환율이 아닙니다.');window.grab().save(str(output/'synthetic-dashboard.png'));window.close()
    report={'status':'passed','platform':sys.platform,'frozen':bool(getattr(sys,'frozen',False)),'synthetic_runtime':'passed','sqlite_excel_gui_chart':'passed','live':{'status':'not_run'}}
    if live:
        report['live']=live_check(output/'live',full_month=False)
        if report['live']['status']!='passed':report['status']='failed'
    save_json(output/'self-test.json',report)
    if report['status']!='passed':raise RuntimeError('Live official bank runtime verification failed: '+report['live'].get('error','unknown'))
    return report
