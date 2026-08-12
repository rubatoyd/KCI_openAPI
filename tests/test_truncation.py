"""절단(max_records) 가시화 회귀 테스트 — 네트워크 없이 _call 모킹.

배경: 상한에 걸린 결과가 조용히 반환되면 불완전한 코퍼스를 완전한 것으로 오인하게 된다.
실제로 '학부모' 수집에서 3,000 → 6,000 건이 연속으로 상한값과 정확히 일치했고,
축별 total 을 직접 실측하기 전까지 절단 사실이 드러나지 않았다. 그 재발을 막는다.
"""
from kci_mcp.client import KciClient
from tests import samples

# total=3779 인데 record 는 1건 → 항상 절단 상태인 샘플
MANY = samples.REST_ARTICLE_SEARCH
# total=1 / record 1건 → 절단 아님
EXACT = samples.REST_ARTICLE_SEARCH.replace("<total>3779</total>", "<total>1</total>")


def _client(monkeypatch, xml=MANY):
    c = KciClient(api_key="TEST", throttle=0)
    monkeypatch.setattr(c, "_call", lambda api_code, params: xml)
    return c


def test_total_mismatch_is_not_reported_as_truncation(monkeypatch):
    """total 에 못 미쳐도 **우리 상한에 걸리지 않았으면 절단이 아니다.**

    회귀(2026-08-11 적대적 검증): 예전엔 `fetched < total` 하나로 판정해, 페이징을 끝까지
    돌았는데도 truncated=True 가 떴다(실측: '교육격차' total 205/실회수 204, 중복 0건).
    그 경우 "max_records 를 올리라"는 조언은 **올려도 해결되지 않는 틀린 처방**이다.
    """
    c = _client(monkeypatch)
    recs, meta = c.search_meta("컴퓨터", max_records=100)
    assert len(recs) == 1
    assert meta["total"] == 3779
    assert meta["fetched"] == 1
    assert meta["truncated"] is False        # 상한(100) 미도달 → 절단 아님
    assert meta["total_mismatch"] is True    # 대신 total 불일치로 표시


def test_hitting_our_cap_is_truncation(monkeypatch):
    """우리 상한에 실제로 걸리면 truncated=True 이고 total_mismatch 는 False 다."""
    c = _client(monkeypatch)
    _, meta = c.search_meta("컴퓨터", max_records=1)
    assert meta["truncated"] is True
    assert meta["total_mismatch"] is False


def test_request_size_never_zero(monkeypatch):
    """display/max_records 가 0 이하여도 요청 크기는 1 이상이어야 한다.

    회귀: displayCount=0 이면 KCI 가 total 까지 0 으로 돌려줘, 205건이 존재하는데도
    '결과 없음'으로 조용히 오보된다(실측 확인).
    """
    seen = {}
    c = KciClient(api_key="TEST", throttle=0)

    def _call(api_code, params):
        seen.update(params)
        return MANY

    monkeypatch.setattr(c, "_call", _call)
    _, meta = c.search_meta("컴퓨터", max_records=0, display=0)
    assert int(seen["displayCount"]) >= 1
    assert meta["total"] == 3779          # total 이 감춰지지 않는다


def test_search_meta_not_truncated_when_complete(monkeypatch):
    c = _client(monkeypatch, xml=EXACT)
    _, meta = c.search_meta("컴퓨터", max_records=100)
    assert meta["total"] == 1
    assert meta["truncated"] is False


def test_search_wrapper_still_returns_list(monkeypatch):
    """기존 호출부 호환 — search() 는 여전히 list[Article]."""
    c = _client(monkeypatch)
    recs = c.search("컴퓨터", max_records=100)
    assert isinstance(recs, list) and recs[0].arti_id == "ART001143784"


