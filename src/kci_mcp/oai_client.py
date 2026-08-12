"""KCI OAI-PMH 클라이언트 — **무인증** 대량 수확.

verb: Identify · ListSets · ListIdentifiers · ListMetadataFormats · ListRecords · GetRecord
ListRecords 는 resumptionToken 으로 100건씩 페이징(토큰 재요청 시 다른 파라미터 동반 금지 = OAI 표준).
규격: docs/KCI_OAI_PMH_GUIDE.md
"""
from __future__ import annotations

import time

import requests

from .config import OAI_URL, use_os_trust
from .models import Article
from .parser import (
    OaiError,
    parse_oai_formats,
    parse_oai_identifiers,
    parse_oai_identify,
    parse_oai_records,
    parse_oai_sets,
)


def _contains_any(a: Article, subs: list[str]) -> bool:
    """하위호환 래퍼 — 실제 로직은 Article.matches (REST/OAI 공통)."""
    return a.matches(subs)


class KciOaiClient:
    def __init__(self, *, throttle: float = 0.5, timeout: int = 30):
        use_os_trust()  # 교육망/사내망 SSL 인터셉션 CA를 OS 저장소로 신뢰(검증 유지)
        self.throttle = throttle
        self.timeout = timeout

    def _call(self, params: dict) -> str:
        r = None
        for attempt in range(3):
            try:
                r = requests.get(OAI_URL, params=params, timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                raise OaiError(type(e).__name__, "네트워크/SSL 오류 — 연결 확인 후 재시도.") from None
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(1.5 * (2 ** attempt))  # 지수 백오프
                continue
            break
        if r is None:  # pragma: no cover
            raise OaiError("network", "요청 실패.")
        if r.status_code == 429:
            raise OaiError("429", "요청 한도 초과 — throttle 상향 또는 잠시 후 재시도.")
        if r.status_code >= 400:
            raise OaiError(str(r.status_code), "OAI 서버 응답 오류.")
        if not r.encoding or r.encoding.lower() in ("iso-8859-1", "latin-1"):
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text

    # ── 단순 verb ────────────────────────────────────────────────────────────
    def identify(self) -> dict:
        return parse_oai_identify(self._call({"verb": "Identify"}))

    def list_sets(self) -> list[dict]:
        return parse_oai_sets(self._call({"verb": "ListSets"}))

    def list_metadata_formats(self) -> list[dict]:
        return parse_oai_formats(self._call({"verb": "ListMetadataFormats"}))

    def list_identifiers(self, *, metadata_prefix: str = "oai_dc", date_from: str | None = None,
                         date_until: str | None = None, max_records: int = 1000,
                         max_pages: int = 10000) -> list[dict]:
        """🔴 예전에는 **종료 조건이 `len(out) < max_records` 뿐이라 무한루프가 났다.**

        서버가 토큰은 주면서 header 를 0건 주면 `out` 이 자라지 않아 영영 끝나지 않는다
        (2026-08-12 로컬 서버로 재현 — 40회 상한에서 끊을 때까지 멈추지 않았다).
        `list_records` 와 같은 방식으로 막는다: **새 identifier 가 없으면 중단** + 페이지 수 상한.
        (토큰 문자열 반복으로 순환을 판정하지 않는다 — 서버가 커서를 들고 있어 매번 같은 토큰을
        주는 구현에서 정상 수확이 조용히 잘린다.)
        """
        out: list[dict] = []
        params: dict = {"verb": "ListIdentifiers", "metadataPrefix": metadata_prefix}
        if date_from:
            params["from"] = date_from
        if date_until:
            params["until"] = date_until
        seen_ids: set[str] = set()
        pages = 0
        while len(out) < max_records and pages < max_pages:
            headers, token = parse_oai_identifiers(self._call(params))
            pages += 1
            fresh = False
            for h in headers:
                ident = h.get("identifier") or ""
                if ident and ident in seen_ids:
                    continue
                if ident:
                    seen_ids.add(ident)
                fresh = True
                out.append(h)
            if not token or not fresh:
                break
            params = {"verb": "ListIdentifiers", "resumptionToken": token}
            time.sleep(self.throttle)
        return out[:max_records]

    # ── 레코드 수확 ───────────────────────────────────────────────────────────
    def get_record(self, identifier: str, *, metadata_prefix: str = "oai_kci") -> Article | None:
        text = self._call({"verb": "GetRecord", "identifier": identifier,
                           "metadataPrefix": metadata_prefix})
        arts, _ = parse_oai_records(text)
        return arts[0] if arts else None

    def list_records(self, *, set_spec: str | None = "ARTI", metadata_prefix: str = "oai_kci",
                     date_from: str | None = None, date_until: str | None = None,
                     max_records: int = 1000, contains: list[str] | None = None,
                     max_pages: int = 100000) -> list[Article]:
        """세트+날짜범위 대량 수확. contains 지정 시 로컬 부분일치 필터(키워드 검색 대용)."""
        out: list[Article] = []
        seen: set = set()
        params: dict = {"verb": "ListRecords", "metadataPrefix": metadata_prefix}
        if set_spec:
            params["set"] = set_spec
        if date_from:
            params["from"] = date_from
        if date_until:
            params["until"] = date_until
        pages = 0
        while len(out) < max_records and pages < max_pages:
            arts, token = parse_oai_records(self._call(params))
            pages += 1
            fresh = False
            for a in arts:
                # ⚠️ 중복 판정을 `contains` **앞에** 둔다 — 진전 여부는 '새 레코드를 봤는가'이지
                #    '필터를 통과했는가'가 아니다. 뒤에 두면 필터가 빡빡한 정상 수확에서
                #    진전 없음으로 오판해 조기 종료한다.
                key = a.dedup_key()
                if key in seen:
                    continue
                seen.add(key)
                fresh = True
                if contains and not _contains_any(a, contains):
                    continue
                out.append(a)
                if len(out) >= max_records:
                    break
            # 🔴 `not token` 만으로는 부족했다 — 토큰이 계속 오는데 새 레코드가 없으면
            #    `max_pages`(기본 100,000) 까지 돈다. throttle 0.5s 로 **13시간**이다.
            #    (2026-08-12 로컬 서버로 재현: 상한에서 끊을 때까지 멈추지 않았다.)
            #    ⚠️ 순환 판정을 **토큰 문자열 반복**으로 하면 안 된다 — 커서를 서버가 들고 있어
            #       매 페이지 같은 토큰을 주는 구현에서 정상 수확이 조용히 잘린다
            #       (실제로 이 하네스에서 300건이 200건으로 잘렸다). 레코드로 판정한다.
            if not token or not fresh:
                break
            params = {"verb": "ListRecords", "resumptionToken": token}
            time.sleep(self.throttle)
        return out[:max_records]

    harvest = list_records  # 별칭
