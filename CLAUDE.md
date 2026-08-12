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

## 7-1. 자매 프로젝트 `nl-openapi-mcp` 세션에서 이관된 교훈 (2026-08-12)

> 국립중앙도서관 MCP 를 만들며 결함 11종을 잡았다(적대적 검증 4 · 라이브 실측 2 · 코드 리뷰 5).
> 그중 **이 저장소에도 해당하는 것**만 옮긴다. 이 저장소의 관례대로 "한쪽에서 고친 결함은
> 다른 쪽에도 있다고 가정하고 확인"했고, **확인 결과를 함께 적는다.**

### 🔴 확인된 결함 — 출력 파일 경로 이탈 (미수정)
`kci_collect` 의 `nm = (name or …).replace(" ", "_")[:60]` 와 `exporters.export` 의
`out / f"{name}{ext}"` 조합은 **`out_dir` 밖에 파일을 쓸 수 있다.** 실제로 재현했다:

```
name="../escaped"  → C:\…\Temp\<tmp>\escaped.json     ← out_dir 밖
name="..\esc2"     → C:\…\Temp\<tmp>\esc2.json        ← out_dir 밖
name="sub/dir/x"   → FileNotFoundError (조용한 실패)
```

`name` 은 MCP 도구 인자이고, 미지정 시 **검색어가 그대로 파일명이 된다** — 사용자 입력이
경로에 직접 닿는다. nl 쪽 처방: `exporters.safe_name()` 을 만들어 호출부마다가 아니라
**`export()` 한 곳에서** 정규화하고(경로 구분자·`..`·제어문자·Windows 예약명·후행 점),
최종 경로가 `out_dir` 안인지 `resolve()` 로 **이중 확인**한다. ⏭️ 이 저장소는 아직 미적용.

### 적대적 검증은 **실제 HTTP 왕복**으로 해야 한다
`_call` 을 monkeypatch 하는 테스트는 **전송·인코딩 감지·재시도/백오프·URL 파라미터 인코딩
계층을 통째로 건너뛴다.** nl 에서는 로컬 `ThreadingHTTPServer` 를 띄워 실제 소켓으로
반복 호출(검사 9,282건)했더니 그 층에서만 결함 4종이 나왔다 — `_call` 스텁으로는 하나도
안 잡혔을 것들이다. ⏭️ 이 저장소 테스트에도 실제 HTTP 왕복 하네스가 없다(확인함).

### 경고 문자열은 **안전장치인데 테스트가 잘 닿지 않는다**
nl 에서 분할 수집 경고가 **잘못된 키 이름 하나** 때문에 한 번도 출력되지 않았다.
'전수가 아니다'를 알리는 문장이 사라져, 조용한 절단을 막겠다는 프로젝트 목적이
정면으로 무너졌는데도 테스트는 전부 통과했다. **경고 문구도 회귀로 고정할 것.**

### 방법론 3가지 (이 저장소에도 그대로 적용)
- **대리 지표를 결론으로 쓰지 말 것.** nl 에서 '오탐률 52%'를 근거로 구문검색을 기본값으로
  올리려 했는데, 그 지표는 *제목에 문자열이 있는가* 였지 *주제가 무관한가* 가 아니었다.
  실제로 버려지는 레코드를 눈으로 보니 76%가 관련 문헌이었고 결론이 정반대가 됐다.
- **부재 증명에는 대조군이 필요하다.** "`author` 검색이 0건이니 미지원"이라고 단정했는데,
  주제어로 저자를 검색했으니 0건이 당연했다. 실제 저자명으로 다시 재니 정상 동작했다.
