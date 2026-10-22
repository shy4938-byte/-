from dataclasses import dataclass
from datetime import date,datetime,timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

KST=ZoneInfo('Asia/Seoul')
SOURCE='https://www.kebhana.com/cms/rate/wpfxd651_01i_01.do'
PAGE='https://www.kebhana.com/cont/mall/mall15/mall1501/index.jsp?_menuNo=23100'

class HanaError(Exception):pass
class ValidationError(HanaError):pass
class NoPublication(HanaError):pass
class Cancelled(HanaError):pass
class AccessRestricted(HanaError):pass

@dataclass(frozen=True)
class Fixing:
    day:date
    rate:Decimal
    announced_at:datetime
    collected_at:datetime
    currency:str='USD'
    round:int=1
    source:str=SOURCE
    validation:str='verified:first_round_usd_base_rate'
    response_sha256:str=''
    def __post_init__(self):
        if self.currency!='USD' or self.round!=1 or not self.rate.is_finite() or not Decimal('0')<self.rate<Decimal('100000'):
            raise ValidationError('USD 최초 고시 매매기준율 검증 실패')
        if self.announced_at.tzinfo is None or self.collected_at.tzinfo is None or self.announced_at.astimezone(KST).date()!=self.day:
            raise ValidationError('고시 날짜·시간 검증 실패')

def now_kst():return datetime.now(KST)
def now_utc():return datetime.now(timezone.utc)
