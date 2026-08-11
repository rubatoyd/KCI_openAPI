# kci-openapi-mcp — 프로젝트 지침

> 한국연구재단(NRF) **KCI(Korea Citation Index)** 문헌·인용지수 검색·수집기.
> 공개 **MCP 서버 + CLI**. 자매 프로젝트 **scienceON-mcp**(`../scienceon`)와 동일 아키텍처.
> KCI는 **두 가지 공개 인터페이스**를 제공하며 본 프로젝트는 둘 다 다룬다:
> - **REST Open API**(키워드 검색형, 인증키 필요) → [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md)
> - **OAI-PMH**(대량 수확형, **인증키 불필요**) → [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md)

## 1. 목표
연구 초반 **자료수집 단계**에서 반복 재사용하는 도구. KCI에서 논문 서지·초록·참고문헌·저널
인용지수를 검색·수집해 후속 텍스트마이닝/계량서지 입력 데이터를 안정적으로 생산한다.
ScienceON(KISTI)과 **상호보완**: 수록 범위 교차검증, 국문 초록 백필, KCI 연구분야 분류·인용지수 확보.

## 2. 확정/계획 결정사항
| 항목 | 결정 |
|------|------|
| 언어/런타임 | Python 3.10+ |
| 패키지 관리 | **uv** (pyproject + uv.lock). venv는 **클라우드 폴더 밖** `C:/Users/user/.venvs/kci-openapi-mcp` (`UV_PROJECT_ENVIRONMENT`) |
| 의존성(계획) | mcp(FastMCP), requests, openpyxl, python-dotenv, pyyaml *(pycryptodome 불필요 — KCI는 토큰/AES 없음)* |
| 인터페이스 | 공용 코어 + **MCP 서버(server.py)** + **CLI(cli.py)** |
| 인터페이스(소스) | **REST**(openApiSearch.kci, 키 필요) + **OAI-PMH**(/oai/request, 무인증) — 둘 다 지원 |
| 수집 대상 | 논문(articleSearch/Detail) 우선 → 참고문헌(referenceSearch) → 저널 인용지수(citation/Detail) → OAI-PMH 대량수확 |
| 출력 | xlsx · csv · json · sqlite |
| 공개 | MIT 예정. `.env`·`reference/`·`output/`는 gitignore |

## 3. 구조 (scienceON-mcp 미러, 계획)
```
src/kci_mcp/
  config.py     # .env 로딩, Base URL/엔드포인트(REST + OAI)
  client.py     # REST GET / 페이징(page,displayCount≤100) / 재시도·throttle / 에러매핑
  oai_client.py # OAI-PMH GET(verb) / resumptionToken 루프 / 무인증
  parser.py     # XML 정규화 — REST(MetaData/outputData/record) + OAI(oai_dc/oai_kci), raw 보존
  models.py     # Article / Reference / JournalCitation 스키마(REST·OAI 공통)
  exporters.py  # xlsx/csv/json/sqlite (scienceON 재사용 가능)
  server.py     # MCP 도구 (아래 §5)
  cli.py        # status/search/detail/references/citation/harvest/collect
docs/
  KCI_API_GUIDE.md       # ★ REST API 명세 (PDF 복구본)
  KCI_OAI_PMH_GUIDE.md   # ★ OAI-PMH 명세 (PDF 복구본)
reference/
  KCI Open API Service 활용가이드.pdf   # 공식 원본 REST (gitignore, 비공개)
  KCI OAI-PMH 활용가이드.pdf            # 공식 원본 OAI-PMH (gitignore, 비공개)
config/         # 검색 설정 템플릿 (search.example.yaml)
```
> ※ 현재 폴더에는 **docs/(가이드 2종) + reference/(PDF 2종)만 마이그레이션 완료**. src/·config/·pyproject·mcpb는 개발 단계에서 생성.

