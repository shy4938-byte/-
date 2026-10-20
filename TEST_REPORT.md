# 테스트 결과

검증 환경: Linux / Python 3.12.14 / PySide6 6.10.2. Windows는 미검증.

실행: `QT_QPA_PLATFORM=offscreen /workspace/speccompare-venv/bin/python -m unittest discover -s tests -v`

결과: **8개 테스트 통과, 실패 0, 건너뜀 0**.

- MEMORY/SSD/VGA 합성 텍스트 PDF의 항목·페이지·근거·가격 미확인 처리.
- 2개 모델 격자 표: 모델별 용량/속도 분리.
- 모호한 복수 모델 텍스트: 사양 혼합 방지 및 자동 입력 보류.
- 손상·빈 스캔·암호화 PDF 오류 안내.
- GB/s 변환, MHz 단위 유지.
- 실제 첨부 양식의 3개 제품군 행 매핑 및 한글 출력 파일 저장.
- Excel 셀 스타일, 열 너비, 행 높이, 병합, 인쇄 영역/설정, 다른 시트 값 보존. ZIP 구성요소 비교에서 선택 시트 XML만 변경됨. 원본 파일 바이트 불변, 수식 주입 방지.
- Qt 백그라운드 Worker 결과 전달, 한글 파일 경로, GUI 기동, 5개 제품 그룹 분리, 직접 편집, 순서 변경, 그룹별 Excel 출력.

GUI는 offscreen 자동 테스트로 검증했습니다. 실제 화면의 시각적 품질, 사용자 드래그 동작, OS 연결 프로그램으로 파일 열기와 설치 마법사는 수동 검증이 필요합니다. Linux에서 fontconfig 캐시 경고와 offscreen 플러그인 경고가 있었으나 테스트는 완료되었습니다.

실제 제조사 PDF 테스트: **미실행**. 제공된 PDF가 없어 제조사 명칭을 포함한 합성 PDF를 사용했으며 삼성/ESSENCORE/ADATA/NVIDIA/AMD 공식 문서의 정확도를 검증한 것으로 간주하지 않습니다. 복잡한 무테 표와 모델 헤더 없는 연속 페이지는 지원 범위 밖입니다.

Windows EXE/설치 파일: **미생성·미검증**. PowerShell PyInstaller onedir 빌드 스크립트와 Inno Setup 스크립트를 제공했습니다. Python 없는 Windows 10/11, 한글 설치 경로, 잠긴 Excel 파일, 실제 권한 제한 폴더, Defender/SmartScreen 및 설치/제거 검증이 남아 있습니다.

## 실제 PM9E1 Rev 1.3 검증 추가

사용자 제공 `PM9E1 M.2 SSD Datasheet_v1.3_For Gen.pdf`(56페이지)로 실행했습니다.
최초 실행에서 행 방향 제품 목록의 Capacity/LBA Count 헤더를 모델명으로 잘못 인식했습니다. 모델/용량 열이 있는 제품 목록과 용량별 성능 매트릭스를 연결하도록 수정했습니다. 공백 없는 `512GB` 단위 인식 오류도 수정했습니다.

원문 p.3/5 제품 목록, p.6 성능표, p.7 TBW표와 4개 모델의 추출 결과를 대조했습니다. 512GB 순차쓰기의 현재 값 7,000 MB/s를 확인했습니다(이전 개정 이력의 6,300 MB/s를 사용하지 않음). 제조사, 인터페이스, PCIe 세대, NVMe 버전도 추출됩니다. 가격, DRAM, NAND, MTBF는 자동 확정하지 않고 확인 필요로 유지합니다.

실제 PDF 통합 테스트를 포함해 **9개 통과, 실패 0, 건너뜀 0**. 이전 ‘실제 제조사 PDF 미실행’ 기록은 최초 버전 기준이며 이 문서의 추가 검증이 최신입니다. 다른 제조사 PDF는 여전히 미검증입니다. Windows EXE 실행 검증도 여전히 미실행입니다.

재현: 환경변수 `SPECCOMPARE_PM9E1_PDF`에 해당 PDF 경로를 지정한 뒤 unittest를 실행하세요. PDF는 소스 ZIP에 포함하지 않습니다. 환경변수가 없으면 해당 통합 테스트 1개만 명시적으로 건너뜁니다.

## Windows 설치 파일 빌드 추가

Windows Python 3.11.9 + PySide6 6.8.3 + PyInstaller 6.19.0 + Inno Setup 7.1.0(x64)을 Wine 10에서 실행했습니다. Qt 6.10의 Windows ICU 의존성과 Wine 호환성 문제로 PySide6를 6.8.3으로 고정했습니다.

- Windows용 Python에서 실제 PM9E1 테스트를 포함한 9개 테스트 통과(실패/건너뜀 0).
- PyInstaller onedir Windows x64 EXE 빌드 성공.
- 생성된 EXE 자체로 실제 PM9E1 4개 모델 분석, Qt GUI 표시 및 한글 경로 Excel 저장 성공.
- Inno Setup의 x64 설치 마법사 `SpecCompare_Setup.exe` 생성 성공.
- 한글 경로로 무인 설치 성공. 바로가기와 제거 프로그램 등록 확인.

이는 Wine 환경의 Windows 바이너리 검증입니다. 실제 Windows 10/11 PC에서의 실행, Defender/SmartScreen, 설치 마법사의 수동 조작은 별도 검증이 필요합니다. 설치 파일은 코드 서명되지 않았습니다. 이전 미생성 기록은 최초 버전 기준이며 이번 추가 기록이 최신입니다.

설치된 EXE에서 실제 PDF → GUI 표시 → 한글 Excel 저장 검증도 통과했습니다. 무인 제거 성공 및 설치된 실행 파일 삭제를 확인했습니다.
