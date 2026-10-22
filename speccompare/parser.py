"""Offline layout/semantic extraction. Unknowns and conflicts stay reviewable.

Values originate in actual text/table cells. Shared capacity matrices are never
joined to multiple unrelated products of the same capacity.
"""
import re
from collections import defaultdict
from pathlib import Path
from .document import read_document, AnalysisError
from .schema import ALIASES, FIELDS, EXTRAS, Product, Value

MISSING='확인 필요'
PERFORMANCE=['순차읽기 속도','순차쓰기 속도','랜덤읽기 속도','랜덤쓰기 속도']

def clean(value):
    s=str(value or '').casefold().replace('\n',' ')
    s=re.sub(r'[\(\[]\s*(?:GB|TB|MB|MB/s|GB/s|IOPS|MT/s|MHz|GHz|W|ns|nCK)\s*[\)\]]','',s,flags=re.I)
    s=re.sub(r'\d+\s*\)|\(up to\)|\(min\)|\(max\)', '', s)
    return re.sub(r'[\s_:()/–−-]+',' ',s).strip(' .®™')

def alias_match(label,key):
    return clean(label) in {clean(key),*(clean(a) for a in ALIASES.get(key,[]))}

def matching(label,category):
    return [key for key in FIELDS[category]+EXTRAS[category] if alias_match(label,key)]

def normalize(value):
    value=re.sub(r'^(?:up to|maximum|max\.?|최대)\s*:?\s*','',str(value).strip(),flags=re.I)
    m=re.fullmatch(r'([\d,.]+)\s*GB/s',value,re.I)
    if m:
        return f'{float(m[1].replace(",", ""))*1000:g} MB/s'
    return value

def new_product(doc,category):
    return Product(doc.source,category,{k:Value() for k in FIELDS[category]+EXTRAS[category]},list(doc.warnings))

def assign(product,key,text,page,evidence,confidence=.95):
    text=normalize(text)
    if not text:
        return
    units={'용량':r'(?:[KMGT]B)\b','VRAM 용량':r'[MGT]B\b','동작속도':r'MT/s|MHz|GHz','순차읽기 속도':r'[MG]B/s','순차쓰기 속도':r'[MG]B/s','랜덤읽기 속도':r'IOPS','랜덤쓰기 속도':r'IOPS','메모리 대역폭':r'[MG]B/s|Gbps','소비전력':r'W\b'}
    if key in units and not re.search(units[key],text):
        product.warnings.append(f'{key}: 단위가 불명확하여 자동 입력을 보류했습니다(p.{page}).')
        return
    old=product.values.get(key,Value())
    if old.conflict:
        return
    if old.page and old.text!=text:
        if confidence<old.confidence:
            return
        if confidence>old.confidence:
            product.values[key]=Value(text,page,evidence,'검토 필요',confidence)
            return
        product.values[key]=Value(MISSING,page,old.evidence+'\n'+evidence,'검토 필요',confidence,True)
    else:
        product.values[key]=Value(text,page,evidence,'검토 필요',confidence)


def capacity(text):
    m=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(GB|TB|MB)\s*',str(text or ''))
    return ''.join(m.groups()) if m else None

def evidence(table,header,row):
    return f'[{table.method}] '+' | '.join(str(v or '') for v in header)+'\n'+' | '.join(str(v or '') for v in row)

def cell_value(header,value):
    text=str(value or '').strip()
    unit=re.search(r'[\(\[]\s*(GB|TB|MB|MB/s|GB/s|IOPS|MT/s|MHz|GHz|W|ns|nCK)\s*[\)\]]',str(header),re.I)
    if unit and re.fullmatch(r'[\d,.]+K?',text,re.I):
        return text+' '+unit[1]
    return text