## 4. 자격증명 (.env 또는 사용자 환경변수)
- 변수: `KCI_API_KEY` (KCI 발급 인증키 1개) — **REST API 전용**.
- 발급: open.kci.go.kr Open API 신청. **AES/토큰/공인IP 불필요** — 평문 key 쿼리 파라미터로 호출.
- **OAI-PMH는 무인증** — 키 없이 즉시 사용(`/oai/request`). 키 발급 전에도 OAI 검증·수집 가능.
- ⚠️ 인증키는 코드/로그/커밋 금지 — `.env`(gitignore) 또는 OS 사용자 환경변수로만.

## 5. MCP 도구 (계획) — scienceON 도구셋 대응
| 도구 | API | 설명 |
|------|-----|------|
| `kci_status` | (소량 articleSearch / OAI Identify) | 인증키 유효성·연결 점검 |
| `kci_search` | articleSearch | 논문 검색 — title 필수 + 필터 + 페이징 자동. `total`·`truncated` 동반 반환. ⚠️ **키워드·ISSN·UCI 미제공**(원본 XML 에 필드 없음) |
| `kci_detail` | articleDetail | Control Number(**`arti_id`**, 예 `ART003047608`)로 상세. **키워드·ISSN·등재여부·FWCI·저자소속·참고문헌의 유일한 출처** |
| `kci_references` | referenceSearch | 제목 검색어로 참고문헌 원형 수집 |
| `kci_journal_citation` | citation / citationDetail | 저널 인용지수(연도) / 상세(등재이력·연도별 IF) |
| `kci_harvest` | OAI-PMH ListRecords | **무인증** 세트+날짜범위 대량 수확(oai_kci, resumptionToken 자동) |
| `kci_collect` | **라우터**(REST↔OAI 자동) | 백엔드 자동 선택 → 정규화·중복제거 → xlsx/csv/json/sqlite. `meta.axes`(축별 total)·`truncated` 동반. ⚠️ REST 경로는 **제목축∪키워드축** 합집합 |

> **혼용 원칙**: REST/OAI를 공통 코어(models/parser/exporters) 위 두 클라이언트로 두고, `kci_collect`가
> 라우팅. 키 없으면 자동 OAI 경로, 인용지수·참고문헌은 REST 전용. 상세 라우팅표 → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 6. 핵심 기술사실 (PDF 기준, ⚠️ 라이브 미검증)
### (A) REST Open API
- **Base**: `https://open.kci.go.kr/po/openapi/openApiSearch.kci` (GET, 응답 XML/UTF-8)
- **5 apiCode**: articleSearch · articleDetail · referenceSearch · citation · citationDetail
- **필수키**: articleSearch/referenceSearch=`title`, articleDetail/citationDetail=`id`, citation=`year`+`years`(2~5)
- **페이징**: `page` + `displayCount`(기본10/최대100). 총건수 `outputData/result/total`
- **articleSearch 출력에 국문·영문 초록 포함** → ScienceON 결측 초록 백필원 후보(검증 필요)
- **인증**: 평문 `key`만. 토큰 발급/갱신 없음 (ScienceON 대비 대폭 단순)
- 에러: "등록되지 않은 key", "검색 조건이 없습니다"(title 0-length) 등 → [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md) §6

### (B) OAI-PMH (무인증 대량 수확)
- **Base**: `https://open.kci.go.kr/oai/request` (GET, `verb=`, OAI-PMH 2.0, XML/UTF-8)
- **6 verb**: Identify · ListSets · ListIdentifiers · ListMetadataFormats · ListRecords · GetRecord
- **세트**: ARTI(논문) · ARTI_CONF(학술대회) · JOUR(학술지) / **형식**: oai_dc(간략) · **oai_kci(상세·초록 포함)**
- **수집 모델**: `set`+`from/until`(YYYY-MM-DD) → `ListRecords`, **resumptionToken**으로 100건씩 전수 페이징
- **인증 불필요** — 키워드 검색은 불가(날짜범위 수확 후 로컬 필터). 상세 → [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md)

