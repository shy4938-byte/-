# SpecCompare Windows v1.0.0

MEMORY / SSD / VGA PDF 데이터시트에서 사양 후보와 페이지 근거를 추출하고,
사용자가 검토·수정한 값을 기존 Excel 비교 양식에 입력하는 오프라인 앱입니다.
Python, Git, VS Code를 최종 사용자 PC에 설치할 필요가 없습니다.

## 다운로드

자동 빌드와 ZIP 압축 해제 후 EXE 검증이 성공해야 배포됩니다.
실제 게시 위치/해시/Actions 실행 주소는 [배포 안내](downloads/SpecCompare_Windows_README.md)와
[배포 메타데이터](downloads/SpecCompare_Windows_v1.0.0.json)에 기록됩니다.

- 요청된 Git 경로: https://github.com/shy4938-byte/-/raw/refs/heads/speccompare-download/downloads/SpecCompare_Windows_v1.0.0.zip
- GitHub 권장 크기 50 MiB를 넘는 ZIP은 Git 저장소에 추가하지 않고 Releases에 게시합니다.
- Releases 경로: https://github.com/shy4938-byte/-/releases/download/speccompare-windows-v1.0.0/SpecCompare_Windows_v1.0.0.zip
- [자동 빌드 상태](https://github.com/shy4938-byte/-/actions/workflows/build-speccompare.yml)

링크의 실제 활성화 여부는 성공한 배포 보고서로 확인하세요. 이전 HTML 앱과 설치 파일은 삭제하지 않습니다.

## 사용 방법

1. 게시된 Windows ZIP을 다운로드하고 **전체 압축 해제**합니다.
2. `SpecCompare/SpecCompare.exe`를 실행합니다.
3. MEMORY / SSD / VGA를 선택한 뒤 PDF를 여러 개 추가합니다(드래그 지원).
4. 스펙 분석 후 비교할 모델을 선택합니다.
5. 셀을 선택해 원문 페이지·근거·규칙 일치도를 확인하고 필요한 값을 수정합니다.
6. 엑셀 저장으로 새 파일을 저장합니다. 4개를 넘으면 비교 그룹별로 저장합니다.

ZIP 구조:

```text
SpecCompare/
  SpecCompare.exe
  _internal/                 # Python 런타임·Qt·DLL 등; 삭제하지 마세요
  templates/스펙비교 양식(1).xlsx
  README.txt
```

가격 등 PDF에 없는 값은 확인 필요입니다. 자동 추출은 검토 필요이며 원문 검토 후 확인 완료로 표시합니다.
원본 PDF 열기 버튼은 현재 선택값의 페이지를 기본 PDF 뷰어에서 열도록 요청합니다(뷰어별 페이지 이동 지원은 다름).
비교표와 Excel은 최대 속도만 표시하고 QD/병기값/TurboWrite 조건은 상세정보에 남깁니다.
제품 값은 가운데 정렬합니다. 템플릿 원본, 다른 시트, 수식, 병합, 인쇄 설정은 보존합니다.

## PDF 처리 범위

- 테두리 있는 표, 좌표 기반 무테 제품 목록, 행/열 방향 모델 표, 콜론 유무가 다른 항목 문장을 처리합니다.
- 항목 동의어를 정규화하고 용량·품번을 통해 성능 표와 모델을 연결합니다.
- 헤더의 단위를 값에 적용하며 Gb(칩 비트 용량)와 GB(모듈 바이트 용량), MT/s와 MHz를 구분합니다.
- 같은 용량의 서로 다른 모델이 모호하거나 값이 충돌하면 자동 확정하지 않습니다.
- 실제 검증 문서: Samsung PM9E1/PM9A1 SSD, ESSENCORE DDR5 SO-DIMM, Samsung DDR5 UDIMM.
- 추가 검증: 제조사 이름을 고정하지 않은 합성 표/문장 변형, VGA 합성 PDF.

**모든 PDF 양식의 완전한 자동 분석을 보장하지 않습니다.** 회전/스캔/복잡한 다단 표/생략된 헤더는
미인식될 수 있습니다. OCR은 내장하지 않았으며 스캔/암호화 PDF에는 명확한 안내를 표시합니다.
규칙 일치도는 경험적으로 보정된 정확도 확률이 아닙니다. 원문 페이지와 모델/측정 조건을 확인하세요.

## 자동 빌드 및 재현

`.github/workflows/build-speccompare.yml`이 Windows 최신 안정 러너에서 Python 3.11 x64를 설치합니다.
단위/GUI 테스트 → PyInstaller onedir → ZIP 생성 → 한글 경로 압축 해제 → 개발 Python 없는 PATH로
실제 EXE의 MEMORY/SSD/VGA 분석·Worker·GUI 편집·Excel 재개방을 검증 → Artifact 업로드 순서입니다.
선택적으로 러너에 설치된 Inno Setup으로 설치 프로그램과 설치 후 EXE도 검증합니다.
실패하면 publish 작업이 실행되지 않습니다. 배포 전후 SHA-256을 확인합니다.

빌드 작업은 contents:read, 배포 작업만 contents:write입니다. downloads 변경은 빌드 트리거에서
제외하고 배포 커밋에 [skip ci]를 넣어 반복 실행을 막습니다. 기존 다른 파일은 변경하지 않습니다.
50 MiB보다 큰 바이너리는 Releases를 사용합니다. 기존 버전의 다른 파일을 덮어쓰지 않습니다.

Windows 개발 머신에서 재현:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python packaging/build_windows.py
```

실제 제조사 PDF는 사용자가 제공한 파일이므로 Git에 넣지 않습니다. 관련 환경변수가 없으면 CI의
실제 PDF 테스트는 명시적으로 skipped이며 합성 표/GUI/패키지 테스트는 실행됩니다.
로컬 실문서 검증과 GitHub Actions 검증을 구분하여 빌드 보고서에 기록합니다.

## 오류 확인

Windows 10/11 x64 및 ZIP 전체 압축 해제를 확인하세요. _internal DLL 폴더를 함께 유지하세요.
폴더 쓰기 권한, Excel 파일 잠금, PDF 암호/스캔 여부를 확인하세요. 미서명 파일은 SmartScreen
경고가 나타날 수 있습니다. 보안 기능을 끄는 대신 출처와 검사 결과를 확인하세요.

실제 Windows 10/11 일반 사용자 PC의 설치·보안 정책·Microsoft Excel UI 확인은 자동 러너 테스트와
다릅니다. 미검증 항목은 downloads/SpecCompare_Windows_BUILD_REPORT.md를 확인하세요.
