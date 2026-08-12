# kci-openapi-mcp

<!-- mcp-name: io.github.rubatoyd/kci-openapi-mcp -->

한국연구재단(NRF) **KCI(Korea Citation Index)** 문헌·인용지수 검색·수집 **MCP 서버 + CLI**.
**REST Open API**(키워드 검색)와 **OAI-PMH**(무인증 대량 수확)를 함께 다룬다.

## 기능

- **논문 검색·상세** — 서지 · 국문/영문 초록 · 키워드 · 저자/소속
- **참고문헌 수집** — 원형 텍스트 + 피인용 논문의 KCI ID(`arti_id`) → 인용 네트워크 구성
- **저널 인용지수** — 연도별 IF · 등재이력
- **OAI-PMH 대량 수확** — 인증키 없이 세트 + 날짜범위 전수 수집
- **내보내기** — xlsx · csv · json · sqlite

## 두 인터페이스

| | REST Open API | OAI-PMH |
|---|---|---|
| 엔드포인트 | `…/po/openapi/openApiSearch.kci` | `…/oai/request` |
| 인증 | `KCI_API_KEY` 필요 | **불필요** |
| 질의 | 키워드 검색(`title` 필수) | 세트 + 날짜범위 수확 |
| 인용지수·참고문헌 | ✅ | ❌ |

규격: [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md) · [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md) · 설계: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 인증키 없이 바로 써보기

REST 검색만 인증키가 필요하고, OAI-PMH 수확은 키 없이 동작한다.

```bash
uvx --from git+https://github.com/rubatoyd/KCI_openAPI kci identify
```
```bash
uvx --from git+https://github.com/rubatoyd/KCI_openAPI kci harvest --set ARTI --from 2024-01-01 --until 2024-03-31 --contains 학부모 --max 200
```

MCP 로 붙였다면 `kci_status` → `kci_harvest` 순으로 바로 쓸 수 있다. 키가 없으면 REST 도구는
오류 대신 OAI 대안을 안내한다.

## 인증키 발급

REST 도구(`kci_search` · `kci_detail` · `kci_references` · `kci_journal_citation`)에만 필요하다.

