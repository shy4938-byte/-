"""Publish verified artifacts only; preserve unrelated files and immutable versions."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request

REPO='shy4938-byte/-'
BRANCH='speccompare-download'
TAG='speccompare-windows-v1.2.0'
ZIP='SpecCompare_Windows_v1.2.0.zip'
SETUP='SpecCompare_Setup_v1.2.0.exe'
MAX_GIT=50*1024*1024
ROOT=Path(__file__).resolve().parents[1]

def command(*args,check=True):
    return subprocess.run(list(args),check=check,capture_output=True,text=True)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def download_verified(url,expected):
    digest=hashlib.sha256()
    with urllib.request.urlopen(url,timeout=180) as response:
        for chunk in iter(lambda:response.read(1024*1024),b''):digest.update(chunk)
    if digest.hexdigest()!=expected:raise RuntimeError('Published download checksum mismatch: '+url)


def main():
    os.chdir(ROOT);artifacts=ROOT/'release-artifacts'
    report=json.loads((artifacts/'build-report.json').read_text(encoding='utf-8'))
    archive=artifacts/ZIP
    if not report.get('github_actions') or report['runtime'].get('status')!='passed':raise RuntimeError('Requires verified GitHub Actions Windows build')
    if not archive.exists() or sha(archive)!=report['sha256']:raise RuntimeError('Artifact integrity mismatch')
    release_url=f'https://github.com/{REPO}/releases/download/{TAG}/'
    raw_url=f'https://github.com/{REPO}/raw/refs/heads/{BRANCH}/downloads/'
    use_release=archive.stat().st_size>MAX_GIT
    downloads=ROOT/'downloads';downloads.mkdir(exist_ok=True)
    filenames=[ZIP,ZIP+'.sha256','build-report.json']
    if (artifacts/SETUP).exists():filenames.append(SETUP)
    # All release upload operations occur after tests and frozen-runtime checks.
    if use_release or (artifacts/SETUP).exists():
        existing=command('gh','release','view',TAG,'--repo',REPO,'--json','isDraft',check=False)
        if existing.returncode==0:raise RuntimeError('Release version already exists. Increment version instead of replacing existing assets.')
        notes='Windows x64 onedir build. See build-report.json for runtime verification. Original manufacturer PDFs are not included. Automated fixtures are synthetic; real-PDF tests are documented separately. Free AI mode requires a local Ollama vision model. Paid online APIs and cloud-backed models are blocked. Live LLM extraction accuracy is UNVERIFIED; the packaged AI test uses a deterministic fixture server.'
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',delete=False) as f:
            f.write(notes);notes_path=f.name
        command('gh','release','create',TAG,'--repo',REPO,'--target',os.environ['SOURCE_SHA'],'--title','SpecCompare Windows v1.2.0','--draft','--notes-file',notes_path)
        command('gh','release','upload',TAG,*[str(artifacts/name) for name in filenames],'--repo',REPO)
        command('gh','release','edit',TAG,'--repo',REPO,'--draft=false')
    if not use_release:
        target=downloads/ZIP
        if target.exists() and sha(target)!=sha(archive):raise RuntimeError('Existing ZIP differs; refusing to overwrite it')
        target.write_bytes(archive.read_bytes());(downloads/(ZIP+'.sha256')).write_bytes((artifacts/(ZIP+'.sha256')).read_bytes())
    url=(release_url if use_release else raw_url)+ZIP
    setup_url=release_url+SETUP if (artifacts/SETUP).exists() else None
    manifest={'version':'1.2.0','url':url,'sha256':sha(archive),'bytes':archive.stat().st_size,'location':'GitHub Releases' if use_release else 'downloads/','setup_url':setup_url,'actions_run':os.environ['BUILD_RUN_URL'],'source_sha':os.environ['SOURCE_SHA'],'ai_setup_required':True,'ai_live_accuracy':'UNVERIFIED; configure a model and review source evidence'}
    text=f'''# SpecCompare Windows v1.2.0\n\n[Windows ZIP 다운로드]({url})\n\nZIP 전체 압축 해제 → SpecCompare/SpecCompare.exe 실행. Python 설치 불필요. 무료 AI 모드는 최초 로컬 Ollama 설치와 비전 모델 다운로드가 필요합니다. API 키·API 이용 요금은 없습니다. 실제 LLM 정확도는 미검증이며 결과 검토가 필요합니다.\n\n빌드: {manifest['actions_run']}\n\nSHA-256: `{manifest['sha256']}`\n\nZIP이 50 MiB를 초과하면 GitHub 권장 제한을 존중하여 Releases에 게시합니다.\n기존 브라우저 앱과 다른 파일은 유지합니다.\n'''
    if setup_url:text+=f'\n[선택 설치 프로그램]({setup_url})\n'
    (downloads/'SpecCompare_Windows_README.md').write_text(text,encoding='utf-8')
    (downloads/'SpecCompare_Windows_v1.2.0.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (downloads/'SpecCompare_Windows_v1.2.0_build-report.json').write_bytes((artifacts/'build-report.json').read_bytes())
    # Stage only this app's new distribution metadata (and small ZIP when applicable).
    paths=['downloads/SpecCompare_Windows_README.md','downloads/SpecCompare_Windows_v1.2.0.json','downloads/SpecCompare_Windows_v1.2.0_build-report.json']
    if not use_release:paths += ['downloads/'+ZIP,'downloads/'+ZIP+'.sha256']
    command('git','config','user.name','github-actions[bot]');command('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    command('git','add','--',*paths)
    if command('git','diff','--cached','--quiet',check=False).returncode:
        command('git','commit','-m','Publish verified SpecCompare Windows v1.2.0 [skip ci]')
        command('git','push','origin','HEAD:'+BRANCH)
    download_verified(url,manifest['sha256'])
    if setup_url:download_verified(setup_url,sha(artifacts/SETUP))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
