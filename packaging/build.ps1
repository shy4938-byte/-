$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:OS -ne 'Windows_NT') { throw 'Windows에서 실행하세요.' }
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 환경 생성 실패' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '의존성 설치 실패' }
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw '테스트 실패' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name SpecCompare --icon assets/icon.ico --add-data 'assets;assets' main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 실패' }
Write-Host 'dist\SpecCompare\SpecCompare.exe를 실행해 PDF 분석/편집/엑셀 저장을 검증하세요.'
