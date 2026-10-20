# Windows v1.0.0 검증 상태

소스 검증과 실제 Windows Actions 빌드/배포를 구분합니다. 실행: https://github.com/shy4938-byte/-/actions/runs/39393098706

소스 커밋: `dd6a04703febfe94b447aee33826c127c698a267`.

- 로컬: 19개 테스트 통과(실제 PDF 4개 포함). PySide6 GUI/Worker, 원본 Excel, 다양한 표 방향·동의어·단위·모호성 검증.
- 실문서: PM9E1, PM9A1, ESSENCORE DDR5 SO-DIMM, Samsung DDR5 UDIMM를 사용. PDF는 저장소에 포함하지 않음.
- GitHub Windows: 단위/GUI 테스트 통과. 실제 PDF는 비공개 입력으로 러너에 전달하지 않아 관련 4개 테스트는 건너뜀.
- Windows onedir EXE 빌드 및 ZIP 압축 해제 후 EXE 자체 검증 통과. 개발 Python이 없는 PATH, 한글 경로, MEMORY/SSD/VGA 합성 PDF, 다중 PDF, GUI 수정, Excel 저장·재열기 검증.
- 게시된 ZIP/설치 프로그램 여부와 실제 SHA-256은 SpecCompare_Windows_v1.0.0.json이 기준.
- 실제 VGA 제조사 PDF, 일반 사용자 PC의 SmartScreen/Defender, Microsoft Excel UI 실행은 미검증.
- 모든 제조사/모든 레이아웃에서의 완전 자동 추출은 보장하지 않음.

## 배포 검증 완료

- GitHub Actions build / publish 모두 성공.
- Inno Setup 설치형 EXE 생성, Windows 러너에 실제 설치, 설치된 EXE 자체 테스트 통과.
- 공개 ZIP 및 설치형 EXE를 별도로 다운로드하여 URL 접근 확인.
- ZIP: 89,368,420 bytes (85.2 MiB), 전체 CRC 검사 통과, PE AMD64 확인, 400개 파일 포함.
- ZIP SHA-256: `0c5317f885c7681e0de6e749c7a34d6018a767a3be3784eb3846a553789556e4`.
- 설치 EXE: 63,560,072 bytes. SHA-256: `bf024d0316b3e74fa9eae39094ca77c54435fe43610a81a4b5a69645e91b44ba`.
- ZIP 내 Excel 원본 SHA-256과 소스 템플릿 해시 일치.
- ZIP이 50 MiB를 넘어 GitHub Releases로 배포. downloads/에는 안내, 매니페스트, 빌드 보고서 저장.
- 다운로드: https://github.com/shy4938-byte/-/releases/tag/speccompare-windows-v1.0.0

검증 한계: Windows 러너는 개발 도구가 설치된 환경입니다. 실행 검증은 Python 개발 경로를 PATH에서 제거하고 번들 라이브러리 위치를 확인했지만, 별도의 초기화된 Windows 10/11 사용자 PC 테스트를 대신하지 않습니다. GUI 검증은 Qt offscreen이며 사용자의 실제 화면·보안 경고 확인은 미검증입니다.
