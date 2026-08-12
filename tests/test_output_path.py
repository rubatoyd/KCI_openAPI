"""출력 경로 이탈 방지 회귀 테스트.

배경: `name` 은 MCP 도구 인자이고 미지정 시 검색어가 그대로 들어온다. 즉 사용자 입력이
파일 경로에 직접 닿는다. 정규화 전에는 실측으로 아래가 재현됐다.

    name="../escaped" → …\\Temp\\<tmp>\\escaped.json      ← out_dir 밖
    name="..\\esc2"    → …\\Temp\\<tmp>\\esc2.json         ← out_dir 밖
    name="sub/dir/x"  → FileNotFoundError (조용한 실패)
"""
import pytest

from kci_mcp.exporters import export, safe_name
from kci_mcp.models import Article

RECS = [Article(source="rest", arti_id="A1", title="t")]


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path / "kci-output"


@pytest.mark.parametrize("name", ["../escaped", "..\\esc2", "../../../etc/passwd",
                                  "sub/dir/x", "a/../../b"])
def test_never_writes_outside_out_dir(out_dir, name):
    p = export(RECS, ["json"], str(out_dir), name)[0]
    assert out_dir.resolve() in __import__("pathlib").Path(p).resolve().parents


def test_nested_path_does_not_fail_silently(out_dir):
    """회귀: 'sub/dir/x' 는 FileNotFoundError 로 조용히 실패했다."""
    p = export(RECS, ["json"], str(out_dir), "sub/dir/x")[0]
    assert p.endswith("x.json")


@pytest.mark.parametrize("name,expected", [
    ("../escaped", "escaped"),
    ("sub/dir/x", "x"),
    ("CON", "_CON"),          # 윈도 예약 장치명
    ("nul.json", "_nul.json"),
    ("trailing. ", "trailing"),
    ("a<b>c", "a_b_c"),
    ("", "output"),
    ("교육격차", "교육격차"),      # 한글은 보존
])
def test_safe_name(name, expected):
    assert safe_name(name) == expected


def test_long_name_truncated():
    assert len(safe_name("가" * 200)) == 60
