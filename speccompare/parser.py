"""Conservative offline extraction. Ambiguous specifications remain unconfirmed."""
import re
from pathlib import Path
import fitz
import pdfplumber
from .schema import ALIASES, FIELDS, EXTRAS, Product, Value

class AnalysisError(Exception):
    pass

def normalize(value):
    match = re.fullmatch(r'([\d,.]+)\s*GB/s', value, re.I)
    if match:
        return f'{float(match[1].replace(",", ""))*1000:g} MB/s'
    return value.strip()

def alias_match(label, key):
    clean = lambda s: re.sub(r'[\s_:()/-]+', ' ', s.casefold()).strip()
    return clean(label) in [clean(x) for x in ALIASES[key]]

def analyze(path, category):
    path = str(Path(path).resolve())
    pages, tables = [], []
    try:
        with fitz.open(path) as doc:
            if doc.needs_pass:
                raise AnalysisError('암호화 PDF입니다. 암호를 해제한 파일을 사용하세요.')
            for index, page in enumerate(doc, 1):
                pages.append((index, page.get_text(sort=True)))
        if not any(text.strip() for _, text in pages):
            raise AnalysisError('텍스트 없는 스캔 PDF입니다. 내장 OCR은 지원하지 않습니다. OCR 처리된 PDF를 사용하세요.')
        with pdfplumber.open(path) as doc:
            for index, page in enumerate(doc.pages, 1):
                for table in page.extract_tables():
                    tables.append((index, table))
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f'PDF 읽기 실패: {exc}') from exc
    keys = FIELDS[category] + EXTRAS[category]
    products = {}
    # Row-oriented product catalogues must not be treated as model-column tables.
    def clean_label(text):
        return re.sub(r'\d+\)|\(Up to\)', '', str(text or ''), flags=re.I).strip()
    for page, table in tables:
        for header_index, header_row in enumerate(table):
            if not header_row:
                continue
            labels = [clean_label(x) for x in header_row]
            model_cols = [i for i,x in enumerate(labels) if alias_match(x,'모델명')]
            cap_cols = [i for i,x in enumerate(labels) if alias_match(x,'용량')]
            if len(model_cols)!=1 or len(cap_cols)!=1:
                continue
            mc, cc = model_cols[0], cap_cols[0]
            for row in table[header_index+1:]:
                if len(row)<=max(mc,cc) or not row[mc] or not row[cc]:
                    continue
                model,capacity = str(row[mc]).strip(),str(row[cc]).strip()
                if not re.fullmatch(r'[\d.]+\s*(?:GB|TB)',capacity,re.I):
                    continue
                product=products.setdefault(model,Product(path,category,{k:Value() for k in keys}))
                evidence=' | '.join(str(v or '') for v in row)
                assign(product,'모델명',model,page,evidence)
                assign(product,'용량',capacity,page,evidence)
    # Capacity matrices join to catalogue products only through an exact capacity match.
    if products and category=='SSD':
        for page,table in tables:
            for hi,header in enumerate(table):
                if not header:
                    continue
                capacity_cols={i:str(v).replace(' ','').upper() for i,v in enumerate(header) if re.fullmatch(r'[\d.]+\s*(?:GB|TB)',str(v or ''),re.I)}
                if not capacity_cols or not any(str(x or '').lower()=='parameter' for x in header):
                    continue
                unit_col=next((i for i,v in enumerate(header) if str(v or '').lower()=='unit'),None)
                for row in table[hi+1:]:
                    label=clean_label(row[0]) if row else ''
                    matched=[k for k in keys if alias_match(label,k)]
                    for col,capacity in capacity_cols.items():
                        if col>=len(row) or not row[col]:
                            continue
                        unit=str(row[unit_col] or '') if unit_col is not None and unit_col<len(row) else ''
                        value=str(row[col]).strip()+' '+unit
                        evidence=' | '.join(str(v or '') for v in header)+'\n'+' | '.join(str(v or '') for v in row)
                        for product in products.values():
                            if product.values['용량'].text.replace(' ','').upper()==capacity:
                                for key in matched: assign(product,key,value.strip(),page,evidence)
        for product in products.values():
            for page,text in pages:
                # Shared specifications are read only from an explicit feature page,
                # never from register defaults or revision-history maxima.
                if 'Drive Configuration' not in text or 'Features' not in text:
                    continue
                if re.search(r'SAMSUNG',pages[0][1],re.I):
                    assign(product,'제조사','Samsung',1,next(line.strip() for line in pages[0][1].splitlines() if 'SAMSUNG' in line.upper()))
                patterns={'인터페이스':r'PCI Express[®™]*\s+Gen\.\d+\s+x\d+', 'PCIe 세대':r'PCIe[®™]*\s+Gen\.\d+', 'NVMe':r'NVM Express[^\n]*?Rev\.\s*[\d.]+[a-z]?'}
                for key,pattern in patterns.items():
                    m=re.search(pattern,text,re.I)
                    if m: assign(product,key,m[0],page,m[0])
        return list(products.values())
    # Only explicit model-header tables allow assigning separate product columns.
    for page, table in tables:
        header = next((i for i,r in enumerate(table) if r and r[0] and alias_match(r[0], '모델명') and sum(bool(v) for v in r[1:]) > 0), None)
        if header is None:
            continue
        if any(alias_match(clean_label(v),'용량') for v in table[header][1:] if v):
            continue
        for col, model in enumerate(table[header][1:], 1):
            if not model or '\n' in model:
                continue
            product = products.setdefault(model, Product(path, category, {k: Value() for k in keys}))
            assign(product, '모델명', model, page, ' | '.join(str(v or '') for v in table[header]))
            for row in table[header+1:]:
                if not row or not row[0] or len(row) <= col or not row[col]:
                    continue
                for key in keys:
                    if alias_match(row[0], key):
                        assign(product, key, row[col], page, ' | '.join(str(v or '') for v in row))
    if products:
        return list(products.values())
    product = Product(path, category, {k: Value() for k in keys})
    candidates = {}
    for page, text in pages:
        for line in text.splitlines():
            match = re.match(r'^\s*(.+?)\s*[:：]\s*(.+?)\s*$', line)
            if not match:
                continue
            for key in keys:
                if alias_match(match[1], key):
                    candidates.setdefault(key, []).append((match[2], page, line))
    models = {v[0] for v in candidates.get('모델명', [])}
    if len(models) > 1:
        product.warnings.append('복수 모델의 열 구조를 확정할 수 없습니다. 모델별 PDF로 분리하거나 수동 입력하세요.')
        return [product]
    for key, values in candidates.items():
        distinct = {v[0] for v in values}
        if len(distinct) == 1:
            assign(product, key, *values[0])
        else:
            product.values[key] = Value(evidence='\n'.join(f'p.{p}: {s}' for _,p,s in values), status='검토 필요')
    product.warnings.append('규칙 기반 추출 결과입니다. 원문을 확인한 뒤 확인 완료로 표시하세요.')
    return [product]

