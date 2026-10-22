from dataclasses import dataclass,field
from datetime import date,datetime,timedelta
from calendar import monthrange
from decimal import Decimal
from .domain import now_utc


def month_dates(year,month,through=None):
    return [date(year,month,d) for d in range(1,min(through or 31,monthrange(year,month)[1])+1)]

def prior_day(day):
    try:return day.replace(year=day.year-1)
    except ValueError:return None  # Feb 29 has no identical prior-year date.


def required_dates(today):
    dates=[]
    # Prioritize this month's recent days so the dashboard fills immediately.
    for d in range(today.day,0,-1):
        dates.append(date(today.year,today.month,d))
        if d<=monthrange(today.year-1,today.month)[1]:dates.append(date(today.year-1,today.month,d))
    for month in range(1,today.month):
        dates.extend(month_dates(today.year,month));dates.extend(month_dates(today.year-1,month))
    return list(dict.fromkeys(dates))

@dataclass
class Snapshot:
    asof:date
    records:dict=field(default_factory=dict)
    coverage:dict=field(default_factory=dict)
    fresh:set=field(default_factory=set)
    retrieved_at:datetime=field(default_factory=now_utc)
    done:int=0
    total:int=0
    cancelled:bool=False
    error:str=''

@dataclass(frozen=True)
class Summary:
    average:Decimal|None
    observed:int
    no_data:int
    errors:int
    pending:int
    @property
    def complete(self):return not (self.errors or self.pending)
    @property
    def status(self):
        if self.pending or self.errors:return f'부분 자료 · 고시 {self.observed} / 미수집 {self.pending} / 오류 {self.errors}'
        return f'고시 {self.observed}일 / 고시 없음 {self.no_data}일' if self.observed else '고시 데이터 없음'


def summarize(snapshot,year,month):
    dates=month_dates(year,month);values=[];no_data=errors=pending=0
    for d in dates:
        c=snapshot.coverage.get(d)
        if d in snapshot.records:values.append(snapshot.records[d].rate)
        if c is None:pending+=1
        elif c.status=='no_data':no_data+=1
        elif c.status=='error':errors+=1
    return Summary(sum(values,Decimal(0))/len(values) if values else None,len(values),no_data,errors,pending)


def difference(current,previous):
    if current is None or previous is None:return None,None
    delta=current-previous;return delta,(delta/previous*100 if previous else None)


def monthly_rows(snapshot):
    rows=[]
    for month in range(1,snapshot.asof.month):
        a=summarize(snapshot,snapshot.asof.year,month);b=summarize(snapshot,snapshot.asof.year-1,month);delta,percent=difference(a.average,b.average)
        rows.append(dict(month=month,current=a.average,previous=b.average,delta=delta,percent=percent,current_status=a.status,previous_status=b.status,complete=a.complete and b.complete))
    return rows


def daily_rows(snapshot):
    rows=[];today=snapshot.asof
    def lookup(d):
        if d is None:return None,'날짜 없음'
        record=snapshot.records.get(d);coverage=snapshot.coverage.get(d)
        if record:return record.rate,('새 조회' if d in snapshot.fresh else '저장된 데이터')+(' · 재확인 실패' if coverage and coverage.status=='error' else '')
        return None,{'no_data':'고시 데이터 없음','error':'조회 오류'}.get(coverage.status,'미수집') if coverage else '미수집'
    for day in range(1,today.day+1):
        current=date(today.year,today.month,day);previous=date(today.year-1,today.month,day) if day<=monthrange(today.year-1,today.month)[1] else None
        a,sa=lookup(current);b,sb=lookup(previous);delta,percent=difference(a,b)
        rows.append(dict(day=day,current=a,previous=b,delta=delta,percent=percent,current_status=sa,previous_status=sb))
    return rows


def cards(snapshot):
    for offset in range(15):
        day=snapshot.asof-timedelta(days=offset)
        if day in snapshot.records:
            current=snapshot.records[day];target=prior_day(day);previous=snapshot.records.get(target) if target else None
            delta,percent=difference(current.rate,previous.rate if previous else None)
            return dict(current=current,previous=previous,comparison_date=target,delta=delta,percent=percent,is_today=day==snapshot.asof,cached=day not in snapshot.fresh)
    return dict(current=None,previous=None,comparison_date=prior_day(snapshot.asof),delta=None,percent=None,is_today=False,cached=False)
