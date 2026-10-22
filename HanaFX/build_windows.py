"""Native Windows onedir build; verify extracted EXE with development PATH removed."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,zipfile

ROOT=Path(__file__).resolve().parent
VERSION='1.0.0'

def build():
    if sys.platform!='win32':raise RuntimeError('Windows runner required')
    dist=ROOT/'dist'/('windows-v'+VERSION)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name','HanaFX','--distpath',str(dist),'--workpath',str(ROOT/'build'),'--specpath',str(ROOT/'build'),'--collect-all','tzdata',str(ROOT/'launcher.py')],check=True,cwd=ROOT)
    app=dist/'HanaFX';shutil.copy2(ROOT/'README.md',app/'README.md')
    archive=dist/f'HanaFX_Windows_v{VERSION}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(app.rglob('*')):
            if path.is_file():z.write(path,Path('HanaFX')/path.relative_to(app))
    extracted=dist/'한글 압축 해제 검증'
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('Archive CRC failure')
        if 'HanaFX/HanaFX.exe' not in z.namelist() or not any(n.startswith('HanaFX/_internal/') for n in z.namelist()):raise RuntimeError('Incomplete distribution')
        z.extractall(extracted)
    env=os.environ.copy();env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    windows=Path(env.get('SystemRoot',r'C:\Windows'));env['PATH']=str(windows/'System32')+';'+str(windows);env['QT_QPA_PLATFORM']='offscreen'
    out=extracted/'실행 결과'
    process=subprocess.run([str(extracted/'HanaFX'/'HanaFX.exe'),'--self-test',str(out),'--live'],cwd=extracted,env=env,timeout=240)
    if process.returncode:
        error=out/'error.txt'
        if error.exists():
            detail=error.read_text(encoding='utf-8');print(detail)
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:f.write('### HanaFX runtime failure\n```text\n'+detail+'\n```')
        raise RuntimeError('Packaged runtime validation failed')
    runtime=json.loads((out/'self-test.json').read_text(encoding='utf-8'))
    if not runtime.get('frozen') or runtime.get('status')!='passed' or runtime['live'].get('status')!='passed':raise RuntimeError('Runtime/live validation incomplete')
    digest=hashlib.sha256(archive.read_bytes()).hexdigest();archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    report={'version':VERSION,'github_actions':os.environ.get('GITHUB_ACTIONS')=='true','source_sha':os.environ.get('GITHUB_SHA'),'sha256':digest,'bytes':archive.stat().st_size,'runtime':runtime,'installer':'not built'}
    (dist/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(ROOT/'publish_release.py',dist/'publish_release.py')
    print(archive)

if __name__=='__main__':build()