def assign(product, key, text, page, evidence):
    text = normalize(str(text))
    if key == '소비전력':
        kind = re.search(r'TDP|TGP|TBP|total graphics power|total board power', evidence, re.I)
        if kind:
            text += ' (' + kind[0] + ')'
    units = {
        '용량': r'(?:[KMGT]B|Gbit|Gb)\b', 'VRAM 용량': r'[KMGT]B\b',
        '동작속도': r'(?:MT/s|MHz|GHz)', '순차읽기 속도': r'(?:MB/s|GB/s)',
        '순차쓰기 속도': r'(?:MB/s|GB/s)', '랜덤읽기 속도': r'IOPS',
        '랜덤쓰기 속도': r'IOPS', '메모리 대역폭': r'(?:MB/s|GB/s|Gbps)',
        '소비전력': r'\bW\b', '전압': r'\bV\b', '부스트 클럭': r'(?:MHz|GHz)',
    }
    if key in units and not re.search(units[key],text,re.I):
        product.values[key] = Value('확인 필요', page, evidence+' [단위 확인 필요]', '검토 필요')
        return
    old = product.values.get(key, Value())
    if old.page is not None and old.text != text:
        product.values[key] = Value('확인 필요', page, old.evidence+'\n'+evidence, '검토 필요')
    else:
        product.values[key] = Value(text, page, evidence, '검토 필요')
