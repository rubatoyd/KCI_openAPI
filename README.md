# kci-openapi-mcp

<!-- mcp-name: io.github.rubatoyd/kci-openapi-mcp -->

한국연구재단(NRF) **KCI(Korea Citation Index)** 문헌·인용지수 검색·수집 **MCP 서버 + CLI**.
**REST Open API**(키워드 검색)와 **OAI-PMH**(무인증 대량 수확)를 **혼용**한다.
자매 프로젝트 scienceON-mcp(KISTI ScienceON)와 동일 아키텍처.

## 무엇을 하나
- 논문 검색·상세 (서지 · **국문/영문 초록** · 키워드 · 저자/소속)
- **OAI-PMH 대량 수확** (인증키 불필요 — 세트+날짜범위)
- 참고문헌 수집 — 원형 텍스트 + **피인용 논문의 KCI ID**(`arti-id`) → 인용 네트워크 구성 가능
- 저널 인용지수/등재이력 (REST 전용)
- 대량 수집 → xlsx / csv / json / sqlite

## 인증키 없이 30초 만에 써보기

**REST 검색만 인증키가 필요하고, OAI-PMH 대량 수확은 키가 없어도 됩니다.** 발급을 기다리는 동안에도
수집을 시작할 수 있습니다.

```bash
uvx --from git+https://github.com/rubatoyd/KCI_openAPI kci identify
# → KCI OAI 저장소 정보가 나오면 연결 정상 (키 불필요)

uvx --from git+https://github.com/rubatoyd/KCI_openAPI \
  kci harvest --set ARTI --from 2024-01-01 --until 2024-03-31 --contains 학부모 --max 200
```

MCP 로 붙였다면 `kci_status`(연결 점검) → `kci_harvest`(무인증 수확) 순서로 바로 쓸 수 있습니다.
키가 없으면 REST 도구들은 오류 대신 **OAI 대안을 안내**합니다.

## 두 인터페이스
| | REST Open API | OAI-PMH |
|---|---|---|
| 엔드포인트 | `…/po/openapi/openApiSearch.kci` | `…/oai/request` |
| 인증 | `KCI_API_KEY` 필요 | **불필요** |
| 질의 | 키워드 검색(title 필수) | 세트+날짜 대량 수확 |
| 인용지수·참고문헌 | ✅ | ❌ |
규격: [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md) · [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md) · 설계: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 현재 상태
- ✅ 구현·**REST/OAI 라이브 검증** 완료 · pytest 38 + MCP 프로토콜 스모크 · 도구 annotations
- ✅ **공식 MCP 레지스트리 발행됨**: `io.github.rubatoyd/kci-openapi-mcp`
- ✅ Claude Desktop **자체완결 `.mcpb`**(win/mac/linux, Python·uv 불필요) + Claude Code `.mcp.json`
- ⚠️ `mcp` SDK는 **1.x 고정**(`mcp>=1.2.0,<2`) — 2.0 에서 `mcp.server.fastmcp` 가 제거되어 상한 없이는 기동 실패

> **Claude 앱 안에서 검색해 설치할 수는 없습니다.** 공식 MCP 레지스트리 등재
> (`registry.modelcontextprotocol.io`)와 Claude Desktop **인앱 커넥터 디렉터리**는 별개이고
> 자동 동기화되지 않습니다. 인앱 노출은 Anthropic 디렉터리 심사를 별도로 통과해야 합니다
> (준비 현황 → [docs/DIRECTORY_SUBMISSION.md](docs/DIRECTORY_SUBMISSION.md)).
> 그때까지는 아래 **파일(.mcpb) 설치 · CLI 등록 · 수동 config** 중 하나를 쓰세요.

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

### 다른 MCP 클라이언트 (Claude 전용 아님)

**소스에 Claude 결합 코드가 없다.** 공식 MCP SDK 의 표준 **stdio** 서버이므로 MCP 를 지원하는
에이전트면 그대로 붙는다 — Cursor · Windsurf · Cline · Zed · VS Code Copilot(agent mode) ·
OpenAI Agents SDK · MCP Python/TS SDK 로 만든 자체 클라이언트 등.

등록 형태는 어디서나 같다. 클라이언트의 MCP 설정에 아래 3요소만 넣으면 된다.

```json
{
  "command": "uvx",
  "args": ["--from", "git+https://github.com/rubatoyd/KCI_openAPI", "kci-mcp"],
  "env": { "KCI_API_KEY": "<발급키 또는 비움>", "KCI_OS_TRUST": "1" }
}
```