1. [open.kci.go.kr](https://open.kci.go.kr) 에서 **Open API 이용 신청**
2. 발급된 인증키 문자열 1개를 받는다
3. 아래 중 한 곳에 넣는다 — 코드나 커밋에는 넣지 않는다

| 사용 환경 | 넣는 곳 |
|---|---|
| Claude Code | `.claude/settings.local.json` 의 `env` (gitignore 대상) |
| Claude Desktop | `claude_desktop_config.json` 의 `env` — 평문 인라인(`${VAR}` 확장 안 됨) |
| `.mcpb` 설치 | 설치 창의 입력란 |
| CLI / 로컬 개발 | `.env`(gitignore) 또는 OS 사용자 환경변수 |

AES 암호화·토큰 발급·공인 IP 등록은 불필요하다. 평문 `key` 쿼리 파라미터 하나로 호출한다.

## 설치

### Claude Desktop

**자체완결 `.mcpb`(권장)** — Python·uv 불필요. [릴리스](https://github.com/rubatoyd/KCI_openAPI/releases/latest)에서
OS에 맞는 파일을 받아 더블클릭(또는 Settings → Extensions → Install) → `KCI_API_KEY` 입력(선택).

| 자산 | 특징 |
|---|---|
| `kci-openapi-mcp-win-x64.mcpb` / `…-macos-arm64.mcpb` / `…-linux-x64.mcpb` | 자체완결 — 사전 설치물 없음 |
| `kci-openapi-mcp.mcpb` | 경량. 실행에 `uv` 필요 |

**수동 config** — `%APPDATA%/Claude/claude_desktop_config.json`:
```json
{ "mcpServers": { "kci": {
  "command": "uvx",
  "args": ["--from", "git+https://github.com/rubatoyd/KCI_openAPI", "kci-mcp"],
  "env": { "KCI_API_KEY": "<발급키 또는 비움>", "KCI_OS_TRUST": "1" }
} } }
```

### Claude Code

```bash
claude mcp add kci --env KCI_API_KEY=$KCI_API_KEY -- uvx --from git+https://github.com/rubatoyd/KCI_openAPI kci-mcp
```

프로젝트 루트의 `.mcp.json` 도 자동 인식된다.

### 다른 MCP 클라이언트

표준 stdio MCP 서버이므로 MCP 를 지원하는 에이전트면 그대로 붙는다 — Cursor · Windsurf · Cline ·
Zed · VS Code Copilot(agent mode) · OpenAI Agents SDK · 자체 클라이언트 등. 위 `command`/`args`/`env`
3요소를 각 클라이언트 설정에 옮기면 된다.

```python
from mcp import StdioServerParameters

params = StdioServerParameters(
    command="uvx",
    args=["--from", "git+https://github.com/rubatoyd/KCI_openAPI", "kci-mcp"],
    env={"KCI_API_KEY": "..."},   # 비우면 OAI 무인증 도구만
)
```

### 전송 방식

```bash
kci-mcp                                # stdio (기본)
kci-mcp --transport streamable-http    # http://127.0.0.1:8000/mcp
kci-mcp --transport sse --port 9000    # http://127.0.0.1:9000/sse
```

환경변수: `KCI_MCP_TRANSPORT` · `KCI_MCP_HOST` · `KCI_MCP_PORT`.

## MCP 도구

| 도구 | 하는 일 |
|---|---|
| `kci_status` | 연결 점검 — OAI Identify + 인증키 보유 여부 |
| `kci_search` | 논문 검색 — `title` 필수 + author/journal/keyword/abstract/doi/발행연월/institution 필터, 정렬 |
| `kci_detail` | Control Number(`ART…`)로 상세 — 키워드·ISSN·저자소속·**참고문헌**의 유일한 출처 |
| `kci_references` | 제목 검색어에 매칭된 논문들의 참고문헌 원형 |
| `kci_journal_citation` | 저널 인용지수 — 연도 목록 / `journal_id` 상세(등재이력·연도별 IF) |
| `kci_harvest` | OAI-PMH 무인증 대량 수확 — 세트 + 날짜범위, `contains` 로컬 필터 |
| `kci_collect` | 라우터 — 키 유무·요청 성격으로 REST↔OAI 자동 선택 후 파일 저장 |

## 알아둘 제한

**`articleSearch` 는 키워드·ISSN·UCI 를 응답에 싣지 않는다.** `keyword=` 로 검색은 되지만 결과에는
없다. 검색 결과의 빈 `keywords` 는 '키워드 없는 논문'이 아니다 — 필요하면 `kci_detail` 로 건별 보강한다.

**`kci_collect` 의 REST 경로는 제목축 ∪ 키워드축이다.** 각 검색어를 두 축으로 조회해 합집합을 만든다.
결과는 '제목검색 결과'가 아니므로 코퍼스 경계를 기술할 때 명시해야 한다. `meta.axes` 에 축별 `total` 이 담긴다.

**참고문헌의 `arti_id` 는 KCI 등재분에만 붙는다.** 단행본·보고서·해외문헌은 빈 문자열이다.
인용 네트워크는 이 ID 가 있는 항목으로만 구성할 수 있다(`references_linked_count` 로 확인).

**`referenceSearch` 는 페이지 파라미터가 없어 1회 100건이 상한이다.** 상한을 넘긴 분량은 이어 받을 수
없다. `sort_dir` 를 뒤집어(asc↔desc) 반대쪽 100건을 받아 합집합을 취하는 것이 유일한 우회책이다.

**KCI 가 보고하는 `total` 은 실제로 받을 수 있는 건수보다 클 수 있다.** 그래서 두 상황을 다른
플래그로 구분한다.

| 플래그 | 뜻 | 대처 |
|---|---|---|
| `truncated` | `max_records` 상한에 걸렸다 | 상한을 올려 재수집하면 늘어난다 |
| `total_mismatch` | 끝까지 페이징했는데 `total` 에 못 미쳤다 | 상한을 올려도 늘지 않는다. 회수량을 확정 수치로 쓴다 |

**다중 페이지 질의는 호출마다 결과가 미세하게 달라진다.** 단일 페이지 질의는 안정적이다.
`total` 에 못 미치고 상한도 아니면 한 번 더 훑어 합집합을 취한다(`meta.sweeps` 가 1보다 크면 보정된 것).
비용이 부담되면 `retry_incomplete=0` 으로 끈다.

**정렬 인자는 전송 전에 검증한다.** `sort_by` 는 `title`/`author`/`pubiYr`, `sort_dir` 은 `asc`/`desc`.
허용값 밖이면 오류를 돌려준다.

**Claude 앱 안에서 검색해 설치할 수는 없다.** 공식 MCP 레지스트리 등재와 Claude Desktop 인앱
커넥터 디렉터리는 별개이고 자동 동기화되지 않는다. 위 설치 방법 중 하나를 쓴다.

**도구 설명이 한국어다.** 한국어를 다루는 모델이어야 도구 선택이 정확하다.

**`mcp` SDK 는 1.x 로 고정된다**(`mcp>=1.2.0,<2`). 2.0 에서 `mcp.server.fastmcp` 가 제거되어
상한이 없으면 기동에 실패한다.

## CLI

```bash
kci identify                                  # OAI 무인증 — 키 없이 즉시
kci harvest --set ARTI --from 2024-01-01 --until 2024-12-31 --contains 학부모 --max 500
kci search --title 경계선지능 --rows 20        # REST(인증키 필요)
kci collect --config config/borderline_slow.yaml
```

로컬 개발은 `uv sync`. 클라우드 동기화 폴더(OneDrive 등)라면 venv 를 폴더 밖에 두기를 권한다
(`UV_PROJECT_ENVIRONMENT`).

## 네트워크

- KCI 방화벽은 **User-Agent 필터**를 건다. `curl` 기본 UA 는 차단 안내페이지를 받는다.
  본 서버는 `requests` 로 호출하므로 정상 동작한다.
- 교육망·사내망 **SSL 인터셉션** 환경에서는 `truststore` 로 OS 신뢰저장소를 사용해 통과한다
  (TLS 검증을 끄지 않는다). 비활성은 `KCI_OS_TRUST=0`.
- HTTP 전송에는 인증이 없다. 기본 바인드는 루프백(`127.0.0.1`)이다. `--host 0.0.0.0` 으로 외부에
  열면 인증키를 가진 서버가 그대로 노출되므로 신뢰된 망에서만 쓴다.

## 라이선스

MIT. 본 프로젝트는 한국연구재단의 비공식 클라이언트이며 제휴 관계가 없다.
KCI 데이터 이용은 KCI 약관을 따른다.