def test_search_terms_meta_records_both_axes(monkeypatch):
    """기본 fields=(title, keyword) → 축 2개가 각각 실행되고 total 이 축별로 남는다."""
    c = _client(monkeypatch)
    recs, meta = c.search_terms_meta(["컴퓨터"], max_records=100)
    assert meta["axes_planned"] == 2 and meta["axes_run"] == 2
    assert [a["field"] for a in meta["axes"]] == ["title", "keyword"]
    assert meta["union"] == 1            # 두 축이 같은 논문 → 합집합 1건
    assert meta["union_upper_bound"] == 3779 * 2
    # 상한 미도달이므로 절단이 아니라 total 불일치 — 조언(notice)도 warning 과 달라야 한다
    assert meta["truncated"] is False
    assert meta["total_mismatch"] is True
    assert "warning" not in meta
    assert "올려도" in meta["notice"]


def test_search_terms_meta_stops_early_and_flags(monkeypatch):
    """상한에 먼저 걸리면 남은 축을 돌지 못한 사실(axes_run < axes_planned)이 드러나야 한다."""
    c = _client(monkeypatch)
    _, meta = c.search_terms_meta(["컴퓨터", "교육"], max_records=1)
    assert meta["axes_run"] < meta["axes_planned"]
    assert meta["truncated"] is True


def test_search_terms_meta_clean_run_not_flagged(monkeypatch):
    c = _client(monkeypatch, xml=EXACT)
    _, meta = c.search_terms_meta(["컴퓨터"], max_records=100)
    assert meta["truncated"] is False
    assert "warning" not in meta


def test_contains_filter_counted_in_meta(monkeypatch):
    c = _client(monkeypatch, xml=EXACT)
    recs, meta = c.search_terms_meta(["컴퓨터"], max_records=100, contains=["존재하지않는단어"])
    assert recs == []
    assert meta["contains_filtered_out"] == 1
    assert meta["returned"] == 0


# ── 불완전 회수 보정 ──────────────────────────────────────────────────────────

def _two_record_pages():
    """total=2 인데 페이지마다 1건씩만, 그것도 호출마다 다른 건을 주는 불안정 응답 모사.

    KCI 실측 현상: 동일 조건 3회에 회수량 204/204/205, 레코드 합집합 205·교집합 203.
    """
    one = samples.REST_ARTICLE_SEARCH.replace("<total>3779</total>", "<total>2</total>")
    other = one.replace("ART001143784", "ART999999999")
    return one, other


def test_retry_recovers_records_missed_by_unstable_paging(monkeypatch):
    one, other = _two_record_pages()
    seq = {"n": 0}

    def _call(api_code, params):
        seq["n"] += 1
        return one if seq["n"] <= 1 else other   # 1스윕: A만 / 재스윕: B

    c = KciClient(api_key="TEST", throttle=0)
    monkeypatch.setattr(c, "_call", _call)
    recs, meta = c.search_meta("컴퓨터", max_records=100)
    assert meta["sweeps"] == 2                    # 보정이 실제로 돌았다
    assert meta["fetched"] == 2 == meta["total"]  # total 을 채웠다
    assert meta["total_mismatch"] is False
    assert {a.arti_id for a in recs} == {"ART001143784", "ART999999999"}


def test_retry_can_be_disabled(monkeypatch):
    """retry_incomplete=0 이면 보정하지 않고 불일치만 보고한다(비용 통제용)."""
    one, _ = _two_record_pages()
    c = KciClient(api_key="TEST", throttle=0)
    monkeypatch.setattr(c, "_call", lambda a, p: one)
    _, meta = c.search_meta("컴퓨터", max_records=100, retry_incomplete=0)
    assert meta["sweeps"] == 1
    assert meta["total_mismatch"] is True


def test_retry_stops_when_nothing_new(monkeypatch):
    """재스윕에서 새 레코드가 안 나오면 무한 반복하지 않는다."""
    one, _ = _two_record_pages()
    c = KciClient(api_key="TEST", throttle=0)
    monkeypatch.setattr(c, "_call", lambda a, p: one)
    _, meta = c.search_meta("컴퓨터", max_records=100, retry_incomplete=5)
    assert meta["sweeps"] == 2        # 1회 시도 후 소득 없으면 중단
