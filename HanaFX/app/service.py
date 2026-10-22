from datetime import timedelta
import threading
from .analytics import Snapshot,required_dates,prior_day
from .database import Database
from .domain import NoPublication,Cancelled,AccessRestricted,HanaError,ValidationError
from .hana_client import HanaClient


def cached_snapshot(db_path,today):
    with Database(db_path) as db:records,coverage=db.load(today)
    return Snapshot(today,records,coverage,total=len(required_dates(today)))


def collect(db_path,today,cancel=None,force=False,progress=None,updated=None,client_factory=HanaClient):
    cancel=cancel or threading.Event();planned=required_dates(today);seen=set();fresh=set();completed=0;failure='';is_cancelled=False;errors_in_a_row=0
    client=client_factory(cancel=cancel)
    with Database(db_path) as db:
        def snapshot():
            records,coverage=db.load(today)
            return Snapshot(today,records,coverage,set(fresh),done=completed,total=len(set(planned)|seen),cancelled=is_cancelled,error=failure)
        def visit(day):
            nonlocal completed,errors_in_a_row
            if day in seen:return
            if cancel.is_set():raise Cancelled('사용자가 취소했습니다.')
            seen.add(day)
            if progress:progress(completed,len(set(planned)|seen),str(day)+' USD 최초 고시 조회')
            if not db.reusable(day,today,force):
                try:
                    fixing=client.fetch(day)
                    if fixing.day!=day:raise ValidationError('요청 날짜와 다른 결과를 저장할 수 없습니다.')
                    db.put(fixing);fresh.add(day);errors_in_a_row=0
                except NoPublication as exc:db.mark(day,'no_data',str(exc));errors_in_a_row=0
                except AccessRestricted:raise
                except Cancelled:raise
                except HanaError as exc:
                    db.mark(day,'error',str(exc));errors_in_a_row+=1
                    if errors_in_a_row>=3:raise HanaError('연속 조회 오류로 은행에 추가 요청하지 않고 중단했습니다. '+str(exc))
            completed+=1
            if progress:progress(completed,len(set(planned)|seen),str(day)+' 확인 완료')
            if updated and (completed<=3 or completed%10==0):updated(snapshot())
        try:
            # Latest valid first fixing; never rename a prior publication as today's.
            anchor=None
            for offset in range(15):
                day=today-timedelta(days=offset);visit(day)
                records,_=db.load(today)
                if day in records:anchor=day;break
            if anchor and prior_day(anchor):visit(prior_day(anchor))
            for day in planned:visit(day)
        except Cancelled:is_cancelled=True
        except Exception as exc:failure=str(exc)
        finally:client.close()
        result=snapshot()
        if updated:updated(result)
        return result
