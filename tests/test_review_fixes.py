"""scienceON 리뷰에서 나온 공통 지적의 kci 판 회귀 테스트.

자매 프로젝트에서 발견된 결함은 이쪽에도 있다고 가정하고 확인한다 — 이번 세션에서만
같은 패턴이 여섯 번 반복됐다.
"""
import importlib
import pathlib

import pytest

from kci_mcp.client import KciClient
from tests import samples

MANY = samples.REST_ARTICLE_SEARCH                                    # total=3779 / record 1건
EXACT = MANY.replace("<total>3779</total>", "<total>1</total>")        # total=1 / record 1건


@pytest.mark.parametrize("mod", [p.stem for p in
                                 sorted(pathlib.Path(__file__).parents[1]
                                        .glob("src/kci_mcp/*.py"))
                                 if p.stem != "__init__"])
def test_every_module_imports(mod):
    """문법 오류 조기 검출 — cli.py 처럼 어떤 테스트도 임포트하지 않는 모듈이 있었다."""
    importlib.import_module(f"kci_mcp.{mod}")


def _client(monkeypatch, xml=EXACT):
    c = KciClient(api_key="TEST", throttle=0)
    monkeypatch.setattr(c, "_call", lambda api_code, params: xml)
    return c


def test_last_axis_filling_cap_is_not_early_stop(monkeypatch):
    """회귀: 마지막 축이 정확히 상한을 채우면 남은 축이 없는데도 truncated 가 붙었다.

    전수 수집된 코퍼스를 두고 max_records 를 올려 무의미한 재수집을 반복하게 된다.
    """
    c = _client(monkeypatch)
    _, meta = c.search_terms_meta(["하나"], fields=("title",), max_records=1)
    assert meta["axes_run"] == meta["axes_planned"] == 1
    assert meta["truncated"] is False


def test_non_last_axis_filling_cap_is_early_stop(monkeypatch):
    """남은 축이 있는데 멈췄으면 그건 진짜 조기 중단이다."""
    c = _client(monkeypatch)
    _, meta = c.search_terms_meta(["하나", "둘"], fields=("title",), max_records=1)
    assert meta["axes_run"] < meta["axes_planned"]
    assert meta["truncated"] is True


def test_version_is_read_from_installed_metadata():
    """회귀: __init__ 의 하드코딩 버전이 pyproject 와 어긋난 채 방치됐다(0.1.3 vs 0.3.x)."""
    import kci_mcp
    assert kci_mcp.__version__ != "0.1.3"
    assert kci_mcp.__version__[0].isdigit()