- ⚠️ **자매 프로젝트의 *API 사실* 을 이식하지 말 것.** nl 문서에 "검색식에 OR 연산자가 없다"고
  적었는데, 이는 KCI 에서 검증된 사실을 근거 없이 옮긴 것이었다(결과적으로 맞았으나 근거가
  없었다). **방법론은 옮기되 API 동작은 각자 실측한다** — 이 절도 그 원칙에 따라
  "이 저장소에서 확인한 것"만 적었다.

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
- ✅ **레지스트리 네임스페이스 이관 완료 (v0.1.4, 2026-08-11)** — 발행이 GitHub OIDC 로 계정 소유를
  검증하므로 구 네임스페이스로는 더 이상 발행할 수 없었다. `server.json` 을
  `io.github.rubatoyd/kci-openapi-mcp` 로 바꾸고 `v0.1.4` 태그 푸시 → 워크플로 전 단계 통과.
  레지스트리 실조회 확인: `io.github.rubatoyd/kci-openapi-mcp v0.1.4 status:active`.
  구 항목 `io.github.rubato103/…` v0.1.0~v0.1.3 은 **active 상태로 고아로 남는다**(회수 불가).
  릴리스 자산 4종(경량 + win/macos/linux 자체완결) 첨부 확인.
  ✅ **자체완결 바이너리(win-x64) 런타임 재검증** — 릴리스 자산을 내려받아 **클린 환경**
  (`env -i`, PATH=system32 만, Python·uv 없음)에서 `kci_status` 실호출 성공.
  OAI Identify **실제 네트워크 왕복**까지 확인(truststore 주입 실패 경고 없음).
  ※ `has_api_key:true` 로 나온 것은 `config.load_dotenv()` 가 **cwd 의 `.env`** 를 읽기 때문이다
  (env 를 비워도 cwd 가 프로젝트면 키가 잡힌다). 클린 검증 시 이 점을 감안할 것.
- ✅ **파손된 프로젝트 내 `.venv/` 정리 완료 (2026-08-11)** — `pyvenv.cfg` 의 home 이 **다른 사용자 프로필**
  `C:\Users\rubat\…`(OneDrive 로 유입된 타 PC 산출물)를 가리켜 `uv run`·`uv lock` 이 exit 103 으로 실패했다.
  kci(3,156 파일)·scienceon(2,424 파일) 양쪽 삭제. MCP 동작에는 애초에 무관했다(uvx 격리환경 사용).
  §2 의 규약대로 **클라우드 폴더 밖** 환경을 쓰도록 `.claude/settings.local.json` 의 env 에
  `UV_PROJECT_ENVIRONMENT=C:/Users/user/.venvs/kci-openapi-mcp` 를 명시(scienceon 도 동일 처리).
  검증: `.venv/` 재생성 없이 pytest 31건 통과.
  ⚠️ 이 설정은 **Claude Code 세션에만** 적용된다. 사용자 터미널에서 `uv run` 하면 프로젝트 안에 `.venv/`
  가 다시 생긴다(`UV_PROJECT_ENVIRONMENT` 는 환경변수 전용 — pyproject/uv.toml 로는 지정 불가).

- ℹ️ **기동 시 stderr 경고는 무해하다(오진 주의)** — 두 서버 모두 매 기동마다 다음을 찍는다:
  `pydantic_settings … IncompleteFieldDefinitionWarning: Field 'lifespan' has an incomplete definition`.
  **pydantic-settings 2.14 에서 새로 생긴 경고**이고 대상은 mcp SDK 의 FastMCP `Settings` 모델이다
  (우리 코드가 아니다). `pydantic-settings<2.14` 를 쓰면 사라지는 것을 실측 확인했으나 **핀하지 않는다**
  — 우리가 직접 쓰지 않는 전이 의존성을 묶으면 상류가 고친 뒤에도 사용자를 낡은 버전에 잡아두게 된다.
  MCP 로그에서 이 두 줄은 무시하고 `Server disconnected` / `Git operation failed` 같은 실제 오류만 볼 것.

