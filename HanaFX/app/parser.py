"""Select by semantic header, never by a hardcoded numeric column offset."""
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
import hashlib,re
from bs4 import BeautifulSoup
from .domain import Fixing,ValidationError,NoPublication,KST,now_utc


def expanded_grid(rows):
    grid=[];occupied={}
    for ri,row in enumerate(rows):
        cells={col:text for (r,col),text in occupied.items() if r==ri};col=0
        for cell in row.find_all(['th','td'],recursive=False):
            while col in cells:col+=1
            text=' '.join(cell.stripped_strings)
            try:rs=int(cell.get('rowspan',1));cs=int(cell.get('colspan',1))
            except (ValueError,TypeError):raise ValidationError('표의 행·열 병합 정보를 읽지 못했습니다.')
            if not 1<=rs<=30 or not 1<=cs<=60:raise ValidationError('예상 범위를 벗어난 표 구조입니다.')
            for dr in range(rs):
                for dc in range(cs):
                    occupied[(ri+dr,col+dc)]=text
                    if dr==0:cells[col+dc]=text
            col+=cs
        grid.append([cells.get(i,'') for i in range(max(cells,default=-1)+1)])
    return grid


def parse_fixing(html,requested,collected_at=None):
    soup=BeautifulSoup(html,'html.parser');metadata=soup.select_one('p.txtRateBox')
    no_data=bool(re.search(r'(?:조회|고시|검색)[^.!。]{0,60}(?:없습니다|없음|존재하지)',soup.get_text(' ',strip=True)))
    if metadata is None:
        if no_data:raise NoPublication(f'{requested}: 고시 데이터 없음')
        raise ValidationError('기준일·고시일시 영역을 찾지 못했습니다. 접속 제한 또는 은행 HTML 변경을 확인하세요.')
    text=metadata.get_text(' ',strip=True)
    pattern=r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일'
    bm=re.search(r'기준일\s*:\s*'+pattern,text);pm=re.search(r'고시일시\s*:\s*'+pattern,text)
    if not bm or not pm:raise ValidationError('응답의 기준일과 고시일을 각각 검증하지 못했습니다.')
    try:base=date(*map(int,bm.groups()));published=date(*map(int,pm.groups()))
    except ValueError:raise ValidationError('올바르지 않은 응답 날짜입니다.') from None
    if published<requested and base in {requested,published} and re.findall(r'\(\s*(\d+)\s*회차\s*\)',text)==['1']:
        raise NoPublication(f'{requested}: 요청일 고시 대신 이전 고시일 {published}을 반환했습니다. 요청일의 값으로 사용하지 않습니다.')
    if base!=requested or published!=requested:
        raise ValidationError(f'요청일 {requested}과 응답 기준일 {base}/고시일 {published}이 다릅니다. 다른 날짜의 값을 대입하지 않습니다.')
    rounds=re.findall(r'\(\s*(\d+)\s*회차\s*\)',text)
    if rounds!=['1']:raise ValidationError('최초 1회차 응답이 아닙니다. 결과를 저장하지 않았습니다.')
    time=re.search(r'(\d{1,2})\s*시\s*(\d{1,2})\s*분\s*(\d{1,2})\s*초',text[pm.end():].split('조회시각')[0])
    if not time:raise ValidationError('고시 시각을 검증하지 못했습니다.')
    try:announced=datetime(requested.year,requested.month,requested.day,*map(int,time.groups()),tzinfo=KST)
    except ValueError:raise ValidationError('올바르지 않은 고시 시각입니다.') from None
    candidates=[]
    for table in soup.find_all('table'):
        head=table.find('thead')
        rows=head.find_all('tr') if head else [r for r in table.find_all('tr') if r.find('th') and not r.find('td')]
        grid=expanded_grid(rows)
        width=max((len(r) for r in grid),default=0)
        indices=[i for i in range(width) if any('매매기준율' in re.sub(r'\s+','',r[i]) for r in grid if i<len(r))]
        usd=[]
        for row in table.find_all('tr'):
            cells=row.find_all('td',recursive=False)
            if not cells:continue
            label=cells[0].get_text(' ',strip=True)
            if re.search(r'(?<![A-Z])USD(?![A-Z])',label):usd.append(row)
        if not usd:continue
        if len(indices)!=1 or len(usd)!=1:raise ValidationError('USD 행 또는 매매기준율 열을 고유하게 식별하지 못했습니다.')
        data=expanded_grid(usd)[0];index=indices[0]
        if index>=len(data):raise ValidationError('매매기준율 열이 데이터 행과 일치하지 않습니다.')
        raw=data[index].strip()
        if not re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}',raw):raise ValidationError('USD 매매기준율 숫자 형식이 잘못되었습니다: '+raw[:40])
        try:rate=Decimal(raw.replace(',',''))
        except InvalidOperation:raise ValidationError('매매기준율 숫자 변환 실패') from None
        candidates.append(rate)
    if len(candidates)!=1:
        if not candidates and no_data:raise NoPublication(f'{requested}: USD 고시 데이터 없음')
        raise ValidationError('USD 매매기준율 표를 고유하게 찾지 못했습니다.')
    raw=html.encode('utf-8') if isinstance(html,str) else html
    return Fixing(requested,candidates[0],announced,collected_at or now_utc(),response_sha256=hashlib.sha256(raw).hexdigest())
