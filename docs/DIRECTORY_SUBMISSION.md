# Anthropic 디렉터리 제출 초안 (copy-paste ready)

> Claude Desktop 커넥터/익스텐션 **디렉터리 등재 신청 폼**에 붙여넣을 내용 초안.
> 폼 항목명은 다를 수 있으니, 아래 블록을 해당 칸에 맞춰 사용하세요. 리뷰어는 영어권일 가능성이 높아
> 제출 본문은 **영어**로 작성했고, 사용자용 한글 안내는 〔 〕 로 표시했습니다.
> 제출물 파일은 **자체완결 `.mcpb`**(Python·uv 불필요)를 사용하세요 — [릴리스](https://github.com/rubatoyd/KCI_openAPI/releases/latest).

---

## 1. Basic information 〔기본정보〕
- **Extension name (id):** `kci-openapi-mcp`
- **Display name:** KCI Citation Search (한국학술지인용색인)
- **Version:** 0.1.3
- **Category:** Research / Academic & Reference / Data
- **Author / Publisher:** Yeondong Yang (GitHub: rubatoyd)
- **Contact email:** rubato103@gmail.com
- **Repository:** https://github.com/rubatoyd/KCI_openAPI
- **Homepage / Docs:** https://github.com/rubatoyd/KCI_openAPI#readme
- **License:** MIT
- **MCP Registry name:** `io.github.rubatoyd/kci-openapi-mcp`
- **Submission artifact (.mcpb):** self-contained, per-OS — `kci-openapi-mcp-win-x64.mcpb` / `-macos-arm64.mcpb` / `-linux-x64.mcpb` (no runtime prerequisite)

## 2. Short description 〔한 줄 설명〕
> Search and collect Korean scholarly literature — bibliographic records, Korean/English abstracts, references, and journal citation metrics — from the Korea Citation Index (KCI).

## 3. Long description 〔상세 설명〕
> kci-openapi-mcp connects Claude to the **Korea Citation Index (KCI)**, the national academic citation database operated by the National Research Foundation of Korea (NRF). It lets you search Korean scholarly articles, retrieve full bibliographic records with Korean/English abstracts, keywords and author affiliations, collect reference lists, and look up journal citation metrics (impact factor, registration history). It also supports keyless bulk metadata harvesting via OAI-PMH, and exports results to xlsx/csv/json/sqlite for downstream text mining and bibliometric analysis.
>
> It combines KCI's two public interfaces — the **REST Open API** (keyword search; requires a free API key from open.kci.go.kr) and **OAI-PMH** (keyless bulk harvesting) — and routes each request to the appropriate backend automatically. Typical users are researchers building literature corpora, cross-validating database coverage, and back-filling Korean-language abstracts.

## 4. Tools 〔도구 7종 — 동작·권한·데이터접근〕
| Tool | What it does | Read-only | Auth | Data accessed / sent |
|---|---|:--:|:--:|---|
| `kci_status` | Connectivity check (OAI Identify + whether a REST key is set) | ✅ | none | KCI OAI endpoint |
| `kci_harvest` | Bulk-harvest metadata by set + date range (OAI-PMH), optional local keyword filter | ✅ | **none** | KCI OAI endpoint |
| `kci_search` | Search articles by title/author/journal/keyword/abstract/DOI/date | ✅ | API key | KCI REST endpoint; query terms sent to KCI |
| `kci_detail` | Article detail (abstract, keywords, authors) by control number | ✅ | API key | KCI REST endpoint |
| `kci_references` | Reference lists of articles matching a title query | ✅ | API key | KCI REST endpoint |
| `kci_journal_citation` | Journal impact factor / registration history | ✅ | API key | KCI REST endpoint |
| `kci_collect` | Router (REST↔OAI) → dedupe → **export to local file** (xlsx/csv/json/sqlite) | ✍️ writes files (non-destructive) | optional | KCI endpoints; writes to user's local disk |

All tools are annotated (`readOnlyHint`, `openWorldHint`); only `kci_collect` writes data, and only by creating export files locally (it never deletes or modifies existing data).

## 5. Authentication & credentials 〔인증·자격증명〕
> The REST tools use a single optional API key (`KCI_API_KEY`), issued free at open.kci.go.kr (no token/OAuth). The OAI-PMH tools (`kci_status`, `kci_harvest`) need **no key**. The key is entered through Claude Desktop's user-config (marked `sensitive`), passed to the server only via an environment variable, and is **never written to logs, tool responses, or error messages** (the server strips key-bearing URLs from exceptions). It is sent only to KCI's own endpoint as the API's required query parameter.

## 6. Privacy & data handling 〔개인정보·데이터 처리〕
> This extension collects **no analytics or telemetry** and sends data to **no third party**. The only network destinations are KCI's public endpoints (`open.kci.go.kr`) over HTTPS:
> - REST: `https://open.kci.go.kr/po/openapi/openApiSearch.kci`
> - OAI-PMH: `https://open.kci.go.kr/oai/request`
>
> User-provided search terms are sent to KCI to perform the search. Any API key, if set, is sent only to KCI. Export files (from `kci_collect`) are written to the user's local disk (default `~/kci-output`, or a path the user specifies). TLS certificate verification is always enabled; on TLS-inspecting networks the OS trust store is used (`truststore`) rather than disabling verification. Source is open (MIT) and auditable.

## 7. Reviewer test plan 〔리뷰어 테스트 — 키 없이도 검증 가능〕
**No API key required (verify core functionality immediately):**
1. `kci_status` → returns OAI repository info (`repositoryName: "KCI (Korea Citation Index) Open Access Repository"`, `has_api_key`).
2. `kci_harvest` with `{ "set_spec": "ARTI", "date_from": "2024-12-02", "date_until": "2024-12-02", "max_records": 3 }` → returns up to 3 article metadata records (title, authors, abstract, doi).
3. `kci_collect` with `{ "set_spec": "ARTI", "date_from": "2024-12-02", "date_until": "2024-12-02", "max_records": 3 }` → harvests via OAI and writes xlsx/csv/json; returns file paths + `backend: "oai"`.

**API-key tools (free key from open.kci.go.kr → set `KCI_API_KEY`):**
4. `kci_search` with `{ "title": "경계선지능", "rows": 5 }` → returns matching articles with Korean/English abstracts.
5. `kci_detail` with `{ "arti_id": "ART002358582" }` → returns one article's full detail.

With no key, key-required tools return a graceful `{ "error": "KCI_API_KEY 미설정 …" }` (no crash) and suggest the keyless `kci_harvest` path.

## 8. Safety & policy compliance 〔정책 준수〕
- No destructive operations; no system/file modification beyond user-initiated exports (`kci_collect`).
- No arbitrary code execution; no shell-out; only HTTPS calls to KCI public endpoints.
- Credentials handled securely (env-only, `sensitive`, never logged/echoed; key-bearing URLs stripped from errors).
- Every tool returns a JSON-serializable result and never leaks exceptions to the protocol.
- Self-contained binary `.mcpb` (PyInstaller) — no external runtime/install required; verified to start and serve tools on a clean machine.
- Open source (MIT), reproducible build (`.github/workflows/build-mcpb.yml`).

## 9. Support 〔지원〕
- Issues: https://github.com/rubatoyd/KCI_openAPI/issues
- Maintainer: rubato103@gmail.com

---

### 제출 체크리스트 〔사용자용〕
- [ ] 위 1~9 내용을 폼 해당 칸에 붙여넣기
- [ ] 제출 파일: 자체완결 `.mcpb`(릴리스 자산) 업로드 또는 릴리스 URL 제공
- [ ] (요청 시) 테스트용 무인증 경로(§7 1~3) 안내 — 리뷰어가 키 없이 검증 가능
- [ ] 제출 후 리뷰 피드백 오면 SUBMISSION.md 체크리스트와 대조해 보완
