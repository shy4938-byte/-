# HanaFX 검증 보고서

샘플 테스트, 캡처 회귀, 실제 HTTP 테스트, 네이티브 Windows EXE 검증을 구분합니다.

- 로컬 클라우드는 네트워크 허용 목록에 하나은행이 없어 직접 접속 실패(클라우드 프록시 CONNECT 403). 은행 자체 거부로 판단하지 않음.
- Windows 공식 서버 probe: https://github.com/shy4938-byte/-/actions/workflows/hanafx-probe.yml
- 공개 진단: ../downloads/HanaFX_live_probe.json
- Windows probe에서 robots 허용, 초기 페이지 HTTP 200, 2026-10-22/2025-10-22 각각 HTTP 200·USD 최초 1회차 응답 확인.
- 실제 응답의 조회시각이 세 번째 날짜로 포함되는 것을 발견. 기준일·고시일시 레이블을 각각 파싱하도록 수정.
- 실제 고시값: probe 관측 시 2026-10-22는 1,325.50원, 2025-10-22는 1,423.70원. 앱의 고정 데이터나 초기 DB로 사용하지 않음.
- tests/fixtures/sample_20261022.html의 1,325.50은 사용자 제공 파서 테스트용 예시이며 라이브 테스트의 대체가 아님.
- captured_*.html은 라이브 probe에서 기록한 메타데이터·머리글·USD 행을 재구성한 회귀 fixture. 관측 시각·원본 응답 해시를 주석에 보존.

로컬: 파서·날짜·평균·누락·캐시·취소·접근 제한·표/그래프·Excel 테스트 통과. 최종 개수와 Windows 결과는 배포 전 갱신.

미검증: 일반 사용자 Windows 10/11 실물 PC, SmartScreen, Microsoft Excel GUI, 미래 은행 HTML/접근 정책 변경, 현재 2개 표본 외 전체 기간 값의 독립 대조.
