"""Layout extraction independent of manufacturers and page numbers."""
from dataclasses import dataclass
from pathlib import Path
import statistics
import re
import fitz
import pdfplumber

class AnalysisError(Exception):
    pass

@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    @property
    def center(self):
        return (self.x0+self.x1)/2

@dataclass
class Line:
    words: list
    @property
    def text(self):
        return ' '.join(w.text for w in self.words)
    @property
    def y(self):
        return statistics.mean((w.y0+w.y1)/2 for w in self.words)

@dataclass
class Page:
    number: int
    text: str
    lines: list

@dataclass
class Table:
    page: int
    rows: list
    method: str = 'ruled table'

@dataclass
class Document:
    source: str
    pages: list
    tables: list
    warnings: list
    @property
    def text(self):
        return '\n'.join(p.text for p in self.pages)


def layout_lines(words):
    """Font-relative baseline grouping; no fixed page/template coordinates."""
    raw=[Word(*v[:4],v[4]) for v in words if v[4].strip()]
    if not raw:
        return []
    tolerance=max(1.5,statistics.median(w.y1-w.y0 for w in raw)*.45)
    lines=[]
    for word in sorted(raw,key=lambda w:((w.y0+w.y1)/2,w.x0)):
        line=next((l for l in reversed(lines[-4:]) if abs(l.y-(word.y0+word.y1)/2)<=tolerance),None)
        if line is None:
            line=Line([]);lines.append(line)
        line.words.append(word)
    for line in lines:
        line.words.sort(key=lambda w:w.x0)
    return sorted(lines,key=lambda l:l.y)


def read_document(path,ocr=False):
    path=Path(path).resolve()
    pages,tables,warnings=[],[],[]
    try:
        with fitz.open(path) as pdf:
            if pdf.needs_pass:
                raise AnalysisError('암호화 PDF입니다. 암호를 해제한 파일을 사용하세요.')
            for number,page in enumerate(pdf,1):
                text=page.get_text(sort=True)
                words=page.get_text('words')
                if ocr and len(re.sub(r'\W','',text))<30:
                    from .resources import ROOT
                    from .ocr import data_path
                    data=data_path(ROOT/'assets'/'ocr')
                    try:
                        tp=page.get_textpage_ocr(language='eng+kor',dpi=200,full=True,tessdata=str(data))
                        text=page.get_text(textpage=tp,sort=True);words=page.get_text('words',textpage=tp)
                        warnings.append(f'p.{number}: 내장 OCR로 읽었습니다. 숫자·단위를 원본 이미지와 대조하세요.')
                    except Exception as exc:
                        raise AnalysisError(f'p.{number}: OCR에 실패했습니다. OCR 언어 파일·페이지 상태를 확인하세요.') from exc
                pages.append(Page(number,text,layout_lines(words)))
                if not text.strip():
                    warnings.append(f'p.{number}: 텍스트가 없어 분석하지 못했습니다. 스캔 페이지는 OCR이 필요합니다.')
        if not any(p.text.strip() for p in pages):
            raise AnalysisError('텍스트 없는 스캔 PDF입니다. OCR 처리된 PDF를 사용하세요. 내장 OCR은 지원하지 않습니다.')
        with pdfplumber.open(path) as pdf:
            for number,page in enumerate(pdf.pages,1):
                try:
                    for rows in page.extract_tables():
                        if rows:
                            tables.append(Table(number,rows))
                except Exception:
                    warnings.append(f'p.{number}: 표 분석 실패. 좌표/텍스트 추출로 계속 분석했습니다.')
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f'PDF 읽기 실패: {exc}') from exc
    document=Document(str(path),pages,tables,warnings)
    tables.extend(split_catalogues(document))
    tables.extend(geometric_catalogues(document))
    tables.extend(capacity_matrices(document))
    return document


def geometric_catalogues(document):
    """Recover unruled product catalogues by header positions and real baselines."""
    result=[]
    model_re=re.compile(r'part\s*(?:number|no\.?|#)|model(?:\s*(?:number|no\.?))?|product\s*(?:code|number)',re.I)
    capacity_re=re.compile(r'capacity|density|module\s*size',re.I)
    for page in document.pages:
        for hi,header in enumerate(page.lines):
            label=header.text
            if re.search(r'model\s+name',label,re.I) and re.search(r'model\s+code',label,re.I):continue
            mm,cm=model_re.search(label),capacity_re.search(label)
            if not mm or not cm:
                continue
            spans=[];cursor=0
            for word in header.words:
                spans.append((cursor,cursor+len(word.text),word));cursor+=len(word.text)+1
            def center(match):
                ws=[w for a,b,w in spans if a<match.end() and b>match.start()]
                return (min(w.x0 for w in ws)+max(w.x1 for w in ws))/2
            mx,cx=center(mm),center(cm)
            # Catalogue layouts may put the model before or after the capacity.
            mid=(mx+cx)/2
            others=[w.center for a,b,w in spans if a>=cm.end() and w.center>cx]
            right=min(others) if others else float('inf')
            rows=[['Part Number','Capacity']]
            previous_y=header.y
            for line in page.lines[hi+1:]:
                if line.y-previous_y>max(30,(header.words[0].y1-header.words[0].y0)*4):
                    break
                if re.search(r'NOTE\s*:|\[Table|features|parameters|ordering information',line.text,re.I):
                    break
                capacity_parts=[w.text for w in line.words if (w.center>mid and w.center<right) if mx<cx] if mx<cx else [w.text for w in line.words if w.center<mid]
                model_parts=[w.text for w in line.words if w.center<mid] if mx<cx else [w.text for w in line.words if w.center>mid]
                cap=''.join(capacity_parts)
                cap_match=re.match(r'^(\d+(?:\.\d+)?\s*(?:GB|TB))\b',cap)
                if not cap_match:
                    continue
                model=''.join(model_parts).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z0-9.$/\-]*\d[A-Za-z0-9.$/\-]*',model) and len(model)>=4:
                    rows.append([model,cap_match[1]])
                    previous_y=line.y
            if len(rows)>1:
                result.append(Table(page.number,rows,'unruled catalogue'))
    return result


