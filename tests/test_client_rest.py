"""REST 클라이언트 검색 로직 검증 (네트워크 없이 _call 모킹).

변형어 합집합·중복제거·연도필터(dateFrom/To)·contains 후처리 — 코퍼스 구성 핵심 로직.
"""
from kci_mcp.client import KciClient
from tests import samples


def _client(monkeypatch, capture=None):
    # throttle=0 필수 — 모킹 테스트에 실제 대기(0.5s/페이지)를 넣으면 스위트가 수 분으로 늘어난다.
    c = KciClient(api_key="TEST", throttle=0)

    def fake_call(api_code, params):
        if capture is not None:
            capture.append(dict(params))
        return samples.REST_ARTICLE_SEARCH

    monkeypatch.setattr(c, "_call", fake_call)
    return c


def test_search_single_title(monkeypatch):
    c = _client(monkeypatch)
    recs = c.search("컴퓨터", max_records=100)
    assert len(recs) == 1
    assert recs[0].arti_id == "ART001143784"


def test_search_terms_union_dedup(monkeypatch):
    c = _client(monkeypatch)
    # 두 변형어가 같은 논문(arti_id)을 반환 → 합집합 시 1건으로 중복제거
    recs = c.search_terms(["컴퓨터", "교육"], max_records=100)
    assert len(recs) == 1
    assert recs[0].arti_id == "ART001143784"


def test_search_terms_contains_filter(monkeypatch):
    c = _client(monkeypatch)
    assert c.search_terms(["컴퓨터"], contains=["존재하지않는단어"]) == []
    assert len(c.search_terms(["컴퓨터"], contains=["용어"])) == 1   # 초록에 '용어' 포함


def test_search_terms_year_filter_to_params(monkeypatch):
    cap: list = []
    c = _client(monkeypatch, capture=cap)
    c.search_terms(["컴퓨터"], year_from=2010, year_to=2020)
    assert any(p.get("dateFrom") == "201001" and p.get("dateTo") == "202012" for p in cap)


def test_matches_helper():
    from kci_mcp.parser import parse_rest_articles
    _, arts = parse_rest_articles(samples.REST_ARTICLE_SEARCH)
    a = arts[0]
    assert a.matches(["용어"]) is True
    assert a.matches("서울교육대학교") is True       # 저자 소속
    assert a.matches(["nope", "없음"]) is False
