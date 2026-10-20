SpecCompare Windows v1.0.0 (64-bit)

1. ZIP 전체를 압축 해제하세요. ZIP 내부에서 실행하지 마세요.
2. SpecCompare 폴더의 SpecCompare.exe를 더블클릭하세요.
3. MEMORY / SSD / VGA 제품군을 선택하세요.
4. PDF를 추가하거나 끌어 놓고 스펙 분석을 누르세요.
5. 여러 모델이 있으면 비교할 모델을 선택하세요.
6. 원문 페이지/근거와 상세정보를 확인하고 값을 수정하세요.
7. 엑셀 저장을 눌러 새 파일로 저장하세요.

Python, VS Code, Git 설치는 필요하지 않습니다. _internal 폴더와 templates
폴더를 실행 파일과 함께 유지하세요. templates의 원본은 수정되지 않습니다.
원본 양식의 선택 제품군 C~F열만 입력하며 제품 값은 가운데 정렬됩니다.

알려진 한계: 모든 PDF 양식의 정확한 추출을 보장하지 않습니다. 표 구조와
항목 표현이 불명확하면 확인 필요로 남습니다. 자동 추출값은 검토 필요이며
사용자가 원문/단위/모델/측정 조건을 확인해야 합니다. OCR은 내장하지 않습니다.
스캔 PDF는 OCR 후 사용하고 암호화 PDF는 암호 해제 후 사용하세요.
실제 VGA 제조사 PDF의 검증 범위는 빌드 보고서를 확인하세요.

실행 오류 시: Windows 10/11 x64 여부, ZIP 전체 압축 해제, 백신 격리 여부,
폴더 쓰기 권한을 확인하세요. 미서명 파일은 SmartScreen 경고가 발생할 수
있습니다. 보안 기능을 끄지 말고 출처/검사 결과를 확인하세요.

소스 및 오류 보고: https://github.com/shy4938-byte/-/tree/speccompare-download
Windows 배포 및 실제 테스트 범위: downloads/SpecCompare_Windows_BUILD_REPORT.md
