"""Publish only verified HanaFX assets; never replace another app or version."""
import hashlib,json,os,subprocess,tempfile,urllib.request
from pathlib import Path

VERSION='1.0.1'
TAG='hanafx-windows-v'+VERSION
REPO='shy4938-byte/-'
BRANCH='speccompare-download'
ZIP='HanaFX_Windows_v'+VERSION+'.zip'
SETUP='HanaFX_Setup_v'+VERSION+'.exe'
ROOT=Path(os.environ.get('GITHUB_WORKSPACE',Path.cwd()))
ARTIFACTS=ROOT/'release-artifacts'/'HanaFX'

def cmd(*args,check=True):return subprocess.run(args,check=check,capture_output=True,text=True)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify_url(url,expected):
    h=hashlib.sha256()
    with urllib.request.urlopen(url,timeout=180) as response:
        for block in iter(lambda:response.read(1024*1024),b''):h.update(block)
    if h.hexdigest()!=expected:raise RuntimeError('Published download checksum mismatch')

def main():
    os.chdir(ROOT);report=json.loads((ARTIFACTS/'build-report.json').read_text(encoding='utf-8'));live=json.loads((ARTIFACTS/'full-month-live-report.json').read_text(encoding='utf-8'));archive=ARTIFACTS/ZIP
    if not report.get('github_actions') or report['runtime'].get('status')!='passed' or report['runtime']['live'].get('status')!='passed' or live.get('status')!='passed':raise RuntimeError('Requires actual Windows and official-bank verification')
    if report['sha256']!=digest(archive):raise RuntimeError('Artifact integrity mismatch')
    if cmd('gh','release','view',TAG,'--repo',REPO,check=False).returncode==0:raise RuntimeError('Immutable release already exists; increment version')
    notes='HanaFX Windows x64. Official Hana Bank first-publication USD/KRW, native GUI, SQLite and Excel. Tests distinguish sample fixtures from real bank HTTP. See build-report.json and full-month-live-report.json. Routine startup and refresh query only today and reuse saved history. Collect missing history explicitly with the separate button; cancellation and cache are supported.'
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',delete=False) as f:f.write(notes);note_file=f.name
    cmd('gh','release','create',TAG,'--repo',REPO,'--target',report['source_sha'],'--title','HanaFX Windows v'+VERSION,'--draft','--notes-file',note_file)
    names=[ZIP,ZIP+'.sha256','build-report.json','full-month-live-report.json']
    if (ARTIFACTS/SETUP).exists():names.append(SETUP)
    cmd('gh','release','upload',TAG,*[str(ARTIFACTS/n) for n in names],'--repo',REPO)
    cmd('gh','release','edit',TAG,'--repo',REPO,'--draft=false')
    base=f'https://github.com/{REPO}/releases/download/{TAG}/'
    manifest={'version':VERSION,'url':base+ZIP,'setup_url':base+SETUP if SETUP in names else None,'sha256':digest(archive),'bytes':archive.stat().st_size,'source_sha':report['source_sha'],'actions_run':os.environ['BUILD_RUN_URL'],'official_live_status':live['status']}
    downloads=ROOT/'downloads';downloads.mkdir(exist_ok=True)
    files=['HanaFX_Windows_v'+VERSION+'.json','HanaFX_Windows_build-report.json','HanaFX_Windows_README.md']
    (downloads/files[0]).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (downloads/files[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    text=f'''# HanaFX Windows v{VERSION}\n\n[Windows ZIP 다운로드]({manifest['url']})\n\nZIP 전체 압축 해제 → HanaFX/HanaFX.exe 실행. Python·Node.js 설치 불필요. 기본 조회는 오늘만 갱신하고 기존 저장 자료를 재사용합니다. 과거 누락 자료 받기는 필요할 때 별도로 실행하세요.\n\n[사용 방법](../HanaFX/README.md) · [검증 보고서](../HanaFX/TEST_REPORT.md) · [Windows 빌드]({manifest['actions_run']})\n\nSHA-256: `{manifest['sha256']}`\n'''
    if manifest['setup_url']:text+=f"\n[설치형 EXE]({manifest['setup_url']})\n"
    (downloads/files[2]).write_text(text,encoding='utf-8')
    cmd('git','config','user.name','github-actions[bot]');cmd('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com');cmd('git','add','--',*[str(Path('downloads')/n) for n in files])
    if cmd('git','diff','--cached','--quiet',check=False).returncode:
        cmd('git','commit','-m','Publish verified HanaFX Windows v'+VERSION+' [skip ci]');cmd('git','push','origin','HEAD:'+BRANCH)
    verify_url(manifest['url'],manifest['sha256'])
    if manifest['setup_url']:verify_url(manifest['setup_url'],digest(ARTIFACTS/SETUP))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