- ⚠️ **액션 버전 표기: 이동 태그가 있는 것과 없는 것을 구분할 것 (2026-08-11 실패로 학습)** —
  Node.js 20 deprecation 해소를 위해 액션들을 상향했다(checkout→v7, setup-python→v7,
  upload-artifact→v7, download-artifact→v8, setup-node→v7, node-version 20→24).
  `actions/*` 는 **이동 메이저 태그**(`v7` 등)를 유지하므로 메이저만 써도 된다. 그러나
  **`astral-sh/setup-uv` 는 v7 이후 이동 태그를 내지 않는다**(`v5`·`v6`·`v7` 존재, `v8`·`v9` 없음).
  `@v9` 로 썼다가 CI 가 `Unable to resolve action … unable to find version v9` 로 즉시 실패했다
  → `@v9.0.0` 정확 고정으로 해결. **상향 전 `gh api repos/<owner>/<repo>/git/ref/tags/<tag>` 로
  태그 실존을 확인할 것.** 릴리스 워크플로는 태그를 밀어야만 실행되므로 이 실수가 거기 있으면
  다음 릴리스에서야 터진다(이번엔 전수 확인해 `actions/*` 는 모두 정상임을 확인).
  아티팩트 액션은 **v4+ 끼리 호환**이므로 upload@v7 ↔ download@v8 조합에 문제 없다(v3 이하만 미지원).
  ✅ **릴리스 경로 실검증** — `build-mcpb.yml` 을 `workflow_dispatch`(tag=v0.1.4)로 돌려 3개 OS
  전부 통과, **annotation 0건**(deprecation 해소 확인). 재빌드 자산으로 교체되었으나 경량
  `kci-openapi-mcp.mcpb` 는 이 워크플로가 건드리지 않으므로 **레지스트리 `fileSha256` 은 유효**하다.
  재빌드 바이너리를 내려받아 **cwd 까지 프로젝트 밖으로 뺀 클린 조건**에서 `kci_status` 실행 →
  `has_api_key:False`(= `.env` 미로딩으로 위 가설 실증) + **OAI Identify 네트워크 왕복 성공**.
  ※ `upload/download-artifact`·`setup-node` 는 이 워크플로가 쓰지 않아 미검증 — 다음 릴리스에서 확인된다.

- ✅ **명세에 있으나 흘려버리던 정보 4종 구현 (2026-08-11)** — 연구 쪽(`투고논문/교육불평등 지도`)에서
  MCP 로는 안 돼 외부 스크립트로 우회하던 것들이다.
  ① **`articleDetail` 의 `<referenceInfo>`** — 논문별 참고문헌을 `arti-id`(KCI 논문 ID)와 함께 준다.
     **인용 네트워크를 구성할 수 있는 유일한 연결고리**인데 파서가 통째로 버리고 있었다.
     `kci_detail` 이 `references`·`references_count`·`references_linked_count` 를 반환한다.
     ⚠️ **원소명이 API 오타다** — `pubi-year`·`isseue`·`pubilisher`. 정상 철자로 추정하면 값이 빈다.
     ⚠️ `arti-id` 는 KCI 등재분에만 붙는다(실측: 55건 중 19건). 나머지는 텍스트뿐.
  ② **`referenceSearch` 의 `total`** — 세 번째 '조용한 절단'이었다. 실측 total 191건인데 50건만
     회수돼도 표시가 없었다. `total`·`truncated`·경고 반환. ⚠️ 이 API 는 **page 파라미터가 없어
     1회 100건이 상한**이라 절단분을 이어 받을 수 없다 — `sort_dir` 를 뒤집어 반대쪽을 받는 게 유일한 우회책.
  ③④ **`institution`·`sortNm`·`sortDir`** — 클라이언트는 `**filters` 로 이미 통과시켰으나 MCP 도구가
     노출하지 않았다. `kci_search`·`kci_references` 에 `institution`·`sort_by`·`sort_dir` 추가.
  검증: 라이브 4종 전수 + 오프라인 회귀 7건(총 38 통과). 명세 복구본 §2-2 도 보완.
- ⏳ **인증키 내장은 보류** — "이용제한 없는 키이니 MCP 에 내장" 요청이 있었으나, 주 배포 경로가
  `uvx --from git+<공개 저장소>` 라 내장 = **공개 저장소 커밋**이고 git 이력에 영구히 남는다.
  클라이언트 측 암호화는 복호화 코드가 같이 배포되므로 보호가 되지 않는다(난독화일 뿐).
  모든 호출이 키 발급자 계정에 귀속되는 문제도 있다. **KCI 측에 키 공개 가능 여부를 확인한 뒤 결정**하기로
  했다(2026-08-11). 그때까지 §4 규칙(키는 코드/커밋 금지) 유지.

- ✅ **전송 선택 추가 — Claude 전용 탈피 (2026-08-11)** — `mcp.run()` 이 인자 없이 호출돼 **stdio 전용**
  이었다. `main()` 에 `--transport stdio|sse|streamable-http` + `--host`/`--port` 를 붙여 HTTP 로도
  띄운다(환경변수 `KCI_MCP_TRANSPORT`/`_HOST`/`_PORT` 도 지원). 소스에 Claude 결합 코드는 원래 없었으므로
  이로써 원격 호스팅·비 stdio 클라이언트까지 열린다.
  ⚠️ **기본값은 stdio 로 못박아 둘 것** — 기존 등록은 인자 없이 서버를 띄우므로 기본이 바뀌면
  모든 사용자의 MCP 가 한 번에 죽는다. 회귀 테스트로 고정했다.
  ⚠️ **HTTP 전송에는 인증이 없다.** 기본 바인드는 루프백. 외부 노출은 인증키를 공개하는 것과 같아
  기동 시 경고를 찍는다. 미지의 CLI 인자·비숫자 포트 환경변수는 서버를 죽이지 않고 무시한다.
  검증: stdio 회귀 + `streamable-http` 실기동(HTTP 200, initialize 응답) + 테스트 46종.

