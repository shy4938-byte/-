"""Keep full native-test diagnostics even if a Qt child process crashes."""
from pathlib import Path
import json,os,subprocess,sys
root=Path(__file__).resolve().parent
output=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'reports'/'unit-tests.json'
env=os.environ.copy();env['PYTHONUTF8']='1';env['QT_QPA_PLATFORM']='offscreen'
result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,env=env,capture_output=True,encoding='utf-8',errors='replace',timeout=180)
report={'status':'passed' if result.returncode==0 else 'failed','returncode':result.returncode,'python':sys.version,'stdout':result.stdout[-100000:],'stderr':result.stderr[-100000:]}
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
if '--strict' in sys.argv:raise SystemExit(result.returncode!=0)