def catalogue(doc,category):
    products={}
    # Geometric catalogues retain cover wildcard SKUs; ruled catalogues then add
    # concrete variants without turning the same capacity into duplicate models.
    tables=sorted(doc.tables,key=lambda t:(t.method!='unruled catalogue',t.page))
    for table in tables:
        for hi,header in enumerate(table.rows[:5]):
            mc=next((i for i,v in enumerate(header) if alias_match(v,'모델명')),None)
            cc=next((i for i,v in enumerate(header) if alias_match(v,'용량')),None)
            if mc is None or cc is None or mc==cc:
                continue
            rc=next((i for i,v in enumerate(header) if alias_match(v,'Rank') or clean(v)=='number of'),None)
            for row in table.rows[hi+1:]:
                if len(row)<=max(mc,cc) or not capacity(cell_value(header[cc],row[cc])) or not row[mc]:
                    continue
                cap=capacity(cell_value(header[cc],row[cc]))
                for model in str(row[mc]).splitlines():
                    model=re.sub(r'\s+','',model)
                    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.$/\-]*',model):
                        continue
                    # Only a literal wildcard SKU explicitly printed in this PDF
                    # may collect its concrete variants; no invented expansion.
                    parent=next((p for code,p in products.items() if '$' in code and re.fullmatch(re.escape(code).replace(r'\$','[A-Za-z]'),model) and p.values.get('용량',Value()).text==cap),None)
                    if parent:
                        k='품번 변형';old=parent.values.get(k,Value(''))
                        variants=set(old.text.splitlines()) if old.page else set()
                        variants.add(model);parent.values[k]=Value('\n'.join(sorted(variants)),table.page,evidence(table,header,row),'검토 필요',.99)
                        continue
                    p=products.setdefault(model,new_product(doc,category))
                    assign(p,'모델명',model,table.page,evidence(table,header,row),.99)
                    assign(p,'부품번호',model,table.page,evidence(table,header,row),.99)
                    assign(p,'VRAM 용량' if category=='VGA' else '용량',cap,table.page,evidence(table,header,row),.99)
                    for ci,label in enumerate(header):
                        if ci in [mc,cc,rc] or ci>=len(row) or not row[ci]:
                            continue
                        keys=['판매 코드'] if clean(label)=='model code' else matching(label,category)
                        for key in keys:
                            assign(p,key,cell_value(label,row[ci]),table.page,evidence(table,header,row),.99)
                    if rc is not None and rc<len(row) and re.fullmatch(r'[1-8]',str(row[rc] or '').strip()):
                        assign(p,'Rank',str(row[rc]).strip()+' Rank',table.page,evidence(table,header,row),.99)
    return list(products.values())


def header_products(doc,category):
    products={}
    for table in doc.tables:
        for hi,header in enumerate(table.rows[:4]):
            if not header or not alias_match(header[0],'모델명'):
                continue
            if any(alias_match(v,'용량') for v in header[1:] if v):
                continue
            recognized=[(row,matching(row[0],category)) for row in table.rows[hi+1:] if row and row[0]]
            if not any(keys for _,keys in recognized):
                continue
            for col,model in enumerate(header[1:],1):
                if not model or '\n' in str(model):
                    continue
                p=products.setdefault(str(model).strip(),new_product(doc,category))
                assign(p,'모델명',model,table.page,evidence(table,header,header),.99)
                for row,keys in recognized:
                    if len(row)>col and row[col]:
                        for key in keys:
                            assign(p,key,row[col],table.page,evidence(table,header,row),.99)
    return list(products.values())


def numbers(value):
    value=re.sub(r'(?<=\d)[1-9]\)', '', str(value or ''))
    return [v.strip() for v in value.split('/') if re.fullmatch(r'[\d,.]+\s*[Kk]?',v.strip())]

def magnitude(value):
    return float(re.sub(r'[Kk,\s]','',value))*(1000 if value.strip().upper().endswith('K') else 1)


