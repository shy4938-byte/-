from pathlib import Path
import os
import tempfile
from openpyxl import load_workbook
from .schema import FIELDS, ALIASES

SHEETS = {'MEMORY':['memory','메모리','ram'], 'SSD':['ssd'], 'VGA':['vga','그래픽카드','gpu']}
def inspect_template(path, category):
    wb = load_workbook(path)
    try:
        matches = [s for s in wb.sheetnames if s.strip().casefold() in SHEETS[category]]
        if len(matches) != 1:
            raise ValueError(f'{category} 시트를 고유하게 식별할 수 없습니다. 시트명: {wb.sheetnames}')
        ws, mapping = wb[matches[0]], {}
        for field in FIELDS[category]:
            labels = {field.casefold(), *[x.casefold() for x in ALIASES[field]]}
            rows = {cell.row for row in ws.iter_rows(min_col=1, max_col=2) for cell in row if isinstance(cell.value,str) and cell.value.strip().casefold() in labels}
            if len(rows) != 1:
                raise ValueError(f'항목 "{field}"의 입력 행을 고유하게 식별할 수 없습니다. A/B열의 원본 항목명을 확인하세요.')
            mapping[field] = rows.pop()
        for row in mapping.values():
            for col in range(3,7):
                cell = ws.cell(row,col)
                if cell.data_type == 'f' or any(cell.coordinate in merged for merged in ws.merged_cells.ranges):
                    raise ValueError(f'{cell.coordinate}: 수식 또는 병합 셀에 덮어쓸 수 없습니다.')
        return matches[0], mapping
    finally:
        wb.close()

def export(template, destination, category, products):
    if not 1 <= len(products) <= 4:
        raise ValueError('한 파일에 1~4개 제품을 저장하세요.')
    if Path(template).resolve() == Path(destination).resolve():
        raise ValueError('원본 템플릿을 덮어쓸 수 없습니다.')
    if any(p.category != category for p in products):
        raise ValueError('제품군이 다른 데이터입니다.')
    sheet, mapping = inspect_template(template, category)
    # Copy the original OOXML package; alter only input cells in the selected sheet.
    # This preserves other sheets and all formatting/print metadata byte-for-byte.
    import zipfile
    import xml.etree.ElementTree as ET
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    relns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    temporary = None
    try:
        with zipfile.ZipFile(template) as source:
            workbook = ET.fromstring(source.read('xl/workbook.xml'))
            rid = next(s.attrib['{'+relns+'}id'] for s in workbook.find('s:sheets',ns) if s.attrib['name']==sheet)
            relationships = ET.fromstring(source.read('xl/_rels/workbook.xml.rels'))
            target = next(r.attrib['Target'] for r in relationships if r.attrib['Id']==rid)
            filename = target.lstrip('/') if target.startswith('/') else 'xl/'+target
            root = ET.fromstring(source.read(filename))
            data = root.find('s:sheetData',ns)
            styles=ET.fromstring(source.read('xl/styles.xml'))
            xfs=styles.find('s:cellXfs',ns)
            centered={}; styles_changed=False
            def center_style(index):
                nonlocal styles_changed
                if index in centered: return centered[index]
                original=xfs[index]
                alignment=original.find('s:alignment',ns)
                if alignment is not None and alignment.get('horizontal')=='center' and alignment.get('vertical')=='center':
                    centered[index]=index; return index
                from copy import deepcopy
                clone=deepcopy(original)
                alignment=clone.find('s:alignment',ns)
                if alignment is None:
                    alignment=ET.Element('{'+ns['s']+'}alignment')
                    protection=clone.find('s:protection',ns)
                    clone.insert(list(clone).index(protection) if protection is not None else len(clone),alignment)
                alignment.set('horizontal','center');alignment.set('vertical','center')
                clone.set('applyAlignment','1'); new_index=len(xfs);xfs.append(clone)
                xfs.set('count',str(len(xfs)));centered[index]=new_index;styles_changed=True
                return new_index
            for field, row_number in mapping.items():
                row = next(r for r in data if int(r.attrib['r'])==row_number)
                for index in range(4):
                    coordinate = f'{chr(67+index)}{row_number}'
                    cell = next((c for c in row if c.attrib.get('r')==coordinate),None)
                    if cell is None:
                        cell = ET.SubElement(row,'{'+ns['s']+'}c',{'r':coordinate})
                    cell.set('s',str(center_style(int(cell.get('s','0')))))
                    for child in list(cell):
                        if child.tag in ['{'+ns['s']+'}v','{'+ns['s']+'}is']:
                            cell.remove(child)
                    cell.attrib.pop('t',None)
                    if index < len(products):
                        cell.set('t','inlineStr')
                        inline = ET.SubElement(cell,'{'+ns['s']+'}is')
                        text = ET.SubElement(inline,'{'+ns['s']+'}t')
                        text.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                        text.text = products[index].values[field].text
                row[:] = sorted(row,key=lambda c:(len(c.attrib.get('r','').rstrip('0123456789')),c.attrib.get('r','').rstrip('0123456789')))
            with tempfile.NamedTemporaryFile(dir=Path(destination).parent,suffix='.xlsx',delete=False) as f:
                temporary=f.name
            def serialize(node,original):
                # Keep Excel's namespace aliases, including mc:Ignorable prefixes.
                import io,re
                from xml.sax.saxutils import quoteattr
                namespaces=dict(value for _,value in ET.iterparse(io.BytesIO(original),events=('start-ns',)))
                for prefix,uri in namespaces.items():
                    if not re.fullmatch(r'ns\d+',prefix): ET.register_namespace(prefix,uri)
                payload=ET.tostring(node,encoding='utf-8',xml_declaration=True)
                offset=payload.find(b'?>')+2
                end=payload.find(b'>',offset)
                opening=payload[offset:end]
                extra=[]
                for prefix,uri in namespaces.items():
                    name='xmlns'+(':'+prefix if prefix else '')
                    if not re.search(rb'\s'+re.escape(name.encode())+rb'=',opening):
                        extra.append(' '+name+'='+quoteattr(uri))
                return payload[:end]+''.join(extra).encode()+payload[end:]
            with zipfile.ZipFile(temporary,'w') as output:
                for entry in source.infolist():
                    if entry.filename==filename:
                        payload=serialize(root,source.read(filename))
                    elif entry.filename=='xl/styles.xml' and styles_changed:
                        payload=serialize(styles,source.read('xl/styles.xml'))
                    else: payload=source.read(entry.filename)
                    output.writestr(entry,payload)
        os.replace(temporary,destination)
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)
