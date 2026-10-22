"""Official public endpoint only. No authentication/captcha/WAF workarounds."""
from datetime import date
import re,time,threading,urllib.robotparser
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from .domain import PAGE,SOURCE,HanaError,AccessRestricted,Cancelled
from .parser import parse_fixing

BASE='https://www.kebhana.com'
INTERVAL=1.2

def payload_for(day,date_field='tmpInqStrDt'):
    return {'ajax':'true','curCd':'USD',date_field:day.isoformat(),'pbldDvCd':'1','pbldSqn':'','hid_key_data':'','inqStrDt':day.strftime('%Y%m%d'),'inqKindCd':'1','hid_enc_data':'','requestTarget':'searchContentDiv'}


class HanaClient:
    def __init__(self,cancel=None,session=None,interval=INTERVAL):
        self.cancel=cancel or threading.Event();self.session=session or requests.Session();self.interval=max(INTERVAL,interval)
        self.session.headers.update({'User-Agent':'HanaFX/1.0 (personal first-publication FX dashboard)','Referer':PAGE,'Accept':'text/html,application/xhtml+xml'})
        self.ready=False;self.last=0.;self.date_field='tmpInqStrDt';self.policy={}
    def close(self):self.session.close()
    def _wait(self,seconds):
        if self.cancel.wait(max(0,seconds)):raise Cancelled('사용자가 수집을 취소했습니다.')
    def _request(self,method,url,**kwargs):
        if urlparse(url).hostname!='www.kebhana.com':raise AccessRestricted('공식 하나은행 도메인 외에는 접속하지 않습니다.')
        last_error=None
        for attempt in range(3):
            self._wait(self.interval-(time.monotonic()-self.last))
            try:
                response=self.session.request(method,url,timeout=(6,18),allow_redirects=False,**kwargs)
                self.last=time.monotonic()
                if response.status_code in (401,403):raise AccessRestricted(f'하나은행 접근 제한 HTTP {response.status_code}. 인증·차단을 우회하지 않고 중단했습니다.')
                if 300<=response.status_code<400:raise AccessRestricted('은행이 다른 위치로 이동을 요청했습니다. 접속 정책을 확인한 후 사용하세요.')
                if response.status_code in (429,500,502,503,504):
                    last_error=HanaError('하나은행 일시 오류 HTTP '+str(response.status_code))
                    retry=response.headers.get('Retry-After','')
                    if retry and (not retry.isdigit() or int(retry)>60):raise AccessRestricted('은행의 재시도 대기 지시가 있어 자동 수집을 중단했습니다. 잠시 후 다시 조회하세요.')
                    if attempt<2:self._wait(max(2**attempt,int(retry or 0)));continue
                    raise last_error
                if response.status_code>=400 and response.status_code not in (404,410):raise HanaError('은행 응답 오류 HTTP '+str(response.status_code))
                if len(response.content)>8*1024*1024:raise HanaError('은행 응답이 예상보다 큽니다. 수집을 중단했습니다.')
                return response
            except (requests.Timeout,requests.ConnectionError) as exc:
                self.last=time.monotonic();last_error=HanaError('하나은행 연결 실패 또는 시간 초과. 인터넷 연결을 확인하세요.')
                if attempt<2:self._wait(2**attempt)
        raise last_error or HanaError('환율 조회 실패')
    def initialize(self):
        if self.ready:return
        robots=self._request('GET',BASE+'/robots.txt')
        self.policy={'robots_status':robots.status_code}
        if robots.status_code==200:
            rp=urllib.robotparser.RobotFileParser();rp.parse(robots.text.splitlines())
            self.policy['robots_allowed']=rp.can_fetch('HanaFX',SOURCE)
            if not self.policy['robots_allowed']:raise AccessRestricted('하나은행 robots 정책에서 자동 조회 경로 접근을 허용하지 않아 중단했습니다.')
        elif robots.status_code not in (404,410):raise AccessRestricted('은행의 자동 접근 정책을 확인하지 못했습니다.')
        response=self._request('GET',PAGE)
        if response.status_code!=200:raise HanaError('공식 조회 페이지를 열지 못했습니다.')
        soup=BeautifulSoup(response.content,'html.parser')
        names=[v.get('name','') for v in soup.select('input[name]')]
        for candidate in ['tmpInqStrDt','tmplnqStrDt','tmpinqStrDt']:
            if candidate in names:self.date_field=candidate;break
        self.policy['date_field']=self.date_field;self.ready=True
    def fetch(self,day):
        self.initialize()
        response=self._request('POST',SOURCE,data=payload_for(day,self.date_field),headers={'X-Requested-With':'XMLHttpRequest'})
        if response.status_code!=200:raise HanaError('환율 조회 HTTP '+str(response.status_code))
        return parse_fixing(response.content,day)