def performance_tables(doc,products):
    for table in sorted(doc.tables,key=lambda t:t.method=='capacity coordinates'):
        for hi,header in enumerate(table.rows[:5]):
            cols={i:capacity(v) for i,v in enumerate(header) if capacity(v)}
            if not cols:
                continue
            uc=next((i for i,v in enumerate(header) if clean(v)=='unit'),None)
            qc=next((i for i,v in enumerate(header) if re.search('queue|depth|^qd$',clean(v))),None)
            groups=defaultdict(list);previous=[]
            for row in table.rows[hi+1:]:
                if not row:
                    continue
                label=str(row[0] or '')
                metric=re.search(r'(sequential|seq\.?|random|ran\.?)\s+(read|write)\s*$',label,re.I)
                normalized=(('Sequential' if metric[1].lower().startswith('seq') else 'Random')+' '+metric[2]) if metric else label
                keys=[k for k in PERFORMANCE+['내구성','TBW'] if alias_match(normalized,k)]
                if keys:
                    previous=keys
                elif row[0] in [None,'']:
                    keys=previous
                else:
                    previous=[]
                if not keys:
                    continue
                unit=re.sub(r'\d+\)','',str(row[uc] or '')).strip() if uc is not None and uc<len(row) else ''
                qd=None
                if qc is not None and qc<len(row):
                    q=re.search(r'\d+',str(row[qc] or ''));qd=int(q[0]) if q else None
                if not any(k.startswith('랜덤') for k in keys):qd=None
                tc=next((i for i,v in enumerate(header) if clean(v)=='thread'),None)
                thread=str(row[tc] or '') if tc is not None and tc<len(row) else ''
                for ci,cap in cols.items():
                    if ci>=len(row) or not row[ci]:
                        continue
                    parts=numbers(row[ci])
                    raw=str(row[ci]).strip()
                    if not parts:
                        m=re.fullmatch(r'([\d,.]+K?)\s*(MB/s|GB/s|IOPS|TB)',raw,re.I)
                        if not m:
                            continue
                        parts=[m[1]];unit=m[2]
                    if not unit:
                        continue
                    matches=[p for p in products if capacity(p.values.get('용량',Value()).text)==cap]
                    if len(matches)!=1:
                        for p in matches:
                            p.warnings.append(f'p.{table.page}: 동일 용량의 여러 모델에 성능을 배정하지 않았습니다.')
                        continue
                    for key in keys:
                        groups[(id(matches[0]),key)].append((matches[0],qd,parts,unit,evidence(table,header,row)+(f'\nThread {thread}' if thread else '')))
            for (_,key),records in groups.items():
                p,qd,parts,unit,proof=max(records,key=lambda r:r[1] or 0)
                assign(p,key,max(parts,key=magnitude)+' '+unit,table.page,proof,1.0 if table.method=='capacity coordinates' else .99)
                if qd:
                    assign(p,key+' · 측정 QD','QD'+str(qd),table.page,proof,.99)
                for _,rq,rp,ru,revidence in records:
                    assign(p,key+' · '+('QD'+str(rq) if rq else '원문'), ' / '.join(rp)+' '+ru,table.page,revidence,.99)
                if key.startswith('순차'):
                    p.values.setdefault(key+' · TurboWrite 미적용',Value())
                    page=doc.pages[table.page-1]
                    note=next((l.text for l in page.lines if re.search('Performance without TurboWrite',l.text,re.I)),None)
                    if len(parts)==2 and note:
                        assign(p,key+' · TurboWrite 미적용',parts[1]+' '+unit,table.page,proof+'\n'+note,.99)


def shared_features(doc,products,category):
    # Prefer explicit manufacturer fields; cover branding is only a fallback.
    brands={'samsung':'Samsung','essencore':'ESSENCORE','sk hynix':'SK hynix','adata':'ADATA','teamgroup':'TEAMGROUP','kingston':'Kingston','crucial':'Crucial','micron':'Micron','nvidia':'NVIDIA','amd':'AMD','asus':'ASUS','gigabyte':'GIGABYTE','msi':'MSI','western digital':'Western Digital','seagate':'Seagate'}
    cover=doc.pages[0]
    found=[(word,name) for word,name in brands.items() if re.search(r'\b'+re.escape(word)+r'\b',cover.text,re.I)]
    if len(found)==1:
        word,name=found[0];proof=next((l.text for l in cover.lines if re.search(re.escape(word),l.text,re.I)),word)
        for p in products:
            assign(p,'제조사',name,cover.number,proof,.8)
    for page in doc.pages:
        if not re.search(r'features|drive configuration|general specification|technical specification',page.text,re.I):
            continue
        patterns={
            '인터페이스':r'(?:PCI Express|PCIe)\s*[®™]*\s+Gen\.?\s*\d+(?:\.\d+)?\s*x\d+(?:,\s*NVMe\s*[\d.]+)?',
            'PCIe 세대':r'PCIe\s*[®™]*\s*Gen\.?\s*\d+(?:\.\d+)?',
            'NVMe':r'(?:NVM|NVMe) Express[^\n]*?Rev\.\s*[\d.]+[a-z]?|NVMe\s+\d+(?:\.\d+)+',
        }
        for key,pattern in patterns.items():
            if key not in FIELDS[category]+EXTRAS[category]:
                continue
            matches=list(re.finditer(pattern,page.text,re.I))
            if len({m[0] for m in matches})==1:
                for p in products:
                    assign(p,key,matches[0][0],page.number,matches[0][0],.9)
    # A family title never replaces the original part-number evidence.
    titles=list(re.finditer(r'\bSAMSUNG\s+SSD\s+(PM[A-Z0-9-]+)\b|\(\s*(PM[A-Z0-9-]+)\s*\)',cover.text,re.I))
    families={next(g for g in m.groups() if g).upper() for m in titles}
    if category=='SSD' and len(families)==1 and re.search('samsung',cover.text,re.I):
        family=next(iter(families))
        for p in products:
            part=p.values.get('부품번호')
            if not part or part.text not in cover.text:
                continue
            p.values['제품군 모델명']=Value(family,1,titles[0][0],'검토 필요',.99)
            cap=p.values['용량'].text
            p.values['모델명']=Value(f'Samsung {family} {cap}',1,titles[0][0]+f'\np.{part.page}: '+part.evidence,'검토 필요',.99)

    if category=='SSD':
        title=re.search(r'Samsung\s+(?:V-NAND\s+)?SSD\s+(\d{3,4}\s+(?:PRO|EVO(?:\s+Plus)?))\b',cover.text,re.I)
        if title:
            family=re.sub(r'\s+',' ',title[1]).upper()
            for p in products:
                part=p.values.get('부품번호')
                if part and part.page:
                    p.values['제품군 모델명']=Value(family,cover.number,title[0],'검토 필요',.99)
                    p.values['모델명']=Value(f'Samsung {family} {p.values["용량"].text}',cover.number,title[0]+f'\np.{part.page}: '+part.evidence,'검토 필요',.99)


