"""Build and verify an onedir Windows app; no repository binary mutation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.0.0'
def run(command,**kwargs):
    subprocess.run([str(v) for v in command],check=True,**kwargs)

def verify_zip(archive,output):
    output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('ZIP CRC failure')
        required={'SpecCompare/SpecCompare.exe','SpecCompare/templates/스펙비교 양식(1).xlsx','SpecCompare/README.txt'}
        if not required.issubset(z.namelist()) or not any(n.startswith('SpecCompare/_internal/') for n in z.namelist()):raise RuntimeError('Incomplete distribution')
        for name in z.namelist():
            if not (output/name).resolve().is_relative_to(output.resolve()):raise RuntimeError('Unsafe ZIP path')
        z.extractall(output)
    app=output/'SpecCompare'/'SpecCompare.exe'
    env=os.environ.copy()
    for key in ['PYTHONHOME','PYTHONPATH']:env.pop(key,None)
    # Prove the EXE does not locate a development Python through PATH.
    windows=Path(os.environ.get('SystemRoot',r'C:\Windows'))
    env['PATH']=str(windows/'System32')+';'+str(windows)
    env['QT_QPA_PLATFORM']='offscreen'
    results=output/'검증 결과'
    run([app,'--self-test',results],cwd=output,env=env,timeout=180)
    report=json.loads((results/'self-test.json').read_text(encoding='utf-8'))
    if report.get('status')!='passed' or not report.get('frozen'):raise RuntimeError('Packaged runtime verification failed')
    return report

def build():
    if sys.platform!='win32' or platform.architecture()[0]!='64bit':raise RuntimeError('Build requires 64-bit Windows Python')
    os.chdir(ROOT)
    dist=ROOT/'dist'/('windows-v'+VERSION)
    run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name','SpecCompare','--icon',ROOT/'assets/icon.ico','--add-data',str(ROOT/'assets')+';assets','--distpath',dist,'--workpath',ROOT/'build'/'windows-native','--specpath',ROOT/'packaging'/'windows',ROOT/'main.py'])
    app=dist/'SpecCompare';(app/'templates').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'assets/template.xlsx',app/'templates/스펙비교 양식(1).xlsx')
    shutil.copy2(ROOT/'packaging/windows/README.txt',app/'README.txt')
    archive=dist/f'SpecCompare_Windows_v{VERSION}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(app.rglob('*')):
            if p.is_file():z.write(p,Path('SpecCompare')/p.relative_to(app))
    report=verify_zip(archive,dist/'ZIP 압축 해제 검증')
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    record={'version':VERSION,'archive':archive.name,'bytes':archive.stat().st_size,'sha256':digest,'runtime':report,'github_actions':os.environ.get('GITHUB_ACTIONS')=='true','runner_os':os.environ.get('RUNNER_OS'),'source_sha':os.environ.get('GITHUB_SHA'),'python':sys.version,'installer':'not built by this command'}
    (dist/'build-report.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(archive)
    return archive

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify-zip',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.verify_zip:verify_zip(args.verify_zip,args.output or ROOT/'build'/'ZIP 검증')
    else:build()
