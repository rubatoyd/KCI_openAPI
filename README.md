# kci-openapi-mcp

<!-- mcp-name: io.github.rubatoyd/kci-openapi-mcp -->

한국연구재단(NRF) **KCI(Korea Citation Index)** 문헌·인용지수 검색·수집 **MCP 서버 + CLI**.
**REST Open API**(키워드 검색)와 **OAI-PMH**(무인증 대량 수확)를 **혼용**한다.
자매 프로젝트 scienceON-mcp(KISTI ScienceON)와 동일 아키텍처.

## 무엇을 하나
- 논문 검색·상세 (서지 · **국문/영문 초록** · 키워드 · 저자/소속)
- **OAI-PMH 대량 수확** (인증키 불필요 — 세트+날짜범위)
- 참고문헌 원형 수집 · 저널 인용지수/등재이력 (REST 전용)
- 대량 수집 → xlsx / csv / json / sqlite

## 두 인터페이스
| | REST Open API | OAI-PMH |
|---|---|---|
| 엔드포인트 | `…/po/openapi/openApiSearch.kci` | `…/oai/request` |
| 인증 | `KCI_API_KEY` 필요 | **불필요** |
| 질의 | 키워드 검색(title 필수) | 세트+날짜 대량 수확 |
| 인용지수·참고문헌 | ✅ | ❌ |
규격: [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md) · [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md) · 설계: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 현재 상태
- ✅ 구현·**REST/OAI 라이브 검증** 완료 · pytest 31 + MCP 프로토콜 스모크 · 도구 annotations
- ✅ **공식 MCP 레지스트리 발행됨**: `io.github.rubatoyd/kci-openapi-mcp` (registry.modelcontextprotocol.io 검색 가능)
- ✅ Claude Desktop **자체완결 `.mcpb`**(win/mac/linux, Python·uv 불필요) + Claude Code `.mcp.json`
- ⚠️ `mcp` SDK는 **1.x 고정**(`mcp>=1.2.0,<2`) — 2.0 에서 `mcp.server.fastmcp` 가 제거되어 상한 없이는 기동 실패

## MCP 클라이언트에 등록

### Claude Code
프로젝트 루트의 `.mcp.json` 이 자동 인식된다(키는 환경변수로 주입):
```bash
export KCI_API_KEY=<발급키>   # 선택 — 없으면 OAI 무인증 도구만 동작
# 또는 어디서나:
claude mcp add kci --env KCI_API_KEY=$KCI_API_KEY -- uvx --from git+https://github.com/rubatoyd/KCI_openAPI kci-mcp
```

### Claude Desktop
**(권장) 자체완결 `.mcpb` — Python·uv 불필요**, 더블클릭 설치:
[릴리스](https://github.com/rubatoyd/KCI_openAPI/releases/latest)에서 OS에 맞는 파일 다운로드 →
더블클릭(또는 Settings → Extensions → Install) → `KCI_API_KEY` 입력(선택).
- Windows: `kci-openapi-mcp-win-x64.mcpb` / macOS: `…-macos-arm64.mcpb` / Linux: `…-linux-x64.mcpb`

**(경량) `kci-openapi-mcp.mcpb`** — 크기 작지만 실행에 `uv` 필요(`uvx --from git+…`).

**(수동 config)** `%APPDATA%/Claude/claude_desktop_config.json`:
```json
{ "mcpServers": { "kci": {
  "command": "uvx",
  "args": ["--from", "git+https://github.com/rubatoyd/KCI_openAPI", "kci-mcp"],
  "env": { "KCI_API_KEY": "<발급키 또는 비움>", "KCI_OS_TRUST": "1" }
} } }
```

### uvx (저장소에서 직접 실행)
```bash
uvx --from git+https://github.com/rubatoyd/KCI_openAPI kci-mcp   # MCP 서버(stdio)
```
> PyPI에는 게시하지 않음 — 레지스트리 배포는 `.mcpb`(GitHub Release) 방식.

## CLI (로컬 개발)
```bash
uv sync                    # venv는 UV_PROJECT_ENVIRONMENT 로 클라우드 폴더 밖 권장
kci identify               # OAI 무인증 — 키 없이 즉시
kci harvest --set ARTI --from 2024-01-01 --until 2024-12-31 --contains 학부모 --max 500
kci search --title 경계선지능 --rows 20   # REST(인증키 필요)
kci collect --config config/borderline_slow.yaml
```

### MCP 도구 (7종)
`kci_status` · `kci_search` · `kci_detail` · `kci_references` · `kci_journal_citation` · `kci_harvest` · `kci_collect`
`kci_collect` 은 요청 성격·키 유무로 REST↔OAI 자동 선택.
> 상세 조회 인자는 `arti_id`(KCI Control Number, 예: `ART003047608`).
>
> **알아둘 두 가지 (실측 확인)**
> - `articleSearch` 는 `keyword=` 로 **검색은 되지만 응답에 키워드·ISSN·UCI 를 싣지 않는다**.
>   검색 결과의 빈 `keywords` 는 '키워드 없는 논문'이 아니다 — 필요하면 `kci_detail` 로 건별 보강.
> - `kci_collect` 의 REST 경로는 각 검색어를 **제목축·키워드축 두 번** 조회해 합집합한다.
>   결과는 '제목검색 결과'가 아니라 제목∪키워드다. `meta.axes` 에 축별 `total` 이 담기고,
>   `max_records` 상한에 걸리면 `truncated: true` 와 경고 문구가 함께 온다.

## 자격증명 / 네트워크
- `KCI_API_KEY` (open.kci.go.kr 발급) → `.env`(gitignore) 또는 OS 환경변수. **커밋·로그 금지.** OAI는 키 불필요.
- KCI 방화벽은 **User-Agent 필터**를 건다(`curl` 기본 UA는 400 차단 안내페이지). 본 서버는 `requests` 로 호출하므로 정상.
- 교육망/사내망 **SSL 인터셉션**은 `truststore`로 OS 신뢰저장소를 사용해 통과(검증 유지). `KCI_OS_TRUST=0`로 비활성.

## 라이선스
MIT