def memory_features(doc,products):
    cover=doc.pages[0]
    factor='SO-DIMM' if re.search(r'SO[\s-]*DIMM',cover.text,re.I) else 'UDIMM' if re.search(r'UDIMM|Unbuffered\s+DIMM',cover.text,re.I) else None
    for p in products:
        cp=p.values['용량'].page
        relevant=[t for t in doc.tables if t.page==cp]
        text=doc.pages[cp-1].text
        if factor and re.search('DDR5',doc.text,re.I):
            assign(p,'메모리 규격','DDR5 '+factor,1,next((l.text for l in cover.lines if re.search('DIMM',l.text,re.I)),''),.95)
            assign(p,'폼팩터',factor,1,p.values['메모리 규격'].evidence,.95)
            assign(p,'DDR 세대','DDR5',cp,'DDR5 module ordering / speed table',.95)
        for page in doc.pages:
            if not re.search('features|description',page.text,re.I):
                continue
            for line in page.lines:
                if re.search(r'VDD[^\n]*?1\.1\s*V',line.text,re.I):
                    assign(p,'전압','1.1 V',page.number,line.text,.9)
                if re.search(r'On[\s-]*Die\s+ECC',line.text,re.I):
                    assign(p,'On-Die ECC','명시됨 (모듈 ECC와 별개)',page.number,line.text,.9)
        bins=[]
        for t in relevant:
            for hi,row in enumerate(t.rows):
                for ci,value in enumerate(row):
                    m=re.fullmatch(r'DDR5\s*[-–]\s*(\d{4})',str(value or '').strip())
                    if m:
                        bins.append((m[1],t,hi,ci))
        rates={b[0] for b in bins};rate=next(iter(rates)) if len(rates)==1 else None;mapping=''
        if len(rates)>1:
            for m in re.finditer(r'[“"\']([A-Z]{2,3})[”"\']\s*[–-]\s*(\d{4})\s*Mbps',text,re.I):
                if p.values['부품번호'].text.endswith(m[1]) and m[2] in rates:
                    rate=m[2];mapping=m[0]
        if not rate:
            p.warnings.append('속도 구간과 품번의 연결을 확정하지 못했습니다. 최대 구간을 임의 선택하지 않았습니다.')
            continue
        _,table,hi,ci=next(b for b in bins if b[0]==rate)
        proof=' | '.join(str(v or '') for v in table.rows[hi])+('\n'+mapping if mapping else '')
        assign(p,'동작속도',rate+' MT/s',table.page,proof,.99)
        if len(rates)==1:
            timing=next((str(v).strip() for v in table.rows[hi] if re.fullmatch(r'\d{2}-\d{2}-\d{2}',str(v or '').strip())),None)
            if timing:
                assign(p,'지연시간','CL'+timing.split('-')[0],table.page,proof,.99)
                assign(p,'타이밍(CL-tRCD-tRP)',timing,table.page,proof,.99)
        else:
            for row in table.rows[hi+1:]:
                if len(row)>ci and alias_match(row[0],'지연시간') and re.fullmatch(r'\d+',str(row[ci] or '')):
                    assign(p,'지연시간','CL'+str(row[ci]),table.page,proof+'\n'+' | '.join(str(v or '') for v in row),.99)
                if len(row)>ci and re.fullmatch(r'\d{2}-\d{2}-\d{2}',str(row[ci] or '').strip()):
                    assign(p,'타이밍(CL-tRCD-tRP)',str(row[ci]).strip(),table.page,proof+'\n'+str(row),.99)


