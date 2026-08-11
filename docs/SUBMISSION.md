# Claude Desktop 디렉터리 등재 신청 가이드

> 공식 MCP 레지스트리 발행과 **별개로**, Claude Desktop **인앱 검색/디렉터리**에 노출되려면
> Anthropic의 **커넥터/익스텐션 디렉터리 심사**를 통과해야 한다(레지스트리는 자동 동기화되지 않음).
> 본 문서는 심사 기준 충족 현황과 신청 절차를 정리한다.

## 현재 배포 상태 (심사 전에도 사용 가능)
- ⚠️ 공식 MCP 레지스트리: **구 네임스페이스** `io.github.rubato103/kci-openapi-mcp` v0.1.3 만 발행돼 있다.
  2026-08-11 GitHub 계정명이 `rubato103` → `rubatoyd` 로 바뀌어 **구 네임스페이스로는 더 이상 발행할 수
  없고**(발행이 GitHub OIDC 로 계정 소유를 검증한다), 기존 항목은 고아로 남는다.
  신 네임스페이스 `io.github.rubatoyd/kci-openapi-mcp` 는 **다음 태그 푸시 시 새 항목으로 생성**된다.
- ✅ Claude Desktop 설치용 `.mcpb`: https://github.com/rubatoyd/KCI_openAPI/releases/latest/download/kci-openapi-mcp.mcpb
- ✅ 수동 config / `.mcp.json`(Claude Code) 모두 동작 (uvx-from-git 라이브 검증됨)

## 심사 기준 (Anthropic 디렉터리)
리뷰어가 **모든 도구를 기능 테스트** + **정책 준수 스캔**을 수행한다(형식검사가 아닌 릴리스 게이트).

### 충족 현황 체크리스트
| 항목 | 상태 | 근거 |
|---|:--:|---|
| 모든 도구 기능 동작 | ✅ | MCP 프로토콜 스모크(stdio) + 라이브 검증, pytest 31 |
| 도구 안전성 annotations | ✅ | `readOnlyHint`(조회 6종)/`openWorldHint`(전체)/collect는 비파괴 쓰기 |
| 파괴적 동작 없음 | ✅ | 삭제·변조 없음. `kci_collect` 만 출력파일 생성(비파괴) |
| 자격증명 안전 | ✅ | `KCI_API_KEY` env 전용, 로그/응답/예외에 미노출(키 포함 URL 누출 차단), **선택**(OAI 무인증 동작) |
| 예외 누수 없음 | ✅ | 모든 도구 `@_safe` 로 dict 반환(프로토콜 안정) |
| 라이선스/문서 | ✅ | MIT, README, docs/(API·아키텍처·검색식) |
| 명확한 도구 설명 | ✅ | 각 도구 description에 REST/OAI·인증 필요여부 명시 |
| 패키징 검증 | ✅ | mcpb manifest 공식 검증 통과, server.json 레지스트리 스키마 통과 |

### 런타임 — ✅ 자체완결 `.mcpb` 제공 (uv·Python 불필요)
- Claude Desktop은 **Node.js만 번들**하고 Python은 안 함 → uv/python 타입은 시스템 Python 필요.
- 그래서 **PyInstaller 단일 실행파일**을 OS별로 빌드해 `server.type:"binary"` `.mcpb` 로 제공한다.
  - 산출물(릴리스 자산): `kci-openapi-mcp-win-x64.mcpb` · `…-macos-arm64.mcpb` · `…-linux-x64.mcpb`
  - 빌드 자동화: `.github/workflows/build-mcpb.yml`(win/mac/linux 매트릭스) — `packaging/binary/{manifest.json,entry.py}`
  - **클린 머신(uv·Python 미설치)에서 기동 검증 완료**(Windows): MCP 프로토콜 handshake + OAI 실호출.
- 심사 제출 시 **자체완결 `.mcpb`** 를 사용하면 리뷰어 클린 환경 기동 실패 리스크가 없다.
  - (참고) 경량 `kci-openapi-mcp.mcpb`(uvx-from-git)는 `uv` 필요 — 디렉터리 제출엔 자체완결본 권장.

## 신청 절차
1. Anthropic **커넥터/익스텐션 디렉터리 제출 폼**으로 신청(Anthropic 계정·신원 필요 — 메인테이너가 직접).
   - 진입: Claude 지원센터(support.claude.com)의 커넥터/익스텐션 문서 → 제출 폼 링크.
2. 제출물: 위 `.mcpb`(릴리스 자산) + 저장소 URL + 도구 목록/설명 + 개인정보·정책 준수 설명.
3. 리뷰어 기능 테스트·정책 스캔 → 통과 시 Desktop 인앱 디렉터리 노출.

## 참고
- 레지스트리/배포는 `uvx --from git+…` 가 **기본 브랜치(main) 최신**을 사용 → 코드 개선이 새 설치에 자동 반영.
  재현성 고정이 필요하면 manifest의 args를 `@v0.1.0` 태그로 고정(이 경우 개선 시 새 태그 발행).
- 빌드/발행 자동화: `.github/workflows/publish-mcp.yml`(태그 푸시 → `.mcpb` 빌드·릴리스·레지스트리 OIDC 발행).