Python 으로 직접 붙일 때(예: 자체 에이전트):
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="uvx",
    args=["--from", "git+https://github.com/rubatoyd/KCI_openAPI", "kci-mcp"],
    env={"KCI_API_KEY": "..."},   # 비워두면 OAI 무인증 도구만
)
```

**제약 2가지**
- **전송은 stdio 전용**이다(`mcp.run()` 기본값). 원격 HTTP/SSE 호스팅은 지원하지 않는다 —
  각 클라이언트가 로컬 서브프로세스로 띄우는 방식만 된다.
- 도구 설명(description)이 **한국어**다. 한국어를 다루는 모델이어야 도구 선택이 정확하다.

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
> **알아둘 것 (전부 실측 확인)**
> - `articleSearch` 는 `keyword=` 로 **검색은 되지만 응답에 키워드·ISSN·UCI 를 싣지 않는다**.
>   검색 결과의 빈 `keywords` 는 '키워드 없는 논문'이 아니다 — 필요하면 `kci_detail` 로 건별 보강.
> - `kci_collect` 의 REST 경로는 각 검색어를 **제목축·키워드축 두 번** 조회해 합집합한다.
>   결과는 '제목검색 결과'가 아니라 제목∪키워드다. `meta.axes` 에 축별 `total` 이 담기고,
>   `max_records` 상한에 걸리면 `truncated: true` 와 경고 문구가 함께 온다.
> - `kci_detail` 은 **참고문헌을 `arti_id`(피인용 논문의 KCI ID)와 함께** 반환한다
>   (`references`·`references_count`·`references_linked_count`). 이 ID 가 인용 네트워크를
>   구성할 수 있는 유일한 연결고리다. 단 **KCI 등재 참고문헌에만 붙는다** — 단행본·보고서·해외문헌은
>   빈 문자열이다(실측: 55건 중 19건 연결).
> - `kci_references` 는 `total`·`truncated` 를 함께 준다. ⚠️ 이 API 는 **page 파라미터가 없어
>   1회 100건이 상한**이라 절단분을 이어 받을 수 없다. 넘쳤다면 `sort_dir` 를 뒤집어(asc↔desc)
>   반대쪽 100건을 받아 합집합을 취하는 것이 유일한 우회책이며, 경고 문구가 그렇게 안내한다.
> - `kci_search`·`kci_references` 는 `institution`(발행기관) · `sort_by`(title/author/pubiYr) ·
>   `sort_dir`(asc/desc) 필터를 지원한다.

## 인증키 발급

REST 도구(`kci_search`·`kci_detail`·`kci_references`·`kci_journal_citation`)에만 필요합니다.
**OAI-PMH 수확은 키 없이 동작**하므로 급하지 않다면 발급 전에도 시작할 수 있습니다.

1. [open.kci.go.kr](https://open.kci.go.kr) 에서 **Open API 이용 신청**
2. 발급된 인증키 문자열 1개를 받는다
3. 아래 중 한 곳에 넣는다 — **코드나 커밋에는 절대 넣지 않는다**

| 사용 환경 | 넣는 곳 |
|---|---|
| Claude Code (프로젝트) | `.claude/settings.local.json` 의 `env` 블록 (gitignore 대상) |
| Claude Desktop | `claude_desktop_config.json` 의 `env` — **평문 인라인**(`${VAR}` 확장 안 됨) |
| `.mcpb` 설치 | 설치 시 뜨는 입력란 |
| CLI / 로컬 개발 | `.env`(gitignore) 또는 OS 사용자 환경변수 |

ScienceON(KISTI)과 달리 **AES 암호화·토큰 발급·공인 IP 등록이 전부 불필요**합니다. 평문 `key`
쿼리 파라미터 하나로 호출합니다.

## 자격증명 / 네트워크
- `KCI_API_KEY` → 위 표의 위치에만. **커밋·로그 금지.** OAI는 키 불필요.
- KCI 방화벽은 **User-Agent 필터**를 건다(`curl` 기본 UA는 400 차단 안내페이지). 본 서버는 `requests` 로 호출하므로 정상.
- 교육망/사내망 **SSL 인터셉션**은 `truststore`로 OS 신뢰저장소를 사용해 통과(검증 유지). `KCI_OS_TRUST=0`로 비활성.

## 라이선스
MIT
