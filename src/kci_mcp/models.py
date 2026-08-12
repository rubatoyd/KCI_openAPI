"""정규화된 메타데이터 스키마 — REST/OAI 공통 통합 레코드.

REST `articleSearch`/`articleDetail` 와 OAI `oai_kci`/`oai_dc` 가 거의 동일한 서지를 주므로
하나의 `Article` 로 흡수한다(`source` 로 출처 태깅, 원본은 `raw` 보존).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 표 출력(csv/xlsx/sqlite) 시 컬럼 순서
COLUMNS = [
    "source", "arti_id", "title", "title_en", "authors",
    "journal", "issn", "publisher", "pub_year", "pub_mon", "volume", "issue",
    "categories", "abstract", "abstract_en", "keywords",
    "citation_count", "doi", "uci", "url",
]


@dataclass
class Article:
    """REST/OAI 공통 정규화 논문 레코드."""

    source: str                                  # 'rest' | 'oai'
    arti_id: str = ""                            # KCI 논문 제어번호 (ART…)
    title: str = ""                              # 국문(원어) 제목
    title_en: str = ""                           # 영문 제목
    authors: list[str] = field(default_factory=list)   # "이름" 또는 "이름(소속)"
    journal: str = ""
    issn: str = ""
    publisher: str = ""
    pub_year: str = ""
    pub_mon: str = ""
    volume: str = ""
    issue: str = ""
    categories: str = ""                         # 연구분야
    abstract: str = ""                           # 국문(원어) 초록
    abstract_en: str = ""                        # 영문 초록
    keywords: list[str] = field(default_factory=list)
    citation_count: str = ""
    doi: str = ""
    uci: str = ""
    url: str = ""
    # articleDetail 의 <referenceInfo> — 이 논문이 **인용한** 참고문헌 목록.
    # arti_id 가 있는 항목만 KCI 논문으로 연결된다(비KCI 서지는 빈 문자열). articleSearch 에는 없다.
    references: list[dict[str, str]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)   # 원본 필드 보존

    def to_row(self, *, list_sep: str = "; ") -> dict[str, Any]:
        """평탄화된 표 한 행(dict). 리스트 필드는 구분자로 join."""
        row: dict[str, Any] = {}
        for col in COLUMNS:
            val = getattr(self, col)
            row[col] = list_sep.join(val) if isinstance(val, list) else val
        return row

    def dedup_key(self) -> str:
        """항상 동일 타입(str) 키 — id/doi/제목폴백 키스페이스 분리, DOI 정규화.

        (REST+OAI 교차 중복제거 신뢰성: arti_id 결측 시에도 일관 비교)
        """
        if self.arti_id:
            return "id:" + self.arti_id
        if self.doi:
            d = self.doi.strip().lower()
            for pre in ("https://doi.org/", "http://doi.org/",
                        "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
                if d.startswith(pre):
                    d = d[len(pre):]
                    break
            return "doi:" + d
        return "tt:" + self.title.strip().lower() + "|" + (self.pub_year or "")

    def haystack(self) -> str:
        """부분일치 필터용 전체 텍스트(소문자)."""
        parts = [self.title, self.title_en, self.abstract, self.abstract_en, self.categories,
                 "; ".join(self.authors), "; ".join(self.keywords)]
        parts += [v for v in self.raw.values() if isinstance(v, str)]
        return "\n".join(parts).lower()

    def matches(self, subs) -> bool:
        """subs(문자열 또는 목록) 중 하나라도 부분일치하면 True (대소문자 무시).

        빈 필터(None/빈 리스트)는 '필터 없음 = 전부 통과'로 처리한다.
        """
        if isinstance(subs, str):
            subs = [subs]
        subs = [s for s in (subs or []) if s and s.strip()]
        if not subs:
            return True
        hay = self.haystack()
        return any(s.lower() in hay for s in subs)
