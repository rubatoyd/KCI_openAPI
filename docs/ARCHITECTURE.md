# kci-openapi-mcp 아키텍처 — REST + OAI-PMH 혼용 설계

> 결론: **혼용 MCP는 가능하며, 그게 정석이다.** 두 백엔드(REST Open API · OAI-PMH)를
> **공통 코어** 위 두 클라이언트로 두고, **요청 성격 + 인증키 유무**로 자동 라우팅한다.
> 규격: [KCI_API_GUIDE.md](KCI_API_GUIDE.md)(REST) · [KCI_OAI_PMH_GUIDE.md](KCI_OAI_PMH_GUIDE.md)(OAI-PMH).
> ⚠️ 라이브 미검증 — OAI(무인증)부터 검증 착수 권장.

---

## 1. 레이어 구조
```
server.py / cli.py            ← MCP 도구 · CLI 표면
        │
     router.py                ← ★ 요청 → 백엔드 결정(혼용의 핵심)
     ┌───┴────────────┐
 client.py        oai_client.py
 (REST, key 필요)   (OAI-PMH, 무인증)
     └───┬────────────┘
  공통 코어:
   models.py     통합 Article/Reference/JournalCitation 스키마
   parser.py     REST XML + OAI(oai_dc/oai_kci) → 동일 Article 로 정규화(raw 보존)
   exporters.py  xlsx/csv/json/sqlite (scienceON 재사용)
   config.py     엔드포인트 2종 + KCI_API_KEY 로딩
```
- 두 클라이언트는 **출력 스키마가 같다**(parser가 흡수) → 상위 도구·exporter는 출처를 몰라도 됨.
- `source` 필드(`"rest"`/`"oai"`)로 출처만 태깅 → 교차검증·디버깅용.

## 2. 통합 레코드 스키마(요지)
`Article`: `artiId` · `doi` · `uci` · `title{ko,en}` · `authors[{name,affiliation}]` ·
`journal{name,issn,publisher,pubYear,pubMon,volume,issue}` · `categories` ·
`abstract{ko,en}` · `fpage` · `lpage` · `citationCount` · `url` · `source` · `raw`
> REST `articleSearch`/`articleDetail` 와 OAI `oai_kci` 가 거의 동일 필드 → 자연스럽게 통합.
> (OAI `oai_dc` 는 일부 평면화 필드 → 같은 스키마에 best-effort 매핑)

## 3. 라우팅 규칙 — `kci_collect`(혼용 진입점)

| 요청 성격 | 키 보유 | 선택 백엔드 | 비고 |
|---|:--:|---|---|
| 저널 인용지수(IF) | — | **REST** citation/citationDetail | OAI 미제공 → 키 없으면 불가 안내 |
| 참고문헌 | — | **REST** referenceSearch | OAI 미제공 |
| 주제어(키워드) 검색 | ✅ | **REST** articleSearch | 정밀·페이징(≤100) |
| 주제어(키워드) 검색 | ❌ | **OAI** ListRecords + **로컬 필터** | 무인증, 정밀도↓·비용↑ 경고 |
| 세트 전수 / 날짜범위 / 증분 | — | **OAI** ListRecords(resumptionToken) | 키 무관, 무인증 |
| 단건 상세(artiId 보유) | ✅ | **REST** articleDetail | OAI는 artiId 타깃조회 불가(§6) |

**결정 트리(의사코드)**
```
def route(req):
    if req.needs in ("journal_citation","references"):
        return REST            # OAI 미제공 (키 필수)
    if req.keyword:
        return REST if has_key() else OAI_with_local_filter(req.keyword)
    return OAI                  # 세트/날짜범위 전수·증분 (무인증)
# 결과 → parser 정규화 → artiId/DOI 중복제거 → (선택) 두 소스 병합 → export
```

## 4. 백엔드 능력 매트릭스(라우팅 근거)
| 능력 | REST | OAI-PMH |
|---|:--:|:--:|
| 인증 | 키 필요 | **불필요** |
| 키워드/필터 검색 | ✅ | ❌(세트+날짜만) |
| 전수·증분 대량수집 | △(page) | ✅(resumptionToken/datestamp) |
| 국문·영문 초록 | ✅ | ✅(oai_kci) |
| 저자·소속 분리 | ✅(detail) | ✅(oai_kci author-name) |
| 저널 인용지수 | ✅ | ❌ |
| 참고문헌 | ✅ | ❌ |

## 5. 혼용이 빛나는 시나리오
1. **키 발급 전 착수**: OAI로 코퍼스 수집·MCP 개발·검증 → 키 나오면 REST 기능 추가(무중단).
2. **완전성 교차검증**: 같은 기간을 REST(주제검색)와 OAI(전수수확+로컬필터)로 모아 **artiId/DOI 합집합·차집합** → 한쪽 누락분 탐지.
3. **초록 백필**: REST 결측 초록을 OAI oai_kci 동일 레코드(artiId/DOI 매칭)로 보강(또는 그 반대).
4. **인용지수 결합**: OAI 수확 논문 + REST citationDetail 저널 IF 를 journal-id/ISSN 으로 조인.

## 6. 한계·주의 (정직하게)
- **식별자 불일치**: OAI `identifier`(`oai:kci.go.kr:ARTI/<일련번호>`) ≠ `artiId`(ART…).
  → OAI는 **artiId로 단건 타깃조회 불가**(수확 전용). 소스 간 매칭·중복제거는 **artiId/DOI 본문값**으로.
- **OAI 로컬 필터 비용**: 키워드 검색이 없어 날짜범위 전수 수확 후 필터 → 범위 넓으면 무거움. 연도 청크 권장.
- **전건 미검증**: 본 설계는 PDF 명세 기반. OAI 1~2건 소량 호출로 스키마 확정 후 라우터 구현 착수.
- **정중한 호출**: 두 클라이언트 공통 throttle·지수백오프·페이지 안전장치(새 레코드 0이면 종료).

## 7. 구현 순서(제안)
1. `oai_client.py` + `parser`(oai_kci) + `models` → OAI 라이브 검증(무인증) → `kci_harvest`
2. `exporters` 연결 → 무인증 코퍼스 수집 end-to-end
3. 키 발급 후 `client.py`(REST) + `kci_search/detail/references/journal_citation`
4. `router.py` + `kci_collect` 로 혼용 통합 → 교차검증·백필 시나리오 적용
