"""Small, rate-limited official-site probe. Never bypass access restrictions."""
import hashlib,json,time,sys,urllib.robotparser
from datetime import date,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

BASE='https://www.kebhana.com'
PAGE=BASE+'/cont/mall/mall15/mall1501/index.jsp?_menuNo=23100'
ENDPOINT=BASE+'/cms/rate/wpfxd651_01i_01.do'

def probe(output):
    result={'observed_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'source':ENDPOINT,'status':'unverified','samples':[]}
    session=requests.Session();session.headers.update({'User-Agent':'HanaFX/1.0 (personal first-publication FX dashboard)','Referer':PAGE})
    try:
        robots=session.get(BASE+'/robots.txt',timeout=(8,20),allow_redirects=False)
        result['robots_status']=robots.status_code
        if robots.status_code==200:
            rules=urllib.robotparser.RobotFileParser();rules.parse(robots.text.splitlines())
            result['robots_allowed']=rules.can_fetch('HanaFX',ENDPOINT)
            if not result['robots_allowed']:raise RuntimeError('Robots policy disallows automated access to the query path; stopped')
        elif robots.status_code not in (404,410):raise RuntimeError('Robots policy could not be checked: HTTP '+str(robots.status_code))
        time.sleep(1.2)
        initial=session.get(PAGE,timeout=(8,20),allow_redirects=False);result['initial_status']=initial.status_code;initial.raise_for_status()
        soup=BeautifulSoup(initial.content,'html.parser')
        names=[v.get('name','') for v in soup.select('input[name]')]
        candidates=[n for n in names if n in {'tmpInqStrDt','tmplnqStrDt','tmpinqStrDt'}]
        field=candidates[0] if candidates else 'tmpInqStrDt'
        result['date_field']=field;result['date_fields_found']=candidates
        result['terms_links']=[{'text':a.get_text(' ',strip=True),'href':a.get('href')} for a in soup.select('a[href]') if any(v in a.get_text() for v in ['이용약관','이용조건','저작권'])][:10]
        for day in ['2026-10-22','2025-10-22']:
            time.sleep(1.2);parsed=date.fromisoformat(day)
            payload={'ajax':'true','curCd':'USD',field:day,'pbldDvCd':'1','pbldSqn':'','hid_key_data':'','inqStrDt':parsed.strftime('%Y%m%d'),'inqKindCd':'1','hid_enc_data':'','requestTarget':'searchContentDiv'}
            response=session.post(ENDPOINT,data=payload,headers={'X-Requested-With':'XMLHttpRequest'},timeout=(8,20),allow_redirects=False)
            sample={'requested':day,'http_status':response.status_code,'sha256':hashlib.sha256(response.content).hexdigest(),'bytes':len(response.content)}
            html=BeautifulSoup(response.content,'html.parser');meta=html.select_one('.txtRateBox');sample['metadata']=meta.get_text(' ',strip=True) if meta else None
            sample['tables']=[]
            for table in html.find_all('table'):
                rows=[r for r in table.find_all('tr') if 'USD' in r.get_text(' ',strip=True) and r.find('td')]
                if rows:
                    sample['tables'].append({'thead':str(table.find('thead')),'usd_rows':[str(r) for r in rows]})
            if not sample['tables']:sample['response_message']=html.get_text(' ',strip=True)[:500]
            result['samples'].append(sample)
            if response.status_code in (401,403,429):raise RuntimeError('Bank access/rate restriction; stopped without workaround')
        result['status']='http_probe_completed'
    except Exception as exc:result['error']=str(exc)
    finally:
        Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2));return result

if __name__=='__main__':probe(sys.argv[1] if len(sys.argv)>1 else 'live_probe.json')
