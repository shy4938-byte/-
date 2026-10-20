import * as pdfjs from 'pdfjs-dist/build/pdf.mjs';
import {unzipSync, zipSync, strFromU8, strToU8} from 'fflate';
const workerBytes=Uint8Array.from(atob(document.getElementById('pdf-worker').textContent.trim()),c=>c.charCodeAt(0));
const workerUrl=URL.createObjectURL(new Blob([workerBytes],{type:'text/javascript'}));
pdfjs.GlobalWorkerOptions.workerPort=new Worker(workerUrl);
pdfjs.GlobalWorkerOptions.workerPort.addEventListener('error',e=>{console.error('PDF worker error',e.message);document.getElementById('notice').textContent='PDF 엔진 시작 실패: '+(e.message||'브라우저 보안 정책을 확인하세요.');});
const FIELDS={MEMORY:['제조사','모델명','용량','메모리 규격','동작속도','지연시간','가격'],SSD:['제조사','모델명','용량','인터페이스','순차읽기 속도','순차쓰기 속도','랜덤읽기 속도','랜덤쓰기 속도','내구성','가격'],VGA:['제조사','모델명','VRAM 용량','VRAM 종류','메모리 대역폭','소비전력','가격']};
const EXTRAS={MEMORY:['DDR 세대','폼팩터','ECC','전압','Rank'],SSD:['PCIe 세대','NVMe','DRAM','NAND','TBW','MTBF'],VGA:['GPU 모델','GPU 아키텍처','코어','부스트 클럭','메모리 버스','보조전원','영상 출력']};
const ALIASES={'제조사':['manufacturer','vendor'],'모델명':['model','part number'],'용량':['capacity','density'],'메모리 규격':['memory type','module type','규격'],'동작속도':['data rate','memory speed'],'지연시간':['cas latency','latency'],'가격':['price'],'인터페이스':['interface'],'순차읽기 속도':['sequential read','순차읽기'],'순차쓰기 속도':['sequential write','순차쓰기'],'랜덤읽기 속도':['random read','랜덤읽기'],'랜덤쓰기 속도':['random write','랜덤쓰기'],'내구성':['endurance','tbw'],'VRAM 용량':['memory size','frame buffer','vram capacity'],'VRAM 종류':['memory type','vram type'],'메모리 대역폭':['memory bandwidth'],'소비전력':['total graphics power','total board power','tdp','tgp','tbp'],'DDR 세대':['ddr generation'],'폼팩터':['form factor'],'ECC':['ecc'],'전압':['voltage'],'Rank':['rank'],'PCIe 세대':['pcie generation'],'NVMe':['nvme version'],'DRAM':['dram'],'NAND':['nand'],'TBW':['tbw'],'MTBF':['mtbf'],'GPU 모델':['gpu model'],'GPU 아키텍처':['architecture'],'코어':['cuda cores','stream processors'],'부스트 클럭':['boost clock'],'메모리 버스':['memory bus'],'보조전원':['power connector'],'영상 출력':['display outputs','outputs']};
const $=id=>document.getElementById(id), normalize=s=>String(s||'').toLowerCase().replace(/\d+\)|\(up to\)/gi,'').replace(/[\s_:()/-]+/g,' ').trim();
const matches=(s,k)=>[k,...(ALIASES[k]||[])].some(v=>normalize(s)===normalize(v));
const capacity=s=>/^\d+(?:\.\d+)?\s*(GB|TB)$/i.test(s.trim());
const blank=()=>({text:'확인 필요',status:'미확인',page:null,evidence:''});
function product(source,category){return {source,category,values:Object.fromEntries([...FIELDS[category],...EXTRAS[category]].map(k=>[k,blank()])),warnings:[]};}
function assign(p,key,text,page,evidence){
 text=String(text).trim();if(!text)return;
 if(/^([\d,.]+)\s*GB\/s$/i.test(text))text=`${Number(text.match(/[\d,.]+/)[0].replaceAll(',',''))*1000} MB/s`;
 const units={'용량':/(GB|TB|MB|Gbit|Gb)\b/i,'VRAM 용량':/(GB|MB)\b/i,'동작속도':/MT\/s|MHz|GHz/i,'순차읽기 속도':/[MG]B\/s/i,'순차쓰기 속도':/[MG]B\/s/i,'랜덤읽기 속도':/IOPS/i,'랜덤쓰기 속도':/IOPS/i,'메모리 대역폭':/[MG]B\/s|Gbps/i,'소비전력':/W\b/i};
 if(units[key]&&!units[key].test(text)){p.values[key]={text:'확인 필요',status:'검토 필요',page,evidence:evidence+'\n단위 확인 필요'};return;}
 if(key==='소비전력'){const type=evidence.match(/TDP|TGP|TBP|total graphics power|total board power/i);if(type)text+=` (${type[0]})`;}
 const old=p.values[key];if(old?.conflict)return;
 if(old?.page&&old.text!==text){p.values[key]={text:'확인 필요',status:'검토 필요',page,evidence:old.evidence+'\n'+evidence,conflict:true};return;}
 p.values[key]={text,status:'검토 필요',page,evidence};
}
function rowsFromItems(items){
 const rows=[];
 for(const i of items.filter(i=>i.str?.trim()).sort((a,b)=>b.transform[5]-a.transform[5]||a.transform[4]-b.transform[4])){
  const y=i.transform[5];let r=rows.find(r=>Math.abs(r.y-y)<=3.3);
  if(!r){r={y,items:[]};rows.push(r);}r.items.push({text:i.str.trim(),x:i.transform[4],center:i.transform[4]+i.width/2});
 }
 for(const r of rows){r.items.sort((a,b)=>a.x-b.x);r.text=r.items.map(i=>i.text).join(' ');}
 return rows.sort((a,b)=>b.y-a.y);
}
function cellAt(row,centers,index){
 const left=index? (centers[index-1]+centers[index])/2:-Infinity,right=index+1<centers.length?(centers[index]+centers[index+1])/2:Infinity;
 return row.items.filter(i=>i.center>=left&&i.center<right).map(i=>i.text).join(' ').trim();
}
// Join adjacent PDF text fragments within a table cell (e.g. "16" + "GB").
function memoryClusters(row){
 const groups=[];
 for(const item of row.items){const end=item.center*2-item.x,last=groups.at(-1);if(last&&item.x-last.end<15){last.text+=item.text.replace(/\s+/g,'');last.end=Math.max(last.end,end);last.center=(last.x+last.end)/2;}else groups.push({text:item.text.replace(/\s+/g,''),x:item.x,end,center:item.center});}
 return groups;
}
function memoryProducts(pages,source){
 const products=new Map();
 for(const page of pages){
  const all=page.rows.flatMap(row=>row.items.map(i=>({...i,y:row.y})));
  for(const modelHeader of all.filter(i=>matches(i.text,'모델명'))){
   const density=all.find(i=>Math.abs(i.y-modelHeader.y)<10&&matches(i.text,'용량'));
   if(!density||density.center<=modelHeader.center)continue;
   const organization=all.find(i=>Math.abs(i.y-modelHeader.y)<10&&/^organization$/i.test(i.text));
   const rank=all.find(i=>Math.abs(i.y-modelHeader.y)<20&&/^ranks?$/i.test(i.text));
   const modelRight=(modelHeader.center+density.center)/2,capRight=organization?(density.center+organization.center)/2:density.center+35;
   for(const row of page.rows.filter(r=>r.y<modelHeader.y-5&&r.y>modelHeader.y-110)){
    const model=row.items.filter(i=>i.center<modelRight).map(i=>i.text).join('').replace(/\s+/g,''),cap=row.items.filter(i=>i.center>=modelRight&&i.center<capRight).map(i=>i.text).join('').replace(/\s+/g,'');
    if(!capacity(cap)||!/^[A-Z][A-Z0-9.$/-]*\d[A-Z0-9.$/-]*$/i.test(model))continue;
    const p=products.get(model)||product(source,'MEMORY');assign(p,'모델명',model,page.number,row.text);assign(p,'부품번호',model,page.number,row.text);assign(p,'용량',cap,page.number,row.text);
    if(rank){const value=row.items.find(i=>Math.abs(i.center-rank.center)<20&&/^[1-8]$/.test(i.text));if(value)assign(p,'Rank',value.text+' Rank',page.number,row.text);}
    p.orderingPage=page.number;products.set(model,p);
   }
  }
 }
 if(!products.size)return [];
 const front=pages.slice(0,6),cover=pages[0],manufacturer=front.find(p=>/Essencore/i.test(p.text))?'ESSENCORE':front.some(p=>/SAMSUNG/i.test(p.text))?'Samsung':null;
 const makerPage=manufacturer&&front.find(p=>(manufacturer==='ESSENCORE'?/Essencore/i:/SAMSUNG/i).test(p.text));
 const factor=/SO[\s-]*DIMM/i.test(cover.text)?'SO-DIMM':/UDIMM|Unbuffered\s+DIMM/i.test(cover.text)?'UDIMM':null;
 for(const p of products.values()){
  const ordering=pages.find(page=>page.number===p.orderingPage);
  if(manufacturer)assign(p,'제조사',manufacturer,makerPage.number,makerPage.rows.find(r=>(manufacturer==='ESSENCORE'?/Essencore/i:/SAMSUNG/i).test(r.text)).text);
  if(/DDR5/i.test(cover.text+'\n'+ordering.text)){
   assign(p,'DDR 세대','DDR5',cover.number,cover.rows.find(r=>/DDR5/i.test(r.text))?.text||ordering.rows.find(r=>/DDR5/i.test(r.text))?.text||'');
   if(factor){assign(p,'폼팩터',factor,cover.number,cover.rows.find(r=>/DIMM/i.test(r.text))?.text||'');assign(p,'메모리 규격','DDR5 '+factor,cover.number,cover.rows.find(r=>/DIMM/i.test(r.text))?.text||'');}
  }
  const voltagePage=front.find(page=>/VDD[^\n]*?1\.1\s*V/i.test(page.text));
  if(voltagePage){const row=voltagePage.rows.find(r=>/VDD[^\n]*?1\.1\s*V/i.test(r.text));assign(p,'전압','1.1 V',voltagePage.number,row.text);}
  const onDie=front.find(page=>/On[\s-]*Die\s+ECC/i.test(page.text));
  if(onDie){assign(p,'On-Die ECC','명시됨',onDie.number,onDie.rows.find(r=>/On[\s-]*Die\s+ECC/i.test(r.text)).text);p.warnings.push('On-Die ECC는 모듈 ECC 지원 여부와 다릅니다. 모듈 ECC는 별도 확인하세요.');}
  // Only use the speed-bin table on this module's ordering page.
  const binRows=ordering.rows.map(row=>({row,bins:memoryClusters(row).filter(c=>/^DDR5-\d{4}$/i.test(c.text))})).filter(v=>v.bins.length);
  const bins=binRows.flatMap(v=>v.bins.map(bin=>({...bin,row:v.row,rate:bin.text.match(/\d{4}$/)[0]})));
  const choices=[...new Set(bins.map(b=>b.rate))];let rate=choices.length===1?choices[0]:null,mappingEvidence='';
  if(choices.length>1){
   for(const row of ordering.rows){const m=row.text.match(/[“"']([A-Z]{2,3})[”"']\s*[–-]\s*(\d{4})\s*Mbps/i);if(m&&p.values['모델명'].text.endsWith(m[1])&&choices.includes(m[2])){rate=m[2];mappingEvidence=row.text;}}
  }
  if(!rate){p.warnings.push('여러 속도 구간 중 해당 품번의 조건을 확정하지 못했습니다. 속도와 지연시간을 원문에서 확인하세요.');continue;}
  const bin=bins.find(b=>b.rate===rate),evidence=bin.row.text+(mappingEvidence?'\n'+mappingEvidence:'');
  assign(p,'동작속도',rate+' MT/s',ordering.number,evidence);
  // A horizontal speed-bin matrix uses a CAS Latency row in nCK.
  if(choices.length>1){
   const cas=ordering.rows.find(r=>r.y<bin.row.y&&bin.row.y-r.y<100&&/CAS\s+Latency/i.test(r.text));
   if(cas){const cs=binRows.find(v=>v.bins.includes(bin))?.bins||bins.filter(b=>b.row===bin.row),centers=cs.map(b=>b.center),idx=cs.findIndex(b=>b.rate===rate);const val=cellAt({items:cas.items.filter(i=>i.center>centers[0]-35&&i.center<centers.at(-1)+35)},centers,idx).replace(/\s+/g,'');if(/^\d{2}$/.test(val))assign(p,'지연시간','CL'+val,ordering.number,evidence+'\n'+cas.text);}
   const timing=ordering.rows.filter(r=>r.y<bin.row.y&&bin.row.y-r.y<30).flatMap(r=>memoryClusters(r).map(c=>({...c,row:r}))).find(c=>Math.abs(c.center-bin.center)<35&&/^\d{2}-\d{2}-\d{2}$/.test(c.text));
   if(timing)assign(p,'타이밍(CL-tRCD-tRP)',timing.text,ordering.number,evidence+'\n'+timing.row.text);
  }else{
   const timings=memoryClusters(bin.row).filter(c=>/^\d{2}-\d{2}-\d{2}$/.test(c.text));
   if(timings.length===1&&/CL[\s-]*tRCD[\s-]*tRP/i.test(ordering.text)){
    assign(p,'지연시간','CL'+timings[0].text.split('-')[0],ordering.number,evidence);
    assign(p,'타이밍(CL-tRCD-tRP)',timings[0].text,ordering.number,evidence);
   }
  }
  delete p.orderingPage;
 }
 return [...products.values()];
}
function parsePages(pages,source,category){
 if(category==='MEMORY'){const modules=memoryProducts(pages,source);if(modules.length)return modules;}
 const keys=[...FIELDS[category],...EXTRAS[category]],products=new Map();
 // Explicit row catalogues: Part Number / Capacity, with columns located by PDF coordinates.
 for(const page of pages)for(let h=0;h<page.rows.length;h++){
  const header=page.rows[h];const mc=header.items.find(i=>matches(i.text,'모델명')),cc=header.items.find(i=>matches(i.text,'용량'));
  if(!mc||!cc)continue;
  const columns=header.items.filter(i=>!/^\d+\)$/.test(i.text)),centers=columns.map(i=>i.center),mi=columns.indexOf(mc),ci=columns.indexOf(cc);
  for(const row of page.rows.slice(h+1,h+12)){
   const cap=cellAt(row,centers,ci),model=cellAt(row,centers,mi);
   if(!capacity(cap)||!model||!/\d/.test(model))continue;
   const p=products.get(model)||product(source,category);assign(p,'모델명',model,page.number,header.text+'\n'+row.text);assign(p,'용량',cap,page.number,header.text+'\n'+row.text);products.set(model,p);
  }
 }
 if(products.size&&category==='SSD'){
  for(const page of pages)for(let h=0;h<page.rows.length;h++){
   const header=page.rows[h],caps=header.items.filter(i=>capacity(i.text));
   if(caps.length<2||!header.items.some(i=>/^parameter$/i.test(i.text)))continue;
   const centers=caps.map(i=>i.center),left=centers[0]-(centers[1]-centers[0])/2;
   const body=[];
   for(const row of page.rows.slice(h+1)){
    if(/NOTE\s*:|\[Table /i.test(row.text)||header.y-row.y>240)break;
    body.push(row);
   }
   const markers=[];
   for(const row of body){
    const label=row.items.filter(i=>i.center<left).map(i=>i.text).join(' ');
    const matched=keys.filter(k=>[k,...(ALIASES[k]||[])].some(a=>normalize(label).startsWith(normalize(a)+' ')||normalize(label)===normalize(a)));
    if(matched.length)markers.push({row,keys:matched});
   }
   const unitHeader=header.items.find(i=>/^unit$/i.test(i.text));
   const numeric=text=>text.replace(/(?:^|\s)\d+\)/g,'').replace(/\s*\/\s*/g,' / ').trim();
   for(let mi=0;mi<markers.length;mi++){
    const marker=markers[mi],top=marker.row.y+7,bottom=markers[mi+1]?markers[mi+1].row.y+7:-Infinity;
    const band=body.filter(r=>r.y<=top&&r.y>bottom),records=[];
    for(const row of band){
     const values=caps.map((_,c)=>numeric(cellAt({items:row.items.filter(i=>i.center>=left)},centers,c)));
     if(!values.every(v=>/^\d[\d,.]*K?(?:\s*\/\s*\d[\d,.]*K?)?$/i.test(v)))continue;
     let unit=row.items.find(i=>i.center<left&&/^(?:MB\/s|GB\/s|IOPS|TB)(?:\d+\))?$/i.test(i.text));
     if(!unit)unit=band.flatMap(r=>r.items.map(i=>({...i,y:r.y}))).find(i=>i.center<left&&Math.abs(i.y-row.y)<6&&/^(?:MB\/s|GB\/s|IOPS|TB)$/i.test(i.text));
     if(!unit)continue;
     const qdItem=row.items.find(i=>i.center<left&&(!unitHeader||i.center>unitHeader.center+15)&&/^\d+$|^QD\s*=\s*\d+$/i.test(i.text));
     const qd=qdItem?Number(qdItem.text.match(/\d+/)[0]):null;
     records.push({values,unit:unit.text.replace(/\d+\)$/,''),qd,row});
    }
    if(!records.length)continue;
    const main=[...records].sort((a,b)=>(b.qd||0)-(a.qd||0))[0];
    for(let c=0;c<caps.length;c++)for(const p of products.values()){
     if(normalize(p.values['용량'].text)!==normalize(caps[c].text))continue;
     for(const key of marker.keys){
      const conditioned=records.length>1||main.values[c].includes('/');
      const pieces=main.values[c].split('/').map(v=>v.trim());
      const magnitude=v=>Number(v.replaceAll(',','').replace(/K$/i,''))*(/K$/i.test(v)?1000:1);
      const maximum=/속도$/.test(key)?[...pieces].sort((a,b)=>magnitude(b)-magnitude(a))[0]:main.values[c];
      const text=`${maximum} ${main.unit}`;
      if(/순차/.test(key))p.values[`${key} · TurboWrite 미적용`]??=blank();
      const evidence=header.text+'\n'+marker.row.text+'\n'+band.map(r=>r.text).join('\n');
      assign(p,key,text,page.number,evidence);
      if(main.qd)assign(p,`${key} · 측정 QD`,'QD'+main.qd,page.number,evidence);
      if(conditioned){
       for(const record of records)assign(p,`${key} · ${record.qd?'QD'+record.qd:'측정값'}`,`${record.values[c]} ${record.unit}`,page.number,evidence);
       if(main.values[c].includes('/')){
        const seq=/순차/.test(key)&&/Performance without TurboWrite technology/i.test(page.text);
        if(seq&&pieces.length===2)assign(p,`${key} · TurboWrite 미적용`,`${pieces[1]} ${main.unit}`,page.number,evidence+'\n'+page.rows.filter(r=>/Performance without TurboWrite technology/i.test(r.text)).map(r=>r.text).join('\n'));
        assign(p,`${key} · 병기값 설명`,seq?'두 번째 값: TurboWrite 미적용 (주석 5)':'슬래시 양쪽 값을 원문 그대로 보존. 추가 측정 조건은 원문 검토 필요',page.number,evidence+'\n'+page.rows.filter(r=>/Performance without TurboWrite technology/i.test(r.text)).map(r=>r.text).join('\n'));
       }
      }
     }
    }
   }
  }

  for(const p of products.values())for(const page of pages){
   if(!/Drive Configuration/.test(page.text)||!/Features/.test(page.text))continue;
   if(/SAMSUNG/i.test(pages[0].text))assign(p,'제조사','Samsung',1,pages[0].rows.find(r=>/SAMSUNG/i.test(r.text))?.text||'');
   for(const [key,re] of Object.entries({'인터페이스':/PCI Express\s*[®™]*\s+Gen\.?\s*\d+\s+x\d+/i,'PCIe 세대':/PCIe\s*[®™]*\s+Gen\.?\s*\d+/i,'NVMe':/(?:NVM|NVMe) Express[^\n]*?Rev\.\s*[\d.]+[a-z]?/i})){
    const m=page.text.match(re);if(m)assign(p,key,m[0],page.number,m[0]);
   }
  }
  // A cover title identifies the shared product family; catalogue codes remain part numbers.
  const cover=pages[0],titles=[...cover.text.matchAll(/\bSAMSUNG\s+SSD\s+([A-Z][A-Z0-9-]*)\b/gi)];
  if(/SAMSUNG/i.test(cover.text))for(const row of cover.rows){const m=row.text.match(/^\(\s*(PM[A-Z0-9-]+)\s*\)$/i);if(m)titles.push(m);}
  const families=new Set(titles.map(m=>m[1].toUpperCase()));
  if(families.size===1&&[...products.values()].every(p=>cover.text.includes(p.values['모델명'].text))){
   const title=titles[0],family=title[1].toUpperCase();
   for(const p of products.values()){
    const part={...p.values['모델명']},cap=p.values['용량'];
    p.values['부품번호']=part;
    p.values['제품군 모델명']={text:family,status:'검토 필요',page:cover.number,evidence:title[0]};
    p.values['모델명']={text:`Samsung ${family}${cap.text!=='확인 필요'?' '+cap.text:''}`,status:'검토 필요',page:cover.number,evidence:`p.${cover.number}: ${title[0]}\np.${part.page}: ${part.evidence}\n제품군명과 해당 부품번호의 용량을 함께 표시`};
   }
  }
  return [...products.values()];
 }
 // Explicit horizontal model headers. Never use Capacity / LBA Count as model names.
 if(!products.size)for(const page of pages)for(let h=0;h<page.rows.length;h++){
  const header=page.rows[h],modelLabel=header.items.findIndex(i=>matches(i.text,'모델명'));
  if(modelLabel!==0||header.items.some(i=>matches(i.text,'용량')))continue;
  const models=header.items.slice(1).filter(i=>/\d/.test(i.text));if(!models.length)continue;
  const centers=[header.items[0].center,...models.map(i=>i.center)];
  for(let c=0;c<models.length;c++){
   const p=products.get(models[c].text)||product(source,category);assign(p,'모델명',models[c].text,page.number,header.text);
   for(const row of page.rows.slice(h+1,h+24)){
    const key=keys.find(k=>matches(cellAt(row,centers,0),k));if(key&&key!=='모델명')assign(p,key,cellAt(row,centers,c+1),page.number,header.text+'\n'+row.text);
   }products.set(models[c].text,p);
  }
 }
 if(products.size)return [...products.values()];
 const p=product(source,category),candidates=[];
 for(const page of pages)for(const row of page.rows){
  const m=row.text.match(/^\s*(.+?)\s*[:：]\s*(.+?)\s*$/);if(!m)continue;
  const key=keys.find(k=>matches(m[1],k));if(key)candidates.push({key,text:m[2],page:page.number,evidence:row.text});
 }
 if(new Set(candidates.filter(c=>c.key==='모델명').map(c=>c.text)).size>1){p.warnings.push('복수 모델의 표 구조를 식별하지 못했습니다. 모델별 PDF로 분리하거나 수동 입력하세요.');return [p];}
 for(const c of candidates)assign(p,c.key,c.text,c.page,c.evidence);
 p.warnings.push('규칙으로 인식한 항목만 표시합니다. 누락 항목은 원문 확인 후 입력하세요.');return [p];
}
async function analyze(file,category,progress=()=>{}){
 const task=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer()),isEvalSupported:false,useWorkerFetch:false});
 let doc;
 try{
  doc=await task.promise;const pages=[];
  for(let n=1;n<=doc.numPages;n++){const page=await doc.getPage(n),content=await page.getTextContent();const rows=rowsFromItems(content.items);pages.push({number:n,rows,text:rows.map(r=>r.text).join('\n')});page.cleanup();progress(n/doc.numPages);}
  if(!pages.some(p=>p.text.trim()))throw Error('텍스트 없는 스캔 PDF입니다. 외부 OCR 처리 후 다시 추가하세요.');
  const titleText=pages.slice(0,2).map(p=>p.text).join('\n');
  const moduleText=pages.slice(0,6).map(p=>p.text).join('\n');
  const memoryDocument=/DDR\s*[345]/i.test(moduleText)&&/SO[\s-]*DIMM|UDIMM|Unbuffered\s+DIMM/i.test(titleText);
  if(memoryDocument&&category!=='MEMORY')throw Error('메모리 데이터시트입니다. MEMORY 탭을 선택한 뒤 다시 분석하세요.');
  return parsePages(pages,file.name,category);
 }catch(e){if(e.name==='PasswordException')throw Error('암호화 PDF입니다. 암호를 해제한 파일을 사용하세요.');throw e;}finally{await task.destroy();}
}
const XMLNS='http://schemas.openxmlformats.org/spreadsheetml/2006/main';
function xml(bytes){const d=new DOMParser().parseFromString(strFromU8(bytes),'application/xml');if(d.getElementsByTagName('parsererror').length)throw Error('Excel XML 해석 실패');return d;}
function descendants(d,name){return [...d.getElementsByTagNameNS(XMLNS,name)];}
function excelBytes(category,products){
 if(!products.length||products.length>4)throw Error('현재 그룹에 1~4개 제품이 필요합니다.');
 const template=Uint8Array.from(atob(document.getElementById('excel-template').textContent.trim()),c=>c.charCodeAt(0)),entries=unzipSync(template),workbook=xml(entries['xl/workbook.xml']),rels=xml(entries['xl/_rels/workbook.xml.rels']);
 const title={MEMORY:'메모리',SSD:'SSD',VGA:'VGA'}[category],sheet=descendants(workbook,'sheet').find(s=>s.getAttribute('name')===title);if(!sheet)throw Error('제품군 시트가 없습니다.');
 const rid=sheet.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id'),target=[...rels.documentElement.children].find(r=>r.getAttribute('Id')===rid).getAttribute('Target');
 const path=target.startsWith('/')?target.slice(1):'xl/'+target,doc=xml(entries[path]);
 // Append centered variants so shared styles on other sheets remain unchanged.
 const styles=xml(entries['xl/styles.xml']),xfs=descendants(styles,'cellXfs')[0],styleMap=new Map();let stylesChanged=false;
 function centeredStyle(index){
  if(styleMap.has(index))return styleMap.get(index);
  const original=xfs.children[index];if(!original)throw Error('Excel 셀 스타일을 찾을 수 없습니다.');
  const old=descendants(original,'alignment')[0];
  if(old?.getAttribute('horizontal')==='center'&&old?.getAttribute('vertical')==='center'){styleMap.set(index,index);return index;}
  const copy=original.cloneNode(true);let alignment=descendants(copy,'alignment')[0];
  if(!alignment){alignment=styles.createElementNS(XMLNS,'alignment');const protection=[...copy.children].find(c=>c.localName==='protection');copy.insertBefore(alignment,protection||null);}
  alignment.setAttribute('horizontal','center');alignment.setAttribute('vertical','center');copy.setAttribute('applyAlignment','1');
  const result=xfs.children.length;xfs.append(copy);xfs.setAttribute('count',String(xfs.children.length));styleMap.set(index,result);stylesChanged=true;return result;
 }
 const strings=entries['xl/sharedStrings.xml']?descendants(xml(entries['xl/sharedStrings.xml']),'si').map(s=>descendants(s,'t').map(t=>t.textContent).join('')):[];
 function value(c){return c.getAttribute('t')==='s'?strings[Number(descendants(c,'v')[0]?.textContent)]:c.getAttribute('t')==='inlineStr'?descendants(c,'t').map(t=>t.textContent).join(''):descendants(c,'v')[0]?.textContent||'';}
 for(const field of FIELDS[category]){
  const labels=descendants(doc,'c').filter(c=>/^[AB]\d+$/.test(c.getAttribute('r'))&&matches(value(c),field));if(labels.length!==1)throw Error(`항목 매핑을 확정할 수 없습니다: ${field}`);
  const rowNumber=labels[0].getAttribute('r').match(/\d+/)[0],row=descendants(doc,'row').find(r=>r.getAttribute('r')===rowNumber);
  for(let index=0;index<4;index++){
   const ref=String.fromCharCode(67+index)+rowNumber;let c=[...row.children].find(c=>c.getAttribute('r')===ref);
   if(!c){c=doc.createElementNS(XMLNS,'c');c.setAttribute('r',ref);row.appendChild(c);}
   c.setAttribute('s',String(centeredStyle(Number(c.getAttribute('s')||0))));
   if(descendants(c,'f').length)throw Error(`${ref}의 수식을 덮어쓸 수 없습니다.`);
   for(const merged of descendants(doc,'mergeCell')){const ends=merged.getAttribute('ref').split(':');const col=x=>x.match(/[A-Z]+/)[0].split('').reduce((a,v)=>a*26+v.charCodeAt(0)-64,0);if(ends.length===2&&col(ends[0])<=index+3&&col(ends[1])>=index+3&&Number(ends[0].match(/\d+/)[0])<=Number(rowNumber)&&Number(ends[1].match(/\d+/)[0])>=Number(rowNumber))throw Error(`${ref}는 병합 셀입니다.`);}
   for(const child of [...c.children])if(['v','is'].includes(child.localName))c.removeChild(child);
   c.removeAttribute('t');if(index<products.length){c.setAttribute('t','inlineStr');const is=doc.createElementNS(XMLNS,'is'),t=doc.createElementNS(XMLNS,'t');t.setAttributeNS('http://www.w3.org/XML/1998/namespace','xml:space','preserve');t.textContent=products[index].values[field].text;is.appendChild(t);c.appendChild(is);}
  }
 }
 entries[path]=strToU8(new XMLSerializer().serializeToString(doc));if(stylesChanged)entries['xl/styles.xml']=strToU8(new XMLSerializer().serializeToString(styles));return zipSync(entries,{level:6});
}
function download(bytes,name,type){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([bytes],{type}));a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
let category='SSD',files=[],products=[],group=0,busy=false,selected=null,lastExcel=null;
const visible=()=>products.slice(group*4,group*4+4);
function note(message,error=false){$('notice').textContent=message;$('notice').className=error?'notice error':'notice';}
function renderFiles(){const list=$('files');list.replaceChildren();for(const [index,file] of files.entries()){const row=document.createElement('div');row.className='file';const label=document.createElement('span');label.textContent=file.name+` · ${(file.size/1024/1024).toFixed(1)} MB`;const button=document.createElement('button');button.textContent='삭제';button.disabled=busy;button.onclick=()=>{files.splice(index,1);renderFiles();};row.append(label,button);list.append(row);}$('file-count').textContent=`${files.length}개 PDF`;}
function addFiles(incoming){if(busy)return;for(const f of incoming){if(!/\.pdf$/i.test(f.name)){note('PDF 파일만 추가하세요.',true);continue;}if(!files.some(x=>x.name===f.name&&x.size===f.size&&x.lastModified===f.lastModified))files.push(f);}renderFiles();}
function showEvidence(p,key){selected={p,key};const v=p.values[key];$('evidence').textContent=`${p.source}\n${key}: ${v.text}\n상태: ${v.status} · 페이지: ${v.page||'없음'}\n\n원문 근거\n${v.evidence||'없음 — 수동 확인 필요'}\n\n${p.warnings.join('\n')}`;}
function render(){
 const groups=$('groups');groups.replaceChildren();for(let n=0;n<Math.max(1,Math.ceil(products.length/4));n++){const b=document.createElement('button');b.textContent=`비교 그룹 ${n+1}`;b.className=n===group?'active':'';b.onclick=()=>{group=n;render();};groups.append(b);}
 $('product-count').textContent=`${products.length}개 제품`;$('category-title').textContent=category;
 const table=$('comparison');table.replaceChildren();const thead=document.createElement('thead'),head=document.createElement('tr');
 const first=document.createElement('th');first.textContent='스펙 항목';head.append(first);
 for(let i=0;i<4;i++){const th=document.createElement('th'),p=visible()[i],label=document.createElement('div');label.textContent=p?(p.values['모델명'].text==='확인 필요'?`제품 ${String.fromCharCode(65+i)}`:p.values['모델명'].text):`제품 ${String.fromCharCode(65+i)}`;th.append(label);if(p){const tools=document.createElement('div');tools.className='header-tools';for(const [name,callback] of [['←',()=>move(p,-1)],['→',()=>move(p,1)],['상세',()=>{$('evidence').textContent=Object.entries(p.values).map(([k,v])=>`${k}: ${v.text} [${v.status}] p.${v.page||'-'}\n${v.evidence}`).join('\n\n');}]]){const b=document.createElement('button');b.textContent=name;b.onclick=callback;tools.append(b);}th.append(tools);}head.append(th);}thead.append(head);table.append(thead);
 const tbody=document.createElement('tbody');for(const key of FIELDS[category]){const row=document.createElement('tr'),label=document.createElement('th');label.textContent=key;row.append(label);const differing=new Set(visible().map(p=>p.values[key].text).filter(t=>t!=='확인 필요')).size>1;
  for(let i=0;i<4;i++){const td=document.createElement('td'),p=visible()[i];if(p){const v=p.values[key],input=document.createElement('input'),badge=document.createElement('span');input.value=v.text;input.setAttribute('aria-label',`${key} 제품 ${i+1}`);input.onfocus=()=>showEvidence(p,key);input.oninput=()=>{v.text=input.value;v.status='검토 필요';badge.textContent='검토 필요 · 수정됨';showEvidence(p,key);};badge.className='badge';badge.textContent=v.status;td.className=v.text==='확인 필요'?'missing':differing?'different':v.status==='확인 완료'?'confirmed':'';td.append(input,badge);}else td.textContent='—';row.append(td);}tbody.append(row);}table.append(tbody);
}
function move(p,delta){const i=products.indexOf(p),j=i+delta;if(j<0||j>=products.length)return;[products[i],products[j]]=[products[j],products[i]];render();}
function setBusy(value){busy=value;for(const b of document.querySelectorAll('[data-lock]'))b.disabled=value;renderFiles();}
async function chooseModels(candidates){if(candidates.length<2)return candidates;const dialog=$('model-dialog'),list=$('model-list');list.replaceChildren();for(const p of candidates){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=true;input.dataset.index=candidates.indexOf(p);label.append(input,document.createTextNode(`${p.values['모델명'].text} · ${p.values['용량']?.text||p.values['VRAM 용량']?.text||''}`));list.append(label);}dialog.showModal();return new Promise(resolve=>{dialog.onclose=()=>resolve(dialog.returnValue==='ok'?[...list.querySelectorAll('input:checked')].map(i=>candidates[Number(i.dataset.index)]):[]);});}
$('pdf-input').onchange=e=>{addFiles(e.target.files);e.target.value='';};$('add').onclick=()=>$('pdf-input').click();$('clear-files').onclick=()=>{files=[];renderFiles();};
$('drop').ondragover=e=>{e.preventDefault();$('drop').classList.add('drag');};$('drop').ondragleave=()=>$('drop').classList.remove('drag');$('drop').ondrop=e=>{e.preventDefault();$('drop').classList.remove('drag');addFiles(e.dataTransfer.files);};
for(const button of document.querySelectorAll('[data-category]'))button.onclick=()=>{if(busy)return;if(products.length&&!confirm('제품군을 변경하면 현재 분석 결과가 초기화됩니다. 계속할까요?'))return;category=button.dataset.category;products=[];group=0;selected=null;for(const b of document.querySelectorAll('[data-category]'))b.classList.toggle('active',b===button);$('evidence').textContent='값을 클릭하면 PDF 페이지와 추출 근거를 확인할 수 있습니다.';render();};
$('analyze').onclick=async()=>{if(!files.length)return note('PDF를 먼저 추가하세요.',true);setBusy(true);const all=[],errors=[];try{for(let i=0;i<files.length;i++){note(`${files[i].name} 분석 중…`);try{const results=await analyze(files[i],category,ratio=>{$('progress').value=(i+ratio)/files.length*100;});const usable=results.filter(p=>FIELDS[category].some(k=>p.values[k].text!=='확인 필요'));if(!usable.length)throw Error('제품 사양을 식별하지 못했습니다. 빈 제품을 비교표에 추가하지 않았습니다.');all.push(...await chooseModels(usable));}catch(e){errors.push(`${files[i].name}: ${e.message}`);}}products=all;group=0;selected=null;render();note(`${all.length}개 제품 분석 완료. 자동 추출값은 원문 검토가 필요합니다.${errors.length?'\n'+errors.join('\n'):''}`,!!errors.length);}finally{setBusy(false);}};
$('reset').onclick=()=>{if(products.length&&!confirm('분석 결과와 수동 수정값을 초기화할까요?'))return;products=[];group=0;selected=null;$('progress').value=0;render();};
$('confirm').onclick=()=>{if(!selected)return note('확인할 셀을 먼저 클릭하세요.');const v=selected.p.values[selected.key];if(!v.text.trim()||v.text==='확인 필요')return note('값을 입력한 뒤 확인하세요.');v.status='확인 완료';showEvidence(selected.p,selected.key);render();};
$('save').onclick=()=>{try{lastExcel={bytes:excelBytes(category,visible()),name:`${category}_SpecCompare_${new Date().toLocaleDateString('sv-SE').replaceAll('-','')}.xlsx`};download(lastExcel.bytes,lastExcel.name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');note('현재 그룹의 Excel 파일을 저장했습니다. 브라우저 다운로드 목록에서 열어주세요.');}catch(e){note(e.message,true);}};
$('save-again').onclick=()=>{if(lastExcel)download(lastExcel.bytes,lastExcel.name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');else note('엑셀을 먼저 저장하세요.');};
window.SpecCompare={analyze,parsePages,excelBytes,FIELDS,loadProducts(p,c='SSD'){category=c;products=p;group=0;render();},getProducts:()=>products,version:'1.1.5-browser'};
render();renderFiles();note('준비 완료 · 인터넷 연결 없이 PDF 분석과 Excel 저장을 사용할 수 있습니다.');
