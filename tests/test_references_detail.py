"""articleDetail 의 <referenceInfo> 파싱과 referenceSearch 절단 노출 검증 (오프라인).

배경 — 이 둘은 명세에는 있으나 MCP 가 흘려버리던 정보다.
  · referenceInfo: 논문별 참고문헌을 **KCI 논문 ID(arti-id)** 와 함께 준다. 인용 네트워크의 유일한 연결고리.
  · referenceSearch 의 total: page 파라미터가 없어 1회 100건이 상한인데, total 을 안 보여주면
    부분 집합을 전수로 오인한다(실측: total 191건인데 50건만 회수돼도 표시가 없었다).
"""
from kci_mcp.parser import parse_rest_articles
from tests import samples


def _detail_article():
    _, arts = parse_rest_articles(samples.REST_ARTICLE_DETAIL)
    return arts[0]


def test_detail_parses_references():
    a = _detail_article()
    assert len(a.references) == 2


def test_reference_keeps_kci_article_id():
    """arti-id 가 인용 네트워크의 연결고리다 — 이게 없으면 텍스트 대조밖에 못 한다."""
    a = _detail_article()
    assert a.references[0]["arti_id"] == "ART002687726"
    assert a.references[0]["refebibl_id"] == "REF077422048"


def test_non_kci_reference_has_empty_arti_id():
    """단행본·보고서 등 KCI 미등재 서지에는 arti-id 가 없다. 빈 문자열로 구분 가능해야 한다."""
    a = _detail_article()
    assert a.references[1]["arti_id"] == ""
    assert a.references[1]["type_name"] == "보고서"


def test_api_typo_field_names_are_honored():
    """KCI 원본 원소명은 `pubi-year`·`isseue`·`pubilisher` 로 **오타**다.

    회귀: 정상 철자(pub-year/issue/publisher)로 추정해 매핑하면 값이 통째로 비어버린다.
    """
    a = _detail_article()
    assert a.references[0]["pub_year"] == "2021"   # <pubi-year>
    assert a.references[0]["volume"] == "70"
    assert a.references[1]["publisher"] == "교육부"  # <pubilisher>


def test_article_search_has_no_references():
    """articleSearch 응답에는 referenceInfo 가 없다 — 빈 리스트여야 하고 예외가 나면 안 된다."""
    _, arts = parse_rest_articles(samples.REST_ARTICLE_SEARCH)
    assert all(a.references == [] for a in arts)


def test_references_meta_reports_truncation(monkeypatch):
    """referenceSearch 는 page 가 없어 상한을 넘으면 이어 받을 수 없다 → total 노출이 필수."""
    from kci_mcp.client import KciClient

    c = KciClient.__new__(KciClient)          # __init__(인증키) 우회
    c.throttle = 0
    monkeypatch.setattr(c, "_call", lambda *a, **k: samples.REST_REFERENCES)
    refs, meta = c.references_meta("컴퓨터", max_records=2)
    assert meta["total"] == 82557
    assert meta["fetched"] == 2
    assert meta["truncated"] is True
    assert meta["api_page_limit"] == 100
    assert len(refs) == 2


def test_references_wrapper_keeps_list_contract(monkeypatch):
    """기존 호출부 호환 — references() 는 여전히 리스트만 반환한다."""
    from kci_mcp.client import KciClient

    c = KciClient.__new__(KciClient)
    c.throttle = 0
    monkeypatch.setattr(c, "_call", lambda *a, **k: samples.REST_REFERENCES)
    out = c.references("컴퓨터")
    assert isinstance(out, list) and out[0]["article_id"] == "ART002703100"
