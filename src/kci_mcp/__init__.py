"""kci-openapi-mcp — KCI(Korea Citation Index) REST Open API + OAI-PMH 혼용 수집기."""

# 하드코딩하면 릴리스마다 pyproject 와 어긋난다(실제로 0.1.0 인 채 방치됐다) → 설치 메타데이터 조회.
try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("kci-openapi-mcp")
except Exception:  # 미설치(소스 직접 실행) 등
    __version__ = "0.0.0+unknown"
