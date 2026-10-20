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