## 7. 개발 원칙
- 자격증명은 `.env`/MCP env 블록으로만. 로그·예외에 노출 금지.
- 정중한 호출: throttle(기본 0.5s), 지수 백오프, 페이지네이션 안전장치(새 record 0이면 종료).
- 원본 XML 필드는 `raw`로 보존. 커밋 메시지 한국어, Claude 서명 금지.
- **라이브 검증 우선(추정 금지)** — 인증키 발급 후 각 API 소량 호출로 응답 스키마 확정 → 가이드 "검증됨" 갱신.

## 8. 상태 (2026-08-11)
- ⚠️ **GitHub 계정명 변경 `rubato103` → `rubatoyd` (2026-08-11)** — Claude Desktop 의 `kci` 서버가
  `Failed to resolve --with requirement / Git operation failed` 로 3회 연속 기동 실패했다(11:04·11:10·11:11).
  `uvx --from git+…` 는 **기동할 때마다 원격 HEAD 를 재해석**하므로 저장소 주소가 곧 단일 장애점이다.
  `.mcp.json`·`claude_desktop_config.json`·`git remote`·메타데이터 전부 신주소로 갱신(해결, 콜드 스타트 재현 확인).
  GitHub 리다이렉트는 살아 있으나 의존하지 말 것. `docs/작업일지.md` 의 과거 기록은 사실이므로 보존.
- ⚠️ **MCP 등록 지점은 3곳이며 서로 독립이다** — ① 본 저장소 `.mcp.json`(Claude Code, 프로젝트 스코프)
  ② `%APPDATA%\Claude\claude_desktop_config.json`(Claude Desktop) ③ **`~/.claude.json`**(Claude Code
  **사용자 전역**, `projects.<경로>.mcpServers` 에 프로젝트별 local 스코프 등록). ①만 고치면 ③에 등록된
  타 프로젝트는 계속 깨진다. 실제로 `투고논문/학부모 학술동향` 의 `kci`·`scienceon` 이 구주소로 남아 있었다.
  ⚠️ `~/.claude.json` 은 **중복 키**(`c:/…` vs `C:/…` 경로)를 담고 있어 **JSON 파싱→재직렬화 금지**
  (한쪽이 조용히 소실된다). 원문 문자열 치환으로만 수정할 것.
- ⚠️ **레지스트리 네임스페이스 이관 필요** — `server.json` 을 `io.github.rubatoyd/kci-openapi-mcp` 로 변경.
  발행은 GitHub OIDC 로 계정 소유를 검증하므로 구 네임스페이스로는 더 이상 발행할 수 없다.
  기존 발행분(`io.github.rubato103/…` v0.1.3)은 고아로 남고, 다음 태그 푸시가 새 항목을 만든다.
- ✅ **파손된 프로젝트 내 `.venv/` 정리 완료 (2026-08-11)** — `pyvenv.cfg` 의 home 이 **다른 사용자 프로필**
  `C:\Users\rubat\…`(OneDrive 로 유입된 타 PC 산출물)를 가리켜 `uv run`·`uv lock` 이 exit 103 으로 실패했다.
  kci(3,156 파일)·scienceon(2,424 파일) 양쪽 삭제. MCP 동작에는 애초에 무관했다(uvx 격리환경 사용).
  §2 의 규약대로 **클라우드 폴더 밖** 환경을 쓰도록 `.claude/settings.local.json` 의 env 에
  `UV_PROJECT_ENVIRONMENT=C:/Users/user/.venvs/kci-openapi-mcp` 를 명시(scienceon 도 동일 처리).
  검증: `.venv/` 재생성 없이 pytest 31건 통과.
  ⚠️ 이 설정은 **Claude Code 세션에만** 적용된다. 사용자 터미널에서 `uv run` 하면 프로젝트 안에 `.venv/`
  가 다시 생긴다(`UV_PROJECT_ENVIRONMENT` 는 환경변수 전용 — pyproject/uv.toml 로는 지정 불가).

