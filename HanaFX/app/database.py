import sqlite3
from dataclasses import dataclass
from datetime import date,datetime,timedelta
from decimal import Decimal
from pathlib import Path
from .domain import Fixing,now_utc

@dataclass(frozen=True)
class Coverage:
    day:date
    status:str
    checked_at:datetime
    detail:str=''

class Database:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.connection=sqlite3.connect(self.path,timeout=10)
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.executescript('''CREATE TABLE IF NOT EXISTS fixings(
          day TEXT NOT NULL,currency TEXT NOT NULL CHECK(currency='USD'),round INTEGER NOT NULL CHECK(round=1),
          rate TEXT NOT NULL,announced_at TEXT NOT NULL,collected_at TEXT NOT NULL,source TEXT NOT NULL,validation TEXT NOT NULL,response_sha256 TEXT NOT NULL,
          PRIMARY KEY(day,currency,round));
          CREATE TABLE IF NOT EXISTS coverage(day TEXT PRIMARY KEY,status TEXT NOT NULL CHECK(status IN ('ok','no_data','error')),checked_at TEXT NOT NULL,detail TEXT NOT NULL);
        ''');self.connection.commit()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):self.connection.close()
    def put(self,fixing):
        with self.connection:
            self.connection.execute('INSERT OR REPLACE INTO fixings VALUES(?,?,?,?,?,?,?,?,?)',(fixing.day.isoformat(),fixing.currency,fixing.round,str(fixing.rate),fixing.announced_at.isoformat(),fixing.collected_at.isoformat(),fixing.source,fixing.validation,fixing.response_sha256))
            self.connection.execute('INSERT OR REPLACE INTO coverage VALUES(?,?,?,?)',(fixing.day.isoformat(),'ok',fixing.collected_at.isoformat(),'USD 최초 1회차 매매기준율 검증 완료'))
    def mark(self,day,status,detail,checked_at=None):
        if status not in ('no_data','error'):raise ValueError('unsupported coverage status')
        if status=='no_data' and self.connection.execute('SELECT 1 FROM fixings WHERE day=?',(day.isoformat(),)).fetchone():
            status='error';detail='저장된 검증값과 현재 고시 없음 응답이 다릅니다. 저장값 보존: '+detail
        with self.connection:
            self.connection.execute('INSERT OR REPLACE INTO coverage VALUES(?,?,?,?)',(day.isoformat(),status,(checked_at or now_utc()).isoformat(),detail))
    def load(self,today):
        start=date(today.year-2,1,1).isoformat();end=today.isoformat();records={}
        for r in self.connection.execute('SELECT * FROM fixings WHERE day BETWEEN ? AND ? AND validation=?',(start,end,'verified:first_round_usd_base_rate')):
            fixing=Fixing(date.fromisoformat(r[0]),Decimal(r[3]),datetime.fromisoformat(r[4]),datetime.fromisoformat(r[5]),r[1],r[2],r[6],r[7],r[8]);records[fixing.day]=fixing
        coverage={date.fromisoformat(r[0]):Coverage(date.fromisoformat(r[0]),r[1],datetime.fromisoformat(r[2]),r[3]) for r in self.connection.execute('SELECT * FROM coverage WHERE day BETWEEN ? AND ?',(start,end))}
        return records,coverage
    def reusable(self,day,today,force=False):
        if force or day==today:return False
        row=self.connection.execute('SELECT status,checked_at FROM coverage WHERE day=?',(day.isoformat(),)).fetchone()
        if not row:return False
        status,stamp=row;age=now_utc()-datetime.fromisoformat(stamp)
        if status=='ok':return True
        if status=='no_data':return day<today-timedelta(days=3) or age<timedelta(hours=6)
        return age<timedelta(minutes=30)