def split_catalogues(document):
    """Separate SKU and packaging columns, including vertically merged rows."""
    result=[]
    for page in document.pages:
        for hi,header in enumerate(page.lines):
            patterns=[r'capacity|density',r'model\s+name',r'box\s+contents',r'model\s+code']
            matches=[re.search(p,header.text,re.I) for p in patterns]
            if not all(matches):continue
            spans=[];cursor=0
            for w in header.words:
                spans.append((cursor,cursor+len(w.text),w));cursor+=len(w.text)+1
            anchors=[]
            for m in matches:
                ws=[w for a,b,w in spans if a<m.end() and b>m.start()]
                anchors.append((min(w.x0 for w in ws)+max(w.x1 for w in ws))/2)
            order=sorted(range(4),key=lambda i:anchors[i]);edges=[(anchors[a]+anchors[b])/2 for a,b in zip(order,order[1:])]
            rows=[['Part Number','Capacity','Model Code']];record=None
            def flush():
                if record and len(record['models'])==1:
                    rows.append([next(iter(record['models'])),record['cap'],'\n'.join(record['codes'])])
            for line in page.lines[hi+1:]:
                if line.y-header.y>200 or re.match(r'\*|For more|TEST CONFIGURATION',line.text,re.I):break
                cells=['']*4
                for w in line.words:
                    col=sum(w.center>e for e in edges);cells[order[col]]+=' '+w.text
                cells=[v.strip() for v in cells]
                cap=re.fullmatch(r'\d+(?:\.\d+)?\s*(?:GB|TB)',cells[0])
                if cap:
                    flush();record={'cap':cap[0],'models':set(),'codes':[]}
                if record:
                    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./$-]*',cells[1]):record['models'].add(cells[1])
                    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./$-]*',cells[3]) and cells[3] not in record['codes']:record['codes'].append(cells[3])
            flush()
            if len(rows)>1:result.append(Table(page.number,rows,'split catalogue columns'))
    return result


def capacity_matrices(document):
    """Recover open-ended capacity columns from text positions, not ruled edges."""
    result=[]
    for page in document.pages:
        for hi,header in enumerate(page.lines):
            if not re.search(r'capacity\s*(?:\d+\))?\s',header.text,re.I):continue
            caps=[w for w in header.words if re.fullmatch(r'\d+(?:\.\d+)?(?:GB|TB)',w.text)]
            if len(caps)<2:continue
            labels=[w for w in header.words if w.x1<caps[0].x0]
            if not labels:continue
            left=(max(w.x1 for w in labels)+caps[0].center)/2
            edges=[left]+[(a.center+b.center)/2 for a,b in zip(caps,caps[1:])]
            rows=[['Metric','Queue Depth','Thread']+[w.text for w in caps]]
            qd=thread=''
            for line in page.lines[hi+1:]:
                if re.match(r'\d+\)\s|Revision\b',line.text,re.I):break
                label=' '.join(w.text for w in line.words if w.center<left)
                q=re.search(r'\bQD\s*(\d+)',label,re.I);t=re.search(r'\bThread\s*(\d+)',label,re.I)
                if q:qd=q[1];thread=''
                if t:thread=t[1]
                cells=['']*len(caps)
                for w in line.words:
                    if w.center>=left:cells[sum(w.center>e for e in edges)-1]+=' '+w.text
                if any(cells):rows.append([label,qd,thread]+[v.strip() for v in cells])
            # QD and Thread labels may occupy different baselines of a merged cell.
            for row in rows[1:]:
                if row[1] and not row[2] and re.search(r'ran\.?\s+(read|write)',row[0],re.I):
                    threads={r[2] for r in rows[1:] if r[1]==row[1] and r[2] and re.search(r'ran\.?\s+(read|write)',r[0],re.I)}
                    if len(threads)==1:row[2]=next(iter(threads))
            if len(rows)>1:result.append(Table(page.number,rows,'capacity coordinates'))
    return result