def prose_candidates(doc,category):
    found=[]
    aliases=sorted([(a,k) for k in FIELDS[category]+EXTRAS[category] for a in [k]+ALIASES.get(k,[])],key=lambda v:-len(v[0]))
    for page in doc.pages:
        for line in page.lines:
            text=line.text.strip()
            for alias,key in aliases:
                pattern=r'^\s*'+re.escape(alias)+r'\s*(?::|：|\.{2,}|\s{1,})\s*(.+)$'
                m=re.match(pattern,text,re.I)
                if not m or not m[1].strip() or alias_match(m[1],key):
                    continue
                # Generic labels must be exact left-side labels, not sentences.
                value=m[1].strip()
                if len(value)>140 or re.match(r'^(is|are|was|means|of|for|and|in|to|the)\b',value,re.I):
                    continue
                if key=='소비전력':
                    kind=re.search(r'TDP|TGP|TBP|total graphics power|total board power',alias,re.I)
                    if kind:value+=' ('+(kind[0].upper() if len(kind[0])==3 else kind[0])+')'
                found.append((key,value,page.number,text,.75 if ':' not in text and '：' not in text else .9))
                break
    return found


def document_category(doc):
    """Require product-specific evidence; DDR/GDDR mentions alone are ambiguous."""
    front='\n'.join(p.text for p in doc.pages[:3])
    detected=set()
    if re.search(r'\bSSD\b|solid[ -]state\s+(?:drive|disk)',front,re.I):
        detected.add('SSD')
    if re.search(r'\bDDR\s*[345]\b',front,re.I) and re.search(r'SO[\s-]*DIMM|\b[UR]DIMM\b|Unbuffered\s+DIMM',front,re.I):
        detected.add('MEMORY')
    if re.search(r'graphics\s+(?:card|processing\s+unit)|\bGPU\b',front,re.I) and re.search(r'GDDR|VRAM|graphics\s+memory|CUDA|stream\s+processors',front,re.I):
        detected.add('VGA')
    return next(iter(detected)) if len(detected)==1 else None


def analyze(path,category,auto_detect=False):
    if category not in FIELDS:
        raise AnalysisError('MEMORY / SSD / VGA 제품군을 선택하세요.')
    doc=read_document(path)
    detected=document_category(doc)
    if detected and detected!=category:
        if auto_detect:
            category=detected
        else:
            raise AnalysisError(f'{detected} 데이터시트입니다. {detected} 탭에서 다시 분석하세요.')
    products=catalogue(doc,category) or header_products(doc,category)
    candidates=prose_candidates(doc,category)
    if not products:
        p=new_product(doc,category)
        models={v for k,v,*_ in candidates if k=='모델명'}
        if len(models)>1:
            p.warnings.append('여러 모델의 사양을 안전하게 분리하지 못했습니다. 모델별 문서로 분리하거나 수동 확인하세요.')
            return [p]
        for key,value,page,proof,score in candidates:
            assign(p,key,value,page,proof,score)
        products=[p]
    else:
        # Only globally unambiguous common textual values may enrich catalogues.
        bykey=defaultdict(list)
        for c in candidates:bykey[c[0]].append(c)
        common={'제조사','인터페이스','메모리 규격','PCIe 세대','NVMe','DRAM','NAND','전압','폼팩터'}
        for key,values in bykey.items():
            if key not in common or (key=='DRAM' and len(products)>1) or len({v[1] for v in values})!=1:
                continue
            for p in products:assign(p,key,*values[0][1:])
    if category=='SSD':
        performance_tables(doc,products)
        capacity_features(doc,products)
    shared_features(doc,products,category)
    if category=='MEMORY' and any(p.values['용량'].page for p in products):memory_features(doc,products)
    for p in products:
        p.warnings.append('자동 추출은 검토 필요 상태입니다. 페이지·단위·측정 조건을 확인하세요. 인식되지 않은 양식은 누락될 수 있습니다.')
    return products


def capacity_features(doc,products):
    """Only explicitly capacity-specific cells can supply per-model caches."""
    for table in doc.tables:
        if table.method!='capacity coordinates':continue
        header=table.rows[0]
        for row in table.rows[1:]:
            if not re.fullmatch(r'DRAM\s+Cache\s+Memory',str(row[0]),re.I):continue
            for ci,cap in enumerate(header[3:],3):
                matches=[p for p in products if capacity(p.values.get('용량',Value()).text)==capacity(cap)]
                if len(matches)==1 and re.fullmatch(r'\d+\s*[GM]B\s+LPDDR\d+[A-Za-z]*',row[ci],re.I):
                    assign(matches[0],'DRAM',row[ci],table.page,evidence(table,header,row),1.0)
