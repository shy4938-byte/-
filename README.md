# SpecCompare Windows 배포

[Windows 다운로드·실행 안내](README_WINDOWS.md) · [GitHub Actions](https://github.com/shy4938-byte/-/actions/workflows/build-speccompare.yml)

Windows 네이티브 빌드와 실행 검증이 성공한 파일만 자동 게시합니다. 실제 ZIP 위치와 해시는 배포 작업이 생성하는 downloads/SpecCompare_Windows_v1.0.1.json에서 확인할 수 있습니다.

# 설치 없이 여는 HTML 버전

`downloads/SpecCompare_HTML.zip`을 받아 압축을 푼 뒤 `SpecCompare.html`을 최신 Chrome/Edge에서 여세요. PDF 엔진과 원본 Excel 양식을 포함하며 인터넷·Python·EXE 설치가 필요 없습니다. 사용법과 검증 범위는 browser/README.md와 browser/TEST_REPORT.md에 있습니다.

# SpecCompare

Python 3.11+ / Windows 10·11용 오프라인 PC 부품 PDF 비교 프로그램.

## 실행

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

MEMORY/SSD/VGA 탭 선택 → PDF 추가 또는 드래그 → 스펙 분석 → 모델 선택 → 값 검토/수정 → 엑셀 저장.
한 그룹은 최대 4개 제품이며 초과하면 비교 그룹이 자동 생성됩니다. 저장은 현재 그룹만 적용합니다.
셀을 누르면 원본 경로, 페이지, 원문 근거와 상태를 표시합니다. 수동 수정 후 검토하여 ‘선택값 확인 완료’를 누르세요.
제품 상세정보 버튼으로 추가 사양을 조회하고 좌우 이동 버튼으로 순서를 변경합니다.

## 원본 엑셀

제공받은 `스펙비교 양식.xlsx`를 변경 없이 `assets/template.xlsx`로 포함했습니다.
- 메모리: B5~B11 항목 → C5:F11. ‘규격’은 메모리 규격에 대응.
- SSD: B5~B14 항목 → C5:F14.
- VGA: B5~B11 항목 → C5:F11.

저장 전 openpyxl로 시트/행/수식/병합을 검사합니다. 원본 OOXML 패키지를 복사하여 선택 시트의 입력 셀만 갱신합니다. 다른 시트, 스타일, 열 너비, 행 높이, 수식, 인쇄 설정 등 나머지 패키지 파일은 원본 바이트를 유지합니다. 출력에 없는 제품 열은 비웁니다. 원본 덮어쓰기는 금지하며 임시 파일 작성 후 결과를 교체합니다. PDF나 수동 입력 문자열은 Excel 수식으로 실행되지 않습니다.

## 분석 범위와 주의사항

PyMuPDF 텍스트와 pdfplumber 격자 표를 분석합니다. `항목: 값` 텍스트와 첫 열이 Model/Part Number/모델명인 표를 지원합니다. 모델 헤더의 각 열을 별도 제품으로 처리하고 반복 모델은 병합하며 충돌값은 확인 필요로 남깁니다. 반복 헤더가 있는 다중 페이지 표는 같은 모델별로 병합합니다. 헤더가 없는 연속 페이지는 자동 추정하지 않습니다.

PDF마다 표 레이아웃과 표현이 달라 **모든 제조사 PDF의 자동 추출을 보장하지 않습니다**. 표 모델을 식별할 수 없는 복수 모델 텍스트는 자동 입력을 보류합니다. 콜론 없는 자유 문장, 복잡한 무테 표, 모델 열이 아닌 용량별 성능 행 등은 수동 확인이 필요합니다. 인식되지 않은 항목은 ‘확인 필요’이며 가격을 추정하지 않습니다. 자동 추출은 모두 ‘검토 필요’, 사람이 확인한 값만 ‘확인 완료’입니다. GB/s는 십진 MB/s로 변환하고 MHz와 MT/s, TDP/TGP/TBP는 구별합니다. OCR은 내장하지 않았습니다. 스캔 PDF는 외부 OCR 후 다시 불러오세요. 암호화 PDF는 먼저 암호를 해제해야 합니다.

추출 데이터는 메모리에 보관됩니다. 프로그램 종료 전 Excel로 저장하세요. PDF 분석은 QThread에서 수행되며 파일별 오류는 나머지 분석을 막지 않습니다.

## 테스트

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

실행 증거와 미검증 범위는 TEST_REPORT.md 참조.

## Windows 배포

1. Windows에 Python 3.11과 Inno Setup 7(x64)을 설치합니다(개발/빌드 머신에만 필요).
2. PowerShell에서 `./packaging/build.ps1` 실행. onedir 결과는 `dist/SpecCompare/SpecCompare.exe`입니다.
3. 해당 EXE를 직접 실행하여 한글 경로에서 PDF 추가, 분석, 수정, Excel 저장/열기를 확인합니다.
4. Inno Setup으로 `packaging/installer.iss`를 열고 Compile하거나 `ISCC.exe packaging/installer.iss` 실행.
5. 결과는 `dist/SpecCompare_Setup.exe`. 설치 후 Python 없는 Windows에서 재검증하세요.

아이콘/원본 템플릿/라이브러리는 배포 폴더에 포함됩니다. onedir 폴더 전체가 필요합니다.
미서명 신규 EXE는 Defender/SmartScreen 경고가 발생할 수 있습니다. 배포 시 코드 서명과 악성코드 검사를 권장하며 보안 기능을 끄도록 안내하지 않습니다. PyMuPDF 및 Qt를 포함한 의존성의 배포 라이선스를 검토하세요.

Windows용 Python 3.11.9를 Wine 10에서 실행해 EXE 및 설치 프로그램을 빌드했습니다. 실제 Windows 10/11에서의 검증과 Wine 검증은 구분하며, 최신 결과는 TEST_REPORT.md를 확인하세요.

### 추가 지원: 용량별 SSD 표
모델/용량 열이 있는 행 방향 제품 목록과 Parameter/Unit/용량 헤더 성능표를 용량으로 연결합니다. 사용자 제공 Samsung PM9E1 Rev 1.3 PDF의 4개 모델로 검증했습니다. 단일 파일 검증이 모든 제조사/표 구조의 지원을 보장하지는 않습니다.

패키지 검증 명령(개발자용): `SpecCompare.exe --verify-package "PDF 경로" "검증 결과 폴더"`. 내장 PDF 분석, GUI 데이터 표시와 Excel 저장을 실행하고 verification.json을 남깁니다.
