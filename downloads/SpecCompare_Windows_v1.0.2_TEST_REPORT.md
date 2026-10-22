# SpecCompare Windows v1.0.2 검증

수정 대상: 990 PRO처럼 표의 오른쪽 선이 없고 QD/Thread 레이블이 여러 줄에 걸친 용량별 사양표, 모델명·포장 내용·판매 코드가 나뉜 제품 목록.

변경:
- 글자 좌표와 명시된 용량 헤더로 오른쪽 열린 열 복원. 용량 열 연결이 모호하면 자동 입력 보류.
- Sequential / Ran. Read / Ran. Write 및 QD/Thread 병합 레이블 인식. QD1과 QD32 원문 값·페이지·조건 보존.
- Model Name과 Model Code 분리, 수직 병합된 모델번호를 해당 용량에 연결. 판매 코드 변형은 별도 필드.
- Samsung 소비자 SSD 제품군 표기와 용량별 DRAM 연결.
- 원본 Excel 양식 및 가운데 정렬 유지. 이전 배포 파일 보존.

검증:
- 실문서 포함 기존 회귀 검사 23개 모두 통과(990 PRO, PM9E1, PM9A1, ESSENCORE, Samsung DDR5).
- 추가 모호성 안전 검사 1개 통과. 최종 테스트 24개 중 실제 문서 5개는 로컬에서 실행하고 CI는 원본 PDF 없이 건너뜀.
- 990 PRO 1TB / 2TB 모두 순차읽기 7,450 MB/s, 순차쓰기 6,900 MB/s.
- 랜덤읽기 QD32/Thread16: 1,200K / 1400K IOPS. 랜덤쓰기: 두 모델 모두 1,550K IOPS.
- QD1/Thread1 읽기 22K, 쓰기 80K IOPS 보존.
- 내구성 600 / 1,200 TB, DRAM 1GB / 2GB LPDDR4, 기본 모델번호와 판매 코드 변형 검증.
- 실제 990 PRO 결과를 원본 Excel에 입력하고 C/D열 값·가운데 정렬·재열기 확인.
- 배포 EXE 자체 검증에 다른 수치를 가진 합성 용량 표를 추가(특정 PDF 정답 하드코딩 방지).

한계: 임의의 모든 제조사·레이아웃, 실제 VGA 제조사 문서, 일반 사용자 Windows PC의 화면·보안 경고, Microsoft Excel UI는 미검증입니다. 합성 GUI 검증은 Qt offscreen입니다.

Windows Actions: https://github.com/shy4938-byte/-/actions/runs/39727129790

Windows build/publish 모두 성공. 압축 해제 EXE 및 실제 설치 후 EXE의 용량별 표/QD 회귀 검사·GUI 수정·Excel 재열기 검증 통과. 공개 ZIP·설치형 EXE 직접 다운로드 확인. ZIP 전체 CRC, SHA-256, AMD64 PE, 템플릿 원본 해시 확인 통과.

ZIP SHA-256: `afb80848393835f4709fe3e94016370c0df7ee28d6d4aa04835d8a213f9de1c5`.