- 🔬 **적대적 검증에서 결함 4종 발견·수정 (2026-08-11)** — 실제 반복 호출로 도구가 *주장하는 값*이
  실제와 맞는지 깨보았다. 계약 위반(예외 누수·비 dict)은 없었으나 **오보 3종 + 데이터 결손 1종**이 나왔다.
  ① 🔴 **`truncated` 오탐** — `fetched < total` 하나로 판정해, 페이징을 끝까지 돌았는데도 True 가 떴다
     (실측 '교육격차' 205/204, '학부모' 4766/4645, 중복제거 0건). KCI 의 total 은 **실제 서빙량보다 클 수
     있다.** 그때 "max_records 를 올리라"는 경고는 **올려도 해결 안 되는 틀린 처방**이었다.
     → `truncated`(우리 상한)와 `total_mismatch`(API total 불일치)를 **분리**하고 조언을 달리한다.
  ② 🔴 **`rows<=0` 이 total 을 감춤** — `displayCount=0` 이면 KCI 가 total 까지 0 으로 준다. 205건이
     존재하는데 "결과 없음"으로 보고됐다. → 요청 크기 하한 1 로 클램프(반환 건수는 요청대로 0).
  ③ 🔴 **다중 페이지 질의의 결과 불안정** — 동일 조건 3회에 회수량 204/204/205, 레코드 합집합 205·
     교집합 203(2건이 호출마다 오감). **단일 페이지 질의는 완전 안정.** 코퍼스 재현성에 직결된다.
     → `retry_incomplete=1`(기본): total 미달이고 상한도 아니면 **한 번 더 훑어 합집합**.
     실측 off=204/204/204 고정 → on=**205/205/205 완전 회수**. `meta.sweeps` 로 보정 여부 노출.
     비용: 불일치일 때만 재페이징(대형 질의는 요청 2배) — 끄려면 `retry_incomplete=0`.
  ④ 🟡 **잘못된 정렬값의 증상이 서로 다름** — `sort_dir=sideways` → **HTTP 500**,
     `sort_by=pubYear`(pubiYr 오타) → **조용히 무시**되어 정렬한 줄 안다. → 전송 전 enum 검증.
  ℹ️ 부수 확인: 한자 검색(`敎育格差`)은 국문과 사실상 같은 결과(KCI 가 정규화), 제목 500자는 HTTP 500.
  회귀 테스트 3 → 51건(KCI). ⚠️ 모킹 테스트는 `throttle=0` 필수 — 실제 대기를 넣으면 스위트가 210초가 된다.

- 🔬 **코드 리뷰 지적 6종 반영 (2026-08-11)** — 리뷰 전용 PR#1 을 만들어 세션 내 리뷰 +
  `/code-review ultra`(다중 에이전트, PR 코멘트로 회신) 두 경로를 돌렸다. **두 리뷰가 상호 보완적**이었다.
  ① 🔴 **`kci_search` 가 `meta["truncated"]` 를 버리고 옛 공식으로 재계산** — client 에서 없앤
     `fetched < total` 오탐이 도구 계층에 되살아나 있었다. `total_mismatch`·`notice` 도 미노출.
     → meta 플래그를 그대로 쓰고 두 상황을 구분해 안내한다. **(양쪽 리뷰가 동시 지적)**
  ② 🔴 **`retry_incomplete` 가 문서에만 있고 도달 불가** — `search_terms_meta` 가 인자를 받지도
     전달하지도 않아 어떤 도구로도 끌 수 없었다. → 인자를 뚫고 `kci_collect` 에 노출. **(세션 리뷰만)**
  ③ 🟡 **`kci_references` 경고가 두 상한을 혼동** — `total ≤ 100` 인데 `rows` 로 자른 경우에도
     "sort_dir 를 뒤집으라"고 안내했다. **API 는 이미 전량을 줬으므로 뒤집어도 같은 레코드**가 온다.
     올바른 처방은 rows 상향. `api_capped` 로 분기. **(ultra 만 — 가장 값진 지적)**
  ④ 🟡 **정렬 인자를 소문자로 검증하고 원본을 전송** — `sort_dir="ASC"` 가 검증 통과 후 대문자로
     나갔다. 검증기가 자기 위협 모델을 통과시킨 셈. → `_norm_sort` 로 검증·정규화를 한 곳에서.
  ⑤ 🟡 하한 클램프가 `search_meta` 에만 적용 → `references_meta`·`citation` 에도 적용.
  ⑥ 🟢 재시도 루프 중복 조건 제거, `sweeps_total` 집계 추가.
  ⚠️ **지적 6건이 전부 도구 계층인데 그 계층 테스트가 없었다** — 클라이언트 테스트를 다 통과하면서
  새어나갔다. `tests/test_server_tools.py` 신설(60종). scienceON 에는 있던 것이 kci 에만 없었다.

