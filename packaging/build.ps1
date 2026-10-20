$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:OS -ne 'Windows_NT') { throw 'Windows에서 실행하세요.' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw '테스트 실패: 배포하지 않습니다.' }
python packaging/build_windows.py
if ($LASTEXITCODE -ne 0) { throw 'Windows 빌드 또는 압축 해제 실행 검증 실패' }
