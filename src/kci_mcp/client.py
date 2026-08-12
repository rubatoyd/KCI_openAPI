"""KCI REST Open API 클라이언트 — 검색/상세/참고문헌/인용지수.

호출: openApiSearch.kci?apiCode=<…>&key=<인증키>&…  (GET, 응답 XML/UTF-8)
규격: docs/KCI_API_GUIDE.md  ⚠️ 라이브 미검증(키 발급 후 확정).
"""
from __future__ import annotations

import time

import requests

from .config import REST_API_URL, require_api_key, use_os_trust
from .models import Article
from .parser import (
    ParseError,
    parse_rest_articles,
    parse_rest_citation,
    parse_rest_references,
)


class KciError(RuntimeError):
    pass


class KciClient:
    def __init__(self, api_key: str | None = None, *, throttle: float = 0.5, timeout: int = 20):
        use_os_trust()  # 교육망/사내망 SSL 인터셉션 CA를 OS 저장소로 신뢰(검증 유지)
        self.api_key = api_key or require_api_key()
        self.throttle = throttle
        self.timeout = timeout

    def _call(self, api_code: str, params: dict) -> str:
        base = {"apiCode": api_code, "key": self.api_key}
        base.update({k: v for k, v in params.items() if v not in (None, "")})
        last_exc: Exception | None = None
        r = None
        for attempt in range(3):
            try:
                r = requests.get(REST_API_URL, params=base, timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                # 네트워크/SSL/타임아웃 — URL(인증키 포함) 노출 금지, 타입만 보고
                last_exc = e
                if attempt < 2:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                raise KciError(f"네트워크 오류({type(e).__name__}) — 연결/SSL 확인 후 재시도.") from None
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(1.5 * (2 ** attempt))
                continue
            break
        if r is None:  # pragma: no cover
            raise KciError(f"요청 실패({type(last_exc).__name__ if last_exc else 'unknown'}).")
        if r.status_code == 429:
            raise KciError("요청 한도 초과(429) — throttle 상향 또는 잠시 후 재시도.")
        if r.status_code >= 400:
            # raise_for_status 는 key 포함 URL 을 메시지에 넣으므로 사용하지 않음
            raise KciError(f"HTTP {r.status_code} — KCI 서버 응답 오류.")
        # charset 헤더 부재 시 requests 가 Latin-1 로 폴백 → 한글 깨짐. UTF-8 로 보정.
        if not r.encoding or r.encoding.lower() in ("iso-8859-1", "latin-1"):
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text

    # ── articleSearch ─────────────────────────────────────────────────────────
    # 라이브 검증(2026-06-22): `title` 은 제목검색(토큰화, 띄어쓰기 무관). `keyword` 는 **단독 검색 가능**
    # (title 없이도 동작) — 제목엔 없고 키워드에만 있는 논문 회수에 유효. `abstract` 단독은 0건.
    def search_page(self, value: str, *, field: str = "title", page: int = 1, display: int = 100,
                    **filters) -> tuple[int, list[Article]]:
        params = {field: value, "page": page, "displayCount": min(display, 100)}
        params.update(filters)  # author/journal/doi/dateFrom… sortNm/sortDir
        try:
            return parse_rest_articles(self._call("articleSearch", params))
        except ParseError as e:
            raise KciError(str(e)) from e

    def search_meta(self, value: str, *, field: str = "title", max_records: int = 1000,
                    display: int = 100, retry_incomplete: int = 1,
                    **filters) -> tuple[list[Article], dict]:
        """search() + 회수 메타 — 조용한 절단 방지.

        meta = {field, term, total, fetched, truncated}
          total    : KCI 가 보고한 해당 축의 전체 건수(`outputData/result/total`)
          fetched  : 실제 회수·중복제거 후 반환 건수
          truncated: fetched < total (= max_records 상한에 걸려 잘렸다는 뜻)
        절단 여부를 호출자에게 **반드시** 노출한다 — 상한에 걸린 결과를 완전한 코퍼스로
        오인하면 계량서지 분석 전체가 무효가 된다.
        """
        # 요청 크기와 종료식이 항상 일치하도록 단일 변수로 클램프.
        # ⚠️ 하한 1 필수 — displayCount=0 이면 KCI 가 total 까지 0 으로 돌려준다.
        #    그러면 결과가 205건 있는데도 "total 0"(= 결과 없음)으로 보고돼 조용한 오보가 된다.
        rows = max(1, min(display, 100))
        max_records = max(1, max_records)
        out: list[Article] = []
        seen: set = set()
        page = 1
        total = 0
        while len(out) < max_records and page <= 1000:
            total_p, arts = self.search_page(value, field=field, page=page, display=rows, **filters)
            if total_p:
                total = total_p
            if not arts:
                break
            before = len(out)
            for a in arts:
                key = a.dedup_key()
                if key in seen:
                    continue
                seen.add(key)
                out.append(a)
            if len(out) == before:
                break
            if total and page * rows >= total:
                break
            page += 1
            time.sleep(self.throttle)
        # ── 불완전 회수 보정 ────────────────────────────────────────────────────
        # KCI 는 **다중 페이지 질의에서 결과가 흔들린다**(2026-08-11 실측: '교육격차'를 동일 조건으로
        # 3회 돌리면 회수량 204/204/205, 레코드 합집합 205·교집합 203 — 2건이 호출마다 오간다).
        # 페이지 경계에서 정렬이 미세하게 바뀌면 한 건이 두 페이지 사이로 빠지기 때문으로 보인다.
        # 단일 페이지 질의(64건)는 완전히 안정적이었다.
        # → total 에 못 미쳤고 우리 상한도 아니면 **한 번 더 훑어 합집합**을 취한다.
        #   코퍼스 구축에서 1~2건 결손은 재현성 문제로 직결되므로 탐지만으로는 부족하다.
        sweeps = 1
        while (retry_incomplete > 0 and total and len(out) < min(total, max_records)
               and len(out) < max_records):
            retry_incomplete -= 1
            sweeps += 1
            before = len(out)
            page = 1
            while len(out) < max_records and page <= 1000:
                _, arts2 = self.search_page(value, field=field, page=page, display=rows, **filters)
                if not arts2:
                    break
                for a in arts2:
                    k = a.dedup_key()
                    if k not in seen:
                        seen.add(k)
                        out.append(a)
                if total and page * rows >= total:
                    break
                page += 1
                time.sleep(self.throttle)
            if len(out) == before:      # 더 건질 게 없으면 반복 중단
                break

        out = out[:max_records]
        # ⚠️ truncated 와 total_mismatch 를 **분리**한다 (2026-08-11 적대적 검증에서 발견).
        #    예전엔 `fetched < total` 하나로 뭉쳐 있어, 페이징을 끝까지 돌았는데도 truncated=True 가
        #    떴다(실측: '교육격차' total 205/실회수 204, '학부모' 4766/4645 — 중복제거 0건).
        #    KCI 의 total 은 **실제 서빙량보다 클 수 있다**. 그때 "max_records 를 올리라"는 조언은
        #    틀린 처방이며 사용자를 무한 재수집으로 몬다.
        hit_cap = len(out) >= max_records
        return out, {"field": field, "term": value, "total": total, "fetched": len(out),
                     "truncated": hit_cap,           # 우리 상한에 걸림 → 올리면 해결된다
                     "sweeps": sweeps,               # 1보다 크면 불완전 회수를 보정한 것
                     "total_mismatch": (not hit_cap) and bool(total) and len(out) < total}

    def search(self, value: str, *, field: str = "title", max_records: int = 1000,
               display: int = 100, **filters) -> list[Article]:
        """레코드만 반환하는 얇은 래퍼. 절단 여부까지 필요하면 search_meta() 를 쓴다."""
        return self.search_meta(value, field=field, max_records=max_records,
                                display=display, **filters)[0]

    def search_terms_meta(self, terms, *, fields=("title", "keyword"),
                          year_from: int | None = None, year_to: int | None = None,
                          max_records: int = 3000, display: int = 100, contains=None,
                          **filters) -> tuple[list[Article], dict]:
        """여러 변형어를 **각 필드(기본 title+keyword)로 개별 검색**해 arti_id/DOI 합집합 + 회수 메타.

        KCI는 필드 내 OR 연산자가 없으므로 변형어·필드별 개별검색 합집합이 정석.
        ⚠️ 기본 fields 가 두 축이라 결과는 '제목검색 결과'가 아니라 **제목∪키워드**다.
           코퍼스 경계를 기술할 때 이 점을 명시해야 한다.
        title=제목검색, keyword=키워드검색(단독 가능). year_from/to→dateFrom/To(YYYYMM).
        contains→결과 부분일치 후처리 필터.

        meta = {axes[], axes_planned, axes_run, union, union_upper_bound,
                max_records, truncated, returned, (warning)}
        """
        terms = [t.strip() for t in (terms or []) if t and t.strip()]
        fields = list(fields)
        if year_from:
            filters["dateFrom"] = f"{year_from}01"
        if year_to:
            filters["dateTo"] = f"{year_to}12"
        out: list[Article] = []
        seen: set = set()
        axes: list[dict] = []
        stopped_early = False
        for term in terms:
            for field in fields:
                recs, m = self.search_meta(term, field=field, max_records=max_records,
                                           display=display, **filters)
                new = 0
                for a in recs:
                    k = a.dedup_key()
                    if k in seen:
                        continue
                    seen.add(k)
                    out.append(a)
                    new += 1
                axes.append({**m, "new": new})
                if len(out) >= max_records:
                    stopped_early = True
                    break
            if stopped_early:
                break
        out = out[:max_records]
        planned = len(terms) * len(fields)
        meta = {
            "axes": axes,
            "axes_planned": planned,
            "axes_run": len(axes),
            "union": len(out),
            "union_upper_bound": sum(a["total"] for a in axes),
            "max_records": max_records,
            "truncated": bool(stopped_early or len(axes) < planned
                              or any(a["truncated"] for a in axes)),
            # KCI 가 보고한 total 이 실제 서빙량보다 큰 축이 하나라도 있으면 표시.
            # 절단과 달리 max_records 를 올려도 해결되지 않는다 → 조언이 달라야 한다.
            "total_mismatch": any(a.get("total_mismatch") for a in axes),
        }
        if contains:
            subs = [contains] if isinstance(contains, str) else list(contains)
            kept = [a for a in out if a.matches(subs)]
            meta["contains_filtered_out"] = len(out) - len(kept)
            out = kept
        meta["returned"] = len(out)
        if meta["truncated"]:
            meta["warning"] = (
                f"⚠️ 절단됨 — max_records={max_records} 상한에 걸렸습니다. "
                f"실행한 검색축 {len(axes)}/{planned}개의 total 합은 {meta['union_upper_bound']}건"
                f"(합집합 상한)입니다. max_records 를 그 위로 올려 재수집하세요."
            )
        elif meta["total_mismatch"]:
            # 상한에 걸리지 않았는데 total 에 못 미친 경우 — 올려도 해결되지 않는다.
            meta["notice"] = (
                "ℹ️ KCI 가 보고한 total 보다 실제 회수량이 적습니다. 페이징은 끝까지 돌았으므로 "
                "**절단이 아니며 max_records 를 올려도 늘지 않습니다** — KCI 의 total 이 실제 서빙 "
                "가능 건수보다 큰 경우입니다(실측 확인). 회수량을 확정 수치로 쓰세요."
            )
        return out, meta

    def search_terms(self, terms, *, fields=("title", "keyword"),
                     year_from: int | None = None, year_to: int | None = None,
                     max_records: int = 3000, display: int = 100, contains=None,
                     **filters) -> list[Article]:
        """레코드만 반환하는 얇은 래퍼. 절단 여부까지 필요하면 search_terms_meta() 를 쓴다."""
        return self.search_terms_meta(terms, fields=fields, year_from=year_from, year_to=year_to,
                                      max_records=max_records, display=display,
                                      contains=contains, **filters)[0]

    # ── articleDetail ─────────────────────────────────────────────────────────
    def detail(self, arti_id: str) -> Article | None:
        try:
            _, arts = parse_rest_articles(self._call("articleDetail", {"id": arti_id}))
        except ParseError as e:
            raise KciError(str(e)) from e
        return arts[0] if arts else None

    # ── referenceSearch ───────────────────────────────────────────────────────
    def references_meta(self, title: str, *, max_records: int = 100, display: int = 100,
                        **filters) -> tuple[list[dict], dict]:
        """referenceSearch + 회수 메타 — 조용한 절단 방지.

        ⚠️ referenceSearch 는 **page 파라미터가 없어**(가이드 §3) 1회 호출 100건이 API 상한이다.
           즉 total 이 100 을 넘으면 나머지는 **어떤 방법으로도 이어 받을 수 없다**. 그래서 total 을
           노출하는 것이 특히 중요하다 — 절단을 모르면 부분 집합을 전수로 오인한다.
           우회책: `sortNm`/`sortDir` 를 뒤집어 반대쪽 100건을 추가로 얻고 합집합을 취한다.
        """
        params = {"title": title, "displayCount": min(display, 100)}
        params.update(filters)  # author/institution/pubiYr/sortNm/sortDir
        try:
            total, refs = parse_rest_references(self._call("referenceSearch", params))
        except ParseError as e:
            raise KciError(str(e)) from e
        out = refs[:max_records]
        return out, {"total": total, "fetched": len(out),
                     "truncated": bool(total) and len(out) < total,
                     "api_page_limit": 100}

    def references(self, title: str, *, max_records: int = 100, display: int = 100,
                   **filters) -> list[dict]:
        """레코드만 반환하는 얇은 래퍼. 절단 여부까지 필요하면 references_meta() 를 쓴다."""
        return self.references_meta(title, max_records=max_records, display=display, **filters)[0]

    # ── citation / citationDetail ─────────────────────────────────────────────
    def citation(self, year: int, *, years: int = 2, max_records: int = 100,
                 display: int = 100, **filters) -> list[dict]:
        years = max(2, min(years, 5))
        rows = min(display, 100)
        base = {"year": year, "years": years, "displayCount": rows}
        base.update(filters)  # journal/doi/institution/modDate…/sortNm/sortDir
        out: list[dict] = []
        page = 1
        while len(out) < max_records and page <= 1000:
            try:
                total, recs = parse_rest_citation(self._call("citation", {**base, "page": page}))
            except ParseError as e:
                raise KciError(str(e)) from e
            if not recs:
                break
            out.extend(recs)
            if total and page * rows >= total:
                break
            page += 1
            time.sleep(self.throttle)
        return out[:max_records]

    def citation_detail(self, journal_id: str) -> dict | None:
        try:
            _, rows = parse_rest_citation(self._call("citationDetail", {"id": journal_id}))
        except ParseError as e:
            raise KciError(str(e)) from e
        return rows[0] if rows else None
