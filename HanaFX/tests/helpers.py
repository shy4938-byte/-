from datetime import datetime,timezone,time
from decimal import Decimal
from app.domain import Fixing,KST,NoPublication

def fixing(day,rate='1325.50'):
    return Fixing(day,Decimal(rate),datetime.combine(day,time(8,24,7),KST),datetime.now(timezone.utc))

class FakeClient:
    def __init__(self,cancel=None,records=None):self.cancel=cancel;self.records=records or {};self.calls=[];self.closed=False
    def fetch(self,day):
        self.calls.append(day)
        if day in self.records:return self.records[day]
        raise NoPublication(str(day)+' no data (test fixture)')
    def close(self):self.closed=True
