# HanaFX v1.0.0 검증 보고서

검증일: 2026-10-22. 샘플 HTML, 실제 HTTP, Windows EXE 실행을 구분합니다.

## 최종 배포 결과

- [Windows 빌드·게시 모두 성공](https://github.com/shy4938-byte/-/actions/runs/39746830962).
- 소스 커밋: `4f1a544abeb55d2b9f3815c5b292248a81525937`.
- [GitHub Release](https://github.com/shy4938-byte/-/releases/tag/hanafx-windows-v1.0.0).
- [ZIP](https://github.com/shy4938-byte/-/releases/download/hanafx-windows-v1.0.0/HanaFX_Windows_v1.0.0.zip): 55,098,420 bytes, SHA-256 `e2481d4f2647ddd576a76820a2c10748a7f872fd53cb89ba0ee60b2ba4bccf9b`.
- [설치형 EXE](https://github.com/shy4938-byte/-/releases/download/hanafx-windows-v1.0.0/HanaFX_Setup_v1.0.0.exe): 38,975,602 bytes, SHA-256 `2ebeb42c39666dc8710ae0411bb65833b330857e3d7c3ce8a04ff56282fb81ca`.
- 게시 작업과 별도로 클라우드에서 두 공개 URL을 실제 다운로드. ZIP SHA-256 일치, 862개 항목 CRC 정상, HanaFX.exe AMD64 PE(0x8664), _internal 런타임 포함, 샘플 DB 미포함 확인.
- Inno 설치 부트스트래퍼는 PE32이며 x64 앱을 설치합니다. 실제 앱 HanaFX.exe는 AMD64입니다.
- 큰 바이너리는 Git 파일로 커밋하지 않고 Release 첨부로 배포. 기존 프로그램과 파일 보존.

## 자동 테스트: 로컬 및 네이티브 Windows

각각 29개 테스트 통과. Windows 테스트 실패 시 빌드·배포 중단.

- 제공된 예시 1,325.50 파싱, 의미 기반 매매기준율 열 선택, USD·최초 회차·날짜·숫자 검증.
- 잘못된 통화·회차·다른 날짜·열 누락·모호한 행은 거부.
- 10월→11월, 12월→1월, 윤년 2월, 당월 첫 고시 전, 전년 대응일 없음.
- 고시일 산술평균, 결측값 미대입, 차이·변동률, 실제 최근 고시일 표시.
- 캐시 재사용·당일 재확인·취소 시 보존·오프라인 오류·robots 차단·제한된 재시도.
- 네이티브 Qt 표/그래프 일치, 월 전환 및 이전 작업 결과의 새 월 덮어쓰기 방지.
- Excel 3개 시트, 숫자·서식·출처·조회시각 검증 및 openpyxl 재열기.

합성 실행 검사는 별도 값과 보고서로 실행합니다. 합성 DB는 배포 앱에 포함하지 않습니다.

## 실제 하나은행 HTTP 검증

[완료 월 실제 조회 보고서](https://github.com/shy4938-byte/-/releases/download/hanafx-windows-v1.0.0/full-month-live-report.json)

Windows에서 공식 초기 페이지 및 robots 확인 후 실제 POST 조회. robots HTTP 200·조회 경로 허용. 요청 사이 최소 1.2초, 제한 우회 없음.

- 2026-10-22: USD 1회차 매매기준율 **1,325.50원**, 08:24:07 KST.
- 2025-10-22: USD 1회차 매매기준율 **1,423.70원**, 08:25:23 KST.
- 2026년 1월 31일 전체: 실제 고시 21일, 고시 없음 10일. 평균 **1,456.51원**.
- 2025년 1월 31일 전체: 실제 고시 18일, 고시 없음 13일. 평균 **1,455.79원**.
- 실제 일별 값을 별도로 합산한 평균과 앱 계산값 일치. 두 1월의 수집 상태 complete=true.
- 총 65개 요청일: 검증 환율 41일, 고시 없음 24일. 오류·미수집 없음(이 검증 대상 범위 내).
- 일요일 2026-10-18 및 휴일 2026-01-01에 은행이 이전 고시일을 반환함을 확인. 요청일 환율로 복사하지 않고 고시 없음 처리.
- 실제 조회 결과를 SQLite에 저장하고 Excel 생성. 실제 표/그래프 데이터 일치. 조회 버튼의 실제 수집 worker로 새 응답을 받은 후 취소까지 확인.

실제 고시값은 관측 당시 응답입니다. 고정 데이터나 초기 DB로 사용하지 않습니다. 2~9월 전체 및 10월 모든 일자의 독립 대조를 수행했다는 의미는 아닙니다.

## Windows 배포 앱 실행

[빌드·실행 보고서](https://github.com/shy4938-byte/-/releases/download/hanafx-windows-v1.0.0/build-report.json)

- Windows Actions, Python 3.11 x64, PyInstaller onedir 빌드.
- ZIP을 한글 경로에 압축 해제. PYTHONHOME/PYTHONPATH 제거, PATH에서 개발 환경 경로 제거 후 EXE 실행 성공.
- 압축 해제 EXE에서 합성 GUI·SQLite·Excel 검사와 실제 하나은행 조회·조회 버튼 worker 검사 통과.
- Inno Setup 생성 및 한글 경로에 실제 설치 성공. 설치된 EXE에서 동일 실행·실제 은행 검사 통과.
- GUI 자동 검사는 Qt offscreen 모드. 사용자 PC의 실제 모니터에서 직접 클릭한 육안 테스트와 구분합니다.
- 보고서 일부 시간은 PowerShell JSON 재직렬화 과정에서 UTC로 표시됩니다. 예: 2026-10-21T23:24:07Z = 2026-10-22 08:24:07 KST. 앱은 Asia/Seoul 사용, 번들 Asia/Seoul tzdata의 +09:00 확인.

## 발견·수정한 오류

1. 실제 응답에 기준일·고시일시 외 조회시각 날짜가 추가됨: 날짜 개수를 가정하지 않고 레이블별 파싱으로 수정.
2. Windows의 한글 strftime 서식에서 locale UnicodeEncodeError 발생: 연·월·일 숫자와 한글 리터럴을 직접 조합하도록 수정. 수정 후 29개 네이티브 테스트와 EXE 검사 통과.
3. 요청일 대신 이전 영업일 응답: 요청일에 환율을 대입하지 않고 고시 없음 처리.
4. 캐시와 고시 없음 재응답 충돌: 검증값은 보존하되 오류 상태로 표시해 완료 평균으로 오인하지 않게 수정.

초기 공개 `HanaFX_windows_unit_diagnostic.json`은 수정 전 실패 진단입니다. 최종 결과는 위 성공한 Actions 실행과 Release 보고서가 기준입니다.

## 테스트 출처 및 미검증 범위

- `tests/fixtures/sample_20261022.html`은 사용자 제공 예시 기반 파서 검사이며 라이브 연결 증거가 아닙니다.
- `captured_*.html`은 실제 probe의 메타데이터·머리글·USD 행을 재구성한 회귀 자료. 관측시각·원본 해시 보존.
- 로컬 클라우드의 은행 직접 접속은 허용 목록 제한으로 CONNECT 403. 실제 HTTP 검증은 제한을 우회하지 않고 Windows Actions에서 수행.
- **미검증**: 일반 사용자 Windows 10/11 실물 PC·SmartScreen·백신·실제 모니터 표시, Microsoft Excel GUI에서 직접 열기, 전체 연간 모든 값의 독립 대조, 미래 은행 HTML·접근 정책 변경.
- 인터넷 단절은 자동 테스트의 모의 연결 실패로 검증. 실제 PC의 네트워크 케이블 분리 시험은 미검증.
