# 브라우저 버전 검증

Linux Chromium, Playwright의 offline=true 컨텍스트에서 검증했습니다. 환경의 관리 정책이 file:// 탐색을 차단하므로 동일 HTML의 내용을 about:blank에 주입하여 opaque origin에서 실행했습니다. 사용자 PC에서 파일을 더블클릭하는 단계 자체는 이 환경에서 검증하지 못했습니다. 앱은 서버 API, 외부 import, 별도 자산 경로를 사용하지 않는 단일 HTML입니다.

통과한 검증:
- 실제 PM9E1 Rev 1.3 PDF 업로드 → 4개 모델 선택 → 표 표시.
- 512/1024/2048/4096GB의 순차/랜덤 성능, TBW, PCIe 인터페이스를 원문과 대조.
- 기본 Excel 다운로드. openpyxl 재개방 및 값 검사. 원본 ZIP과 비교해 선택된 시트 XML 하나만 변경됨.
- 수동 수정, 확인 완료 상태, 수정값 Excel 저장.
- 5개 제품 비교 그룹 분리.
- MEMORY/VGA 합성 PDF의 용량·속도·전력 구분.
- 같은 Web Worker에서 여러 PDF 연속 분석.
- 복수 모델이 모호한 PDF의 자동 입력 보류.
- 스캔·암호화·손상 PDF 오류 처리.
- 브라우저 JavaScript 오류 0, 외부 HTTP 요청 0.

자동 검증 스크립트는 regression.cjs입니다. Playwright를 설치한 뒤 PLAYWRIGHT_MODULE(선택), SPECCOMPARE_HTML, SPECCOMPARE_PM9E1_PDF, SPECCOMPARE_SAMPLES, SPECCOMPARE_TEST_OUTPUT 환경변수로 로컬 경로를 지정할 수 있습니다. samples 생성은 generate_samples.py를 사용하세요. 실제 제조사 PDF는 소스나 앱에 포함하지 않습니다.

원본 EXE를 사용자 PC에서 실행하지 못한 정확한 원인은 아직 확정되지 않았습니다. 이번 HTML 배포본은 해당 설치 프로그램을 사용하지 않습니다.

## 1.1.1 회귀 검증
실제 PM9E1 PDF의 네 모델에 대해 제조사·제품군·용량 표시, 부품번호 분리, 표지/제품 목록의 근거 보존을 확인했습니다. UI 모델명과 상세정보, 내려받은 Excel C6:F6을 검사했으며 기존 성능값도 유지됩니다. 기존 브라우저 회귀 검증도 모두 통과했습니다.

## 1.1.2 실제 PM9A1 및 두 PDF 동시 검증
사용자 제공 PM9A1 Rev 1.1의 256/512/1024/2048GB 모델명·품번·PCIe Gen4·NVMe·순차/랜덤 속도·TBW를 p.1/3/6/7과 대조했습니다. QD1/QD32를 분리하고 슬래시 병기값과 순차 성능 주석 5를 보존했습니다. 두 PDF를 동시에 업로드해 각각 512GB를 선택하고 2개 제품만 비교하는 UI와 Excel C/D열 값을 확인했습니다. 선택하지 않은 열은 비어 있으며 원본 ZIP의 선택 시트 XML 이외는 보존됩니다. PM9E1 및 기존 브라우저 회귀 검증도 모두 통과했습니다. PM9A1 통합 테스트는 pm9a1_regression.cjs와 SPECCOMPARE_PM9A1_PDF/SPECCOMPARE_PM9E1_PDF 환경변수로 재현할 수 있습니다.
스크린샷 A열의 전부 미확인 제품은 최신 버전에서 제공된 PM9E1 PDF로 재현되지 않았습니다. 기존 결과의 정확한 생성 버전/모델 선택은 확정하지 않았습니다. PDF에 없는 가격은 계속 미확인입니다.

## 1.1.3 표시 형식 검증
PM9A1의 4개 용량에 대해 순차/랜덤 최대 속도만 표시되고 QD·원문 병기값·TurboWrite 미적용 수치는 내부 상세정보에 남는지 검사했습니다. PM9E1/PM9A1 512GB UI와 Excel의 순차읽기는 각각 12,200 MB/s, 6,900 MB/s입니다. 순차쓰기와 랜덤읽기/쓰기 역시 최대 수치와 단위만 Excel에 저장됩니다. QD256/QD32, PM9A1 순차읽기 TurboWrite 미적용 6,300 MB/s 보존과 PM9E1의 해당 값 미확인을 검증했습니다. 원본 Excel의 선택 시트 XML 이외 항목 보존 및 두 PDF 모델 선택 테스트가 통과했습니다.

## 1.1.4 정렬 검증
Chromium 화면의 비교표 th/td/input 계산 정렬이 모두 center임을 확인했습니다. MEMORY/SSD/VGA 내보내기의 C~F 입력 셀 가로/세로 정렬을 openpyxl로 검사했습니다. 원본과 비교하여 선택 시트 XML 및 필요한 추가 스타일 정의만 변경되며 다른 시트, 기존 글꼴·테두리·배경색·표시 형식을 보존합니다. 분석 로직은 변경하지 않았습니다.