## 8-1. 이전 상태 (2026-08-04)
- ✅ 공식 PDF 2종 → `reference/`(원본) + `docs/`(복구 명세 2종) 마이그레이션 완료.
- ✅ **`src/kci_mcp/` 구현 완료** — config/models/parser/oai_client/client/router/exporters/server/cli.
- ✅ **OAI-PMH 라이브 검증 완료**(무인증): Identify/ListSets/Formats/ListRecords(oai_kci·oai_dc)/GetRecord.
  검증 메모 → [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md) §10.
- ✅ **REST 라이브 검증 완료 (2026-08-04)** — MCP 프로토콜(stdio)로 7개 도구 전수 실호출 성공:
  `kci_status` / `kci_search`(초록 포함) / `kci_detail`(`arti_id=ART003047608`, `사회과학 > 교육학`) /
  `kci_references` / `kci_journal_citation`(2023년 50저널, `impactFactor`·`exImpactFactor`·`selfCitedRate`) /
  `kci_harvest` / `kci_collect`(라우터 `rest` 선택 → xlsx·json 산출). → §6 "라이브 미검증" 단서 해소.
- ⚠️ **`mcp` SDK 상한 필수** — 2.0.0 에서 `mcp.server.fastmcp` 제거(→ `mcp.server.MCPServer` 체계).
  상한 없는 `mcp>=1.2.0` 은 2.0 으로 해석되어 `uvx --from git+…` 기동이 `ModuleNotFoundError` 로 실패했다.
  `pyproject.toml`·`uv.lock` 에 `>=1.2.0,<2` 고정(해결). `.mcpb` 번들·로컬 `.venv` 는 영향 없었음.
- ⚠️ **KCI 방화벽은 User-Agent 필터** — `curl` 기본 UA 는 HTTP 400 "차단" 안내페이지 반환(해외 IP 문구이나
  실제 조건은 UA). `requests` UA 는 200. 즉 클라우드/원격 환경에서도 REST·OAI 모두 정상 동작한다.
- ✅ **v0.1.3 — 조용한 절단 제거**: `search_meta`/`search_terms_meta` 신설로 축별 `total`·`fetched`·
  `truncated`·`union_upper_bound` 를 반환. `kci_search`/`kci_collect` 가 상한에 걸리면 경고 문자열을 붙인다.
  기존 `search`/`search_terms` 는 얇은 래퍼로 남겨 호출부 호환 유지. 회귀 테스트 7건 추가(총 31 통과).
- ⚠️ **articleSearch 는 키워드·ISSN·UCI 를 제공하지 않는다**(원본 XML 필드 부재 — 파서 문제 아님).
  `keyword=` 로 **검색은 되지만** 결과에는 실리지 않는 비대칭. 키워드는 `articleDetail` 에만 있으므로
  STM 토픽 라벨링용 키워드가 필요하면 건별 `kci_detail` 보강 패스가 전제 조건이다.
- ⚠️ **`search_terms` 의 기본 `fields=("title","keyword")` = 두 축 합집합** — 결과는 '제목검색 결과'가
  아니다. 코퍼스 경계를 기술할 때 반드시 명시할 것.
- ⏭️ 다음: ① `kci_collect` 혼용 교차검증·초록 백필을 학부모 코퍼스에 적용 → ② `.mcpb` 재빌드·릴리스 태그 갱신.
- ⚠️ **교육망(학교/교육청)·사내망 SSL 인터셉션** 대응: `truststore` 의존성으로 **OS 신뢰저장소** 사용
  (검증 끄지 않음). `KCI_OS_TRUST=0` 로 비활성 가능.
- 🔗 연계 연구: `투고논문/학부모 학술동향` (ScienceON 621편 STM 분석) — KCI는 초록 백필·완전성 교차검증원.
