# SpecCompare Windows v1.0.1 검증

원인: 기본 MEMORY 탭에서 SSD PDF를 분석할 때, 공통 필드(부품번호·용량)만 인식하여 메모리 항목의 결과를 그대로 표시했습니다.

수정:
- 본문 앞 3페이지의 명시적 제품군 근거로 SSD / MEMORY / VGA 판별. 판별 근거가 없거나 복합적인 문서는 사용자가 선택한 제품군을 유지.
- 자동 판별된 결과 제품군으로 GUI 탭·항목 및 Excel 저장 시트 동기화.
- 다른 제품군 PDF를 한 번에 분석한 경우 비교 결과를 섞지 않고 안내.
- 엄격한 parser API는 다른 제품군을 지정하면 안내 오류를 반환. GUI Worker에서만 자동 전환 사용.
- 기존 v1.0.0 배포 파일 보존. 새 v1.0.1 배포.

로컬 검증:
- 21개 테스트 통과(실제 PM9E1, PM9A1, ESSENCORE, Samsung DDR5 포함).
- PM9A1을 MEMORY로 선택하고 자동 판별: SSD로 분류, Samsung PM9A1 256GB/512GB/1024GB/2048GB, 모델별 성능·측정 근거 검증 통과.
- GUI에서 MEMORY 기본 상태에 SSD 업로드 → SSD 항목 자동 표시 → SSD Excel 저장 회귀 테스트 통과.
- SSD·MEMORY 혼합 업로드 차단 검증 통과.
- 실행 파일 자체 테스트에도 위 제품군 자동 전환 재현 추가.

Windows 빌드: https://github.com/shy4938-byte/-/actions/runs/39397952283

미검증: 일반 사용자 Windows 10/11 PC의 화면·보안 경고, Microsoft Excel UI, 실제 VGA 제조사 문서, 모든 임의 PDF 레이아웃. 명확한 제품군 근거가 없는 문서는 사용자가 탭을 선택해야 합니다.

배포 검증 완료: Windows build/publish 모두 성공. 압축 해제 EXE 및 설치 EXE 자체 검증 통과(제품군 자동 전환 포함). 공개 ZIP·설치형 EXE 실제 다운로드 확인. ZIP CRC/전체 SHA-256 검증 통과.

ZIP SHA-256: `1dbf7ca8abe44fdff0ed64078de3ad6cb0e1ddb24fb324b80393c40b73b345dc`.