- 🔬 **scienceON 리뷰의 공통 지적 반영 (2026-08-11)** — 자매 프로젝트 PR 리뷰에서 나온 7건 중
  이쪽에도 해당하는 것을 확인해 고쳤다. **한쪽에서 나온 지적은 반대쪽도 확인한다**는 규칙의 적용.
  ① **마지막 축이 상한을 채우면 `stopped_early` 오탐** — 남은 축이 없는데 조기 중단으로 표시돼
     전수 수집한 코퍼스에 절단 경고가 붙었다. `term is terms[-1] and field is fields[-1]` 로 판정.
  ② `search_meta` docstring 이 옛 판정(`truncated: fetched < total`)을 설명 → 실제 스키마로 갱신.
  ③ `__version__` 이 `0.1.3` 으로 방치(실제 0.3.x) → `importlib.metadata` 조회로 변경.
  ④ **한 겹 더 깊은 오탐** — `max_records` 가 실제 `total` 과 같으면 전부 회수했는데도 `hit_cap` 이
     True 였다. `hit_cap = 상한도달 and fetched < total` 로 정정. **테스트를 쓰다가 발견했다.**
  ⑤ 전 모듈 임포트 테스트 추가(`cli.py` 처럼 어떤 테스트도 임포트하지 않는 모듈이 있었다). 60 → **72**.
  ℹ️ 자격증명 유출(scienceON 최우선 지적)은 **kci 에는 해당 없다** — `raise_for_status()` 가
  키 포함 URL 을 메시지에 넣는다는 것을 알고 처음부터 피했고 주석으로 남겨두었다.

- 🔴 **출력 경로 이탈 차단 (2026-08-11)** — 세 번째 자매 프로젝트 `nl-openapi-mcp` 에서 발견돼
  이쪽에서도 **그대로 재현**됐다. `export()` 가 `out_dir / f"{name}{ext}"` 를 쓰는데 `name` 은
  `.replace(" ", "_")[:60]` 만 거쳐 경로 구분자·`..` 가 통과했다.
  ```
  name="../escaped" → …\Temp\<tmp>\escaped.json     ← out_dir 밖
  name="..\esc2"    → …\Temp\<tmp>\esc2.json        ← out_dir 밖
  name="sub/dir/x"  → FileNotFoundError (조용한 실패)
  ```
  ⚠️ **`name` 은 MCP 도구 인자이고 미지정 시 검색어가 그대로 들어온다** — 사용자 입력이 파일
  경로에 직접 닿는다. `exporters.safe_name()` 신설(경로 성분·`..`·제어문자·윈도 예약명·후행 점
  제거)하고 **`export()` 한 곳에서** 적용한다(호출부마다 고치면 새 호출부에서 또 샌다).
  최종 경로가 `out_dir` 안인지 `resolve()` 로 이중 확인. 한글 파일명은 보존된다.
  회귀 테스트 15건 추가(72 → 87). scienceON 도 동일 수정.

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
- ⚠️ **교육망(학교/교육청)·사내망 SSL 인터셉션** 대응: `truststore` 의존성으로 **OS 신뢰저장소** 사용
  (검증 끄지 않음). `KCI_OS_TRUST=0` 로 비활성 가능.
- 🔗 연계 연구: `투고논문/학부모 학술동향` (ScienceON 621편 STM 분석) — KCI는 초록 백필·완전성 교차검증원.
