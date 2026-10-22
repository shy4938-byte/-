# HanaFX · 하나은행 USD 최초 고시 대시보드

Windows 10/11 x64용 독립 실행 앱입니다. Python·Node.js·AI 프로그램 설치가 필요 없습니다.
하나은행 공식 USD/KRW **최초 1회차 매매기준율**을 조회합니다. 장중 시장 실시간 호가와는 다릅니다.

## 다운로드·실행

[Windows ZIP 다운로드](https://github.com/shy4938-byte/-/releases/download/hanafx-windows-v1.0.1/HanaFX_Windows_v1.0.1.zip) · [설치형 EXE 다운로드](https://github.com/shy4938-byte/-/releases/download/hanafx-windows-v1.0.1/HanaFX_Setup_v1.0.1.exe)

오늘만 갱신하는 v1.0.1입니다. 빌드·배포 및 실행 검증 결과는 TEST_REPORT.md에 기록합니다. [배포 안내](../downloads/HanaFX_Windows_README.md)에서 SHA-256을 확인할 수 있습니다.
[Windows Actions](https://github.com/shy4938-byte/-/actions/workflows/build-hanafx.yml)에서 Artifact도 받을 수 있습니다.

1. ZIP 전체 압축 해제 → HanaFX/HanaFX.exe 실행. 또는 제공된 설치형 EXE를 실행합니다.
2. 실행 시 자동 조회합니다. **오늘 환율만 갱신**으로 오늘 데이터만 다시 확인합니다.
3. 저장된 과거 자료는 즉시 표시하며, 자동 조회·갱신·날짜 전환 때는 **오늘 날짜만** 조회합니다. 주말·휴일에도 과거 날짜를 추가 조회하지 않습니다. 최근 고시는 이미 저장된 자료에서만 표시합니다.
4. 처음 사용하는 PC나 중간에 사용하지 않은 기간 등 **과거 미수집 자료는 자동으로 채우지 않습니다**. 필요할 때 **과거 누락 자료 받기**를 한 번 실행하세요. 올해·작년 비교 기간을 수집하므로 수 분~십여 분 이상 걸릴 수 있으며 취소 후 이어받기를 지원합니다. 이미 받은 정상 과거 값은 재조회하지 않습니다.
5. **과거 수집 시 저장된 자료도 재조회**는 명시적으로 과거 자료를 재검증할 때만 선택합니다. 오늘 갱신에는 적용되지 않습니다.
6. **Excel 저장**으로 월평균_비교 / 당월_일별_비교 / 환율_원본데이터 시트를 저장합니다.

원본 은행 데이터나 샘플 DB를 배포 앱에 끼워 넣지 않습니다. 처음에는 인터넷이 필요합니다.
인터넷 실패 시 수집된 데이터만 표시하고, 저장된 데이터·부분 자료·오류 상태를 구분합니다.
v1.0.0에서 사용하던 DB 경로와 스키마를 그대로 사용하므로 같은 Windows 사용자라면 업데이트 후에도 기존 데이터가 유지됩니다. 앱을 사용하지 않은 날의 값은 다음 실행에서 자동으로 채우지 않으며, 과거 누락 자료 받기로 보충합니다.

DB는 Windows의 사용자 AppLocalDataLocation/HanaFX 폴더에 저장합니다(일반적으로 %LOCALAPPDATA%/HanaFX/HanaFX/).

## 계산 기준

- 한국시간 Asia/Seoul, 원/USD 단위. 날짜가 바뀌면 제목·표·그래프·Excel 범위를 자동 재계산합니다.
- 월평균: 올해 1월~지난달과 전년 동일 월. **각 고시일 최초 매매기준율 산술평균**입니다. 은행 공식 월평균과 다를 수 있습니다.
- 1월에는 완료된 월이 없다고 표시합니다. 일별은 당월 1일~오늘 및 전년 동일 월일입니다.
- 주말·공휴일·미수집일의 환율을 채우지 않습니다. 빈 날짜는 그래프 선도 연결하지 않습니다.
- 노란 월평균 셀은 오류/미수집이 있는 부분 자료입니다. 툴팁에서 고시일·고시 없음·오류·미수집 수를 확인합니다.
- 상단: 오늘 고시가 없으면 최근 14일 내 검증값을 **실제 날짜와 함께 최근 고시**로 표시합니다. 오늘 값으로 부르지 않습니다.
- 상단 전년 비교는 실제 표시 고시일의 전년 동일 월일 기준입니다. 전년 해당일 고시 없음/미수집, 2월29일 대응일 없음이면 비교 불가입니다.
- 표·차이·변동률·그래프는 같은 Snapshot으로 계산합니다. 소수점 둘째 자리 표시, 원본 고시값은 Decimal/SQLite 텍스트로 보존합니다.

## 수집·접근 정책

공식 페이지: https://www.kebhana.com/cont/mall/mall15/mall1501/index.jsp?_menuNo=23100

조회: POST https://www.kebhana.com/cms/rate/wpfxd651_01i_01.do

- requests.Session, 공식 Referer, 투명한 HanaFX User-Agent, 세션 초기 접속.
- 날짜 필드 tmpInqStrDt(공식 초기 페이지에 정확한 필드가 있으면 그 이름 사용), inqStrDt=YYYYMMDD, curCd=USD, pbldDvCd=1.
- 병합 머리글을 펼쳐 매매기준율 열을 찾습니다. 현찰·송금 환율을 열 번호로 추측하지 않습니다.
- 기준일·고시일·1회차·USD·숫자·고시시각 검증. 메타데이터의 조회시각은 고시일시와 분리합니다.
- 이전 고시일을 반환하면 요청일 값으로 저장하지 않습니다. 해당 날짜 고시 없음 상태를 표시합니다.
- 요청 간 최소 1.2초, 타임아웃 및 최대 3회 시도. 401/403/robots 차단 시 중단하며 인증·접속 제한을 우회하지 않습니다.
- 429의 Retry-After를 지키며 긴 대기를 요구하면 중단합니다. HTML 변경·연속 오류 때도 추가 대량 요청을 중단합니다.
- 사이트 이용조건·접근 정책은 변경될 수 있으며 은행 공식 화면에서 확인해야 합니다. 프로그램은 보안 우회·로그인 자동화를 하지 않습니다.

## 개발·검증

```powershell
cd HanaFX
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python launcher.py
```

build_windows.bat 또는 루트의 .github/workflows/build-hanafx.yml로 네이티브 Windows onedir 빌드.
HanaFX/.github/workflows/build-windows.yml은 프로젝트 내 참고 복사본이며, 이 저장소에서 실행되는 워크플로는 루트 파일입니다.

샘플 HTML·합성 GUI 검사·실제 서버 검사는 TEST_REPORT.md에서 구분합니다.
GitHub Windows에서 실제 서버·완료 월 계산·EXE 실행·조회 버튼 worker·Excel·ZIP 압축 해제를 검증한 후 배포합니다.
실제 사용자 PC의 보안 경고/화면, Microsoft Excel UI, 모든 미래 HTML 변경은 별도 검증 범위입니다.
