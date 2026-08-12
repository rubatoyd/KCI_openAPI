"""MCP 도구 계층 테스트 (네트워크 없음).

배경: 지적된 결함이 전부 도구 계층에 있었는데 이 계층 테스트가 없어 클라이언트 테스트를
모두 통과하면서도 새어나갔다. 도구가 **클라이언트의 판단을 그대로 전달하는지**를 고정한다.
"""
import pytest

from kci_mcp import client as kci_client
from kci_mcp import server as s


class _StubClient:
    """search_meta / references_meta 를 고정 결과로 대체."""

    def __init__(self, *, search=None, refs=None, capture=None):
        self._search, self._refs, self._cap = search, refs, capture

    def search_meta(self, value, **kw):
        if self._cap is not None:
            self._cap.update(kw)
        return self._search

    def search_terms_meta(self, terms, **kw):
        if self._cap is not None:
            self._cap.update(kw)
        return self._search

    def references_meta(self, title, **kw):
        if self._cap is not None:
            self._cap.update(kw)
        return self._refs


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setattr(s, "get_api_key", lambda: "TEST")


def _install(monkeypatch, **kw):
    stub = _StubClient(**kw)
    monkeypatch.setattr(kci_client, "KciClient", lambda *a, **k: stub)
    return stub


# ── kci_search: 클라이언트 판단을 재계산하지 말 것 ────────────────────────────

def test_search_does_not_recompute_truncated(monkeypatch, keyed):
    """회귀: `fetched < total` 로 다시 세면 client 에서 없앤 오탐 공식이 되살아난다.

    total=15 / 실회수 14 인 total_mismatch 상황에서 옛 공식은 truncated=True 로 오보하고
    '전건 수집은 kci_collect' 라는 틀린 처방을 내보냈다.
    """
    meta = {"total": 15, "fetched": 14, "truncated": False, "total_mismatch": True}
    _install(monkeypatch, search=([], meta))
    r = s.kci_search(title="x", rows=100)
    assert r["truncated"] is False
    assert r["total_mismatch"] is True
    assert "warning" not in r
    assert "rows 를 올려도" in r["notice"]


def test_search_reports_truncation_when_cap_hit(monkeypatch, keyed):
    meta = {"total": 205, "fetched": 20, "truncated": True, "total_mismatch": False}
    _install(monkeypatch, search=([], meta))
    r = s.kci_search(title="x", rows=20)
    assert r["truncated"] is True
    assert "notice" not in r
    assert "kci_collect" in r["warning"]


def test_search_request_size_never_zero(monkeypatch, keyed):
    """rows<=0 이어도 API 요청 크기는 1 이상 — displayCount=0 은 total 까지 0 으로 만든다."""
    cap = {}
    meta = {"total": 205, "fetched": 1, "truncated": True, "total_mismatch": False}
    _install(monkeypatch, search=([], meta), capture=cap)
    r = s.kci_search(title="x", rows=0)
    assert cap["display"] >= 1 and cap["max_records"] >= 1
    assert r["total"] == 205          # total 이 감춰지지 않는다
    assert r["count"] == 0            # 요청대로 0건만 반환


# ── 정렬 인자: 검증한 값과 보낸 값이 같아야 한다 ──────────────────────────────

def test_sort_is_normalized_before_send(monkeypatch, keyed):
    """회귀: 소문자로 검증하고 원본(대문자)을 보내면 검증이 무의미해진다."""
    cap = {}
    meta = {"total": 1, "fetched": 1, "truncated": False, "total_mismatch": False}
    _install(monkeypatch, search=([], meta), capture=cap)
    s.kci_search(title="x", sort_by="TITLE", sort_dir="ASC")
    assert cap["sortNm"] == "title"    # KCI 표기로 정규화
    assert cap["sortDir"] == "asc"


@pytest.mark.parametrize("kw", [{"sort_by": "pubYear"}, {"sort_dir": "sideways"}])
def test_invalid_sort_rejected_with_allowed_values(monkeypatch, keyed, kw):
    _install(monkeypatch, search=([], {}))
    r = s.kci_search(title="x", **kw)
    assert "허용값" in r["error"]


# ── kci_references: 부족한 이유에 따라 처방이 정반대다 ────────────────────────

def test_references_api_cap_advises_sort_flip(monkeypatch, keyed):
    """total>100 이면 API 가 더 줄 수 없다 → sort_dir 반전이 유일한 우회책."""
    meta = {"total": 250, "fetched": 100, "truncated": True,
            "api_capped": True, "api_page_limit": 100}
    _install(monkeypatch, refs=([{}] * 100, meta))
    r = s.kci_references(title="x", rows=100)
    assert "sort_dir" in r["warning"] and "API 상한" in r["warning"]


def test_references_rows_cap_advises_raising_rows(monkeypatch, keyed):
    """회귀: total<=100 인데 rows 로 자른 경우에도 'sort_dir 를 뒤집으라'고 안내했다.

    이때 API 는 이미 전량을 줬으므로 뒤집어도 같은 레코드만 다시 온다. 올바른 처방은 rows 상향.
    """
    meta = {"total": 80, "fetched": 50, "truncated": True,
            "api_capped": False, "api_page_limit": 100}
    _install(monkeypatch, refs=([{}] * 50, meta))
    r = s.kci_references(title="x", rows=50)
    assert "rows 를 80 이상으로" in r["warning"]
    assert "sort_dir 반전은 이 경우" in r["warning"]   # 오안내 방지 문구


# ── kci_collect: 문서에 있는 스위치가 실제로 닿아야 한다 ──────────────────────

def test_collect_forwards_retry_incomplete(monkeypatch, keyed):
    """회귀: README 는 끌 수 있다고 안내하는데 도구에 인자가 없어 도달 불가였다."""
    cap = {}
    meta = {"truncated": False, "total_mismatch": False, "returned": 0}
    _install(monkeypatch, search=([], meta), capture=cap)
    monkeypatch.setattr(s, "decide_backend", lambda **k: ("rest", "테스트"))
    monkeypatch.setattr("kci_mcp.exporters.export", lambda *a, **k: [])
    s.kci_collect(title="x", retry_incomplete=0)
    assert cap["retry_incomplete"] == 0
