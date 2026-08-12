"""적대적 검증 — **실제 HTTP 왕복**으로 전송·인코딩·재시도·페이징 계층을 태운다.

왜 별도로 두는가: `_call`(또는 `requests.get`)을 monkeypatch 하는 테스트는 **전송·charset
감지·재시도/백오프·URL 파라미터 인코딩·resumptionToken 루프를 통째로 건너뛴다.**
자매 프로젝트 nl 에서 로컬 서버를 띄우자 그 층에서만 결함 4종이 나왔고, scienceon 에서는
3종이 나왔다. 이 저장소에서 나온 것(2026-08-12):

  🔴 오류 응답이 되돌려주는 `<inputData><key>` 가 예외 메시지에 실려 인증키가 MCP 응답까지 누출
  🔴 `display=1` 이 1,000회 요청을 유발(REST 검색)
  🔴 OAI `list_identifiers` 가 **무한 루프** — 토큰은 오는데 header 가 0건이면 영영 끝나지 않는다

⚠️ **이 저장소는 인증키를 URL 쿼리에 평문으로 싣는다**(토큰/AES 없음). 그래서 누출 검사가
   최우선이다. `raise_for_status()` 를 피하는 것만으로는 부족하다는 것이 위 첫 항목이다.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

# 이 값이 예외·응답 어디에도 나오면 안 된다
API_KEY = "SECRET-KCI-KEY-13579"
SECRETS = (API_KEY,)

_REST_OK = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData><key>{key}</key><apiCode>articleSearch</apiCode></inputData>
  <outputData>
    <result><total>{total}</total></result>
    {recs}
  </outputData>
</MetaData>"""

_REST_REC = """<record>
  <journalInfo><journal-name>한국교육학연구</journal-name><pub-year>2020</pub-year></journalInfo>
  <articleInfo article-id="ART{i:09d}">
    <title-group><article-title lang="original">한글 제목 {i}</article-title></title-group>
    <author-group><author>김철수</author></author-group>
  </articleInfo>
</record>"""

# ⚠️ KCI 오류 봉투는 **inputData 를 그대로 되돌려준다** — 거기에 key 가 들어 있다.
_REST_ERR = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData><key>{key}</key><apiCode>articleSearch</apiCode><title>테스트</title></inputData>
  <error>등록되지 않은 key 입니다.</error>
</MetaData>"""

# ⚠️ 구조는 `tests/samples.py::OAI_LISTRECORDS_KCI`(실응답)를 따른다. 처음에 `<title>` 을
#    oai_kci 직속에 두었더니 파서가 `articleInfo/title-group` 만 보므로 arti_id·title 이 전부 비어
#    **모든 레코드의 중복키가 같아졌다** — 300건이 1건으로 접혔다(하네스 버그였다).
_OAI_REC = """<record>
  <header><identifier>oai:kci.go.kr:ARTI/{i}</identifier><datestamp>2020-01-01</datestamp>
    <setSpec>ARTI</setSpec></header>
  <metadata><oai_kci>
    <journalInfo><journal-name>한국교육학연구</journal-name><pub-year>2020</pub-year></journalInfo>
    <articleInfo article-id="ART{i:09d}">
      <title-group><article-title lang="original">한글 제목 {i}</article-title></title-group>
      <author-group><author>김철수(한국교원대학교)</author></author-group>
    </articleInfo>
  </oai_kci></metadata>
</record>"""

_OAI_HDR = """<header><identifier>oai:kci:ART{i:09d}</identifier>
  <datestamp>2020-01-01</datestamp><setSpec>ARTI</setSpec></header>"""


def _oai(body: str, token: str | None) -> str:
    tok = f"<resumptionToken>{token}</resumptionToken>" if token else ""
    return ('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH>'
            f"<ListRecords>{body}{tok}</ListRecords></OAI-PMH>")


STATE: dict = {"mode": "normal", "total": 1000, "calls": [], "fail_left": 0, "cap": None}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # 조용히
        pass

    def _send(self, body: bytes, status=200, ctype="text/xml; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        STATE["calls"].append({"path": u.path, "q": q})
        mode = STATE["mode"]

        # ⚠️ 무한루프 시험용 안전핀. pytest-timeout 을 들이는 대신 **서버가 끊는다** —
        #    루프가 안 끝나면 테스트가 매달리는 게 아니라 호출수와 함께 실패한다(결정적).
        if STATE["cap"] is not None and len(STATE["calls"]) > STATE["cap"]:
            return self._send(b'<?xml version="1.0"?><OAI-PMH><error code="tooManyCalls">'
                              b"harness cap</error></OAI-PMH>")

        if mode == "http_500":
            return self._send(b"server error", 500, "text/plain")
        if mode == "http_429":
            return self._send(b"slow down", 429, "text/plain")
        if mode == "malformed":
            return self._send(b"<MetaData><outputData><record>")
        if mode == "empty":
            return self._send(b"")
        if mode == "flaky" and STATE["fail_left"] > 0:
            STATE["fail_left"] -= 1
            return self._send(b"tmp", 503, "text/plain")

        if "oai" in u.path:
            return self._oai(q, mode)
        return self._rest(q, mode)

    # ── REST ────────────────────────────────────────────────────────────────
    def _rest(self, q, mode):
        if mode == "rest_error_xml":
            return self._send(_REST_ERR.format(key=q.get("key", "")).encode())
        rows = int(q.get("displayCount", 10) or 10)
        page = int(q.get("page", 1) or 1)
        total = STATE["total"]
        start = (page - 1) * rows
        n = max(0, min(rows, total - start))
        body = _REST_OK.format(key=q.get("key", ""), total=total,
                               recs="".join(_REST_REC.format(i=start + i) for i in range(n)))
        if mode == "no_charset":
            return self._send(body.encode("utf-8"), 200, "text/xml")   # charset 없음
        return self._send(body.encode("utf-8"))

    # ── OAI ─────────────────────────────────────────────────────────────────
    def _oai(self, q, mode):
        verb = q.get("verb", "")
        if mode == "oai_error_xml":
            return self._send(b'<?xml version="1.0"?><OAI-PMH><error code="badArgument">'
                              b"bad</error></OAI-PMH>")
        # 🔴 토큰은 계속 오는데 레코드는 0건 — 실서버 장애/필터링에서 실제로 나올 수 있는 형태
        if mode == "oai_token_empty":
            if verb == "ListIdentifiers":
                return self._send(('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH>'
                                   "<ListIdentifiers><resumptionToken>t</resumptionToken>"
                                   "</ListIdentifiers></OAI-PMH>").encode())
            return self._send(_oai("", "t").encode())
        # 서버가 커서를 들고 있어 **매 페이지 같은 토큰 문자열**을 준다 — 내용은 정상 진행한다.
        # 표준 위반이 아니다. 토큰 반복을 순환으로 오판하면 여기서 수확이 조용히 잘린다.
        if mode == "oai_same_token":
            i = len(STATE["calls"])
            if verb == "ListIdentifiers":
                return self._send(('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH>'
                                   f"<ListIdentifiers>{_OAI_HDR.format(i=i)}"
                                   "<resumptionToken>same</resumptionToken>"
                                   "</ListIdentifiers></OAI-PMH>").encode())
            return self._send(_oai(_OAI_REC.format(i=i), "same").encode())
        # 🔴 진짜 순환 — **같은 레코드**를 토큰과 함께 영원히 반복한다
        if mode == "oai_repeat":
            if verb == "ListIdentifiers":
                return self._send(('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH>'
                                   f"<ListIdentifiers>{_OAI_HDR.format(i=7)}"
                                   "<resumptionToken>t</resumptionToken>"
                                   "</ListIdentifiers></OAI-PMH>").encode())
            return self._send(_oai(_OAI_REC.format(i=7), "t").encode())

        page = len(STATE["calls"])
        if verb == "ListIdentifiers":
            body = "".join(_OAI_HDR.format(i=page * 100 + i) for i in range(100))
            return self._send(('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH>'
                               f"<ListIdentifiers>{body}"
                               f"<resumptionToken>{'t' if page < 5 else ''}</resumptionToken>"
                               "</ListIdentifiers></OAI-PMH>").encode())
        body = "".join(_OAI_REC.format(i=page * 100 + i) for i in range(100))
        return self._send(_oai(body, "t" if page < 5 else None).encode())


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture
def rest(server, monkeypatch):
    """실제 소켓으로 로컬 서버를 때리는 REST 클라이언트."""
    import kci_mcp.client as clientmod

    monkeypatch.setattr(clientmod, "REST_API_URL", f"{server}/po/openapi/openApiSearch.kci")
    monkeypatch.setenv("KCI_API_KEY", API_KEY)
    monkeypatch.setenv("KCI_OS_TRUST", "0")

    def make(mode="normal", total=1000, fail=0):
        STATE.update(mode=mode, total=total, calls=[], fail_left=fail)
        return clientmod.KciClient(api_key=API_KEY, throttle=0)
    return make


@pytest.fixture
def oai(server, monkeypatch):
    import kci_mcp.oai_client as oaimod

    monkeypatch.setattr(oaimod, "OAI_URL", f"{server}/oai/request")
    monkeypatch.setenv("KCI_OS_TRUST", "0")

    def make(mode="normal"):
        STATE.update(mode=mode, calls=[], fail_left=0)
        return oaimod.KciOaiClient(throttle=0)
    return make


def _leaked(text: str) -> list[str]:
    return [s for s in SECRETS if s in text]


# ══ 자격증명 누출 — 최우선 ═══════════════════════════════════════════════════
@pytest.mark.parametrize("mode", [
    "rest_error_xml", "http_500", "http_429", "malformed", "empty", "flaky",
])
def test_어떤_오류_경로에서도_인증키가_새지_않는다(rest, mode):
    """🔴 `rest_error_xml` 에서 실제로 샜다.

    이 저장소는 `raise_for_status()` 가 URL 을 예외에 넣는다는 것을 알고 처음부터 피했고
    주석까지 남겼다. 그런데 **누출은 다른 문에서 났다** — `check_rest_error` 가 오류 응답의
    모든 요소 텍스트를 이어붙여 예외에 담는데, KCI 오류 봉투는 `<inputData><key>` 로
    **인증키를 그대로 되돌려준다.** 전송 계층만 잠그면 되는 게 아니었다.
    """
    c = rest(mode, fail=99)
    msg = ""
    try:
        c.search("교육격차", max_records=10, display=10)
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"
    assert not _leaked(msg), f"[{mode}] 예외에 인증키: {msg[:200]}"


@pytest.mark.parametrize("mode", ["rest_error_xml", "http_500", "malformed"])
def test_MCP_도구_응답에_인증키가_없다(rest, mode, monkeypatch, tmp_path):
    """예외가 `_safe` 를 타고 MCP 응답 → LLM 트랜스크립트로 흘러가는 경로를 막는다.

    ⚠️ 처음엔 `kci_search(..., max_records=5)` 로 불러 **TypeError 가 `_safe` 에 먹히는 바람에
       통과했다**(도구 인자는 `rows` 다). 오류 경로를 시험한다면서 도구에 닿지도 못한 것이다 —
       그래서 아래는 **정상 인자로 호출되었는지**를 먼저 검사한다.
    """
    import kci_mcp.client as clientmod
    from kci_mcp import server as srv
    c = rest(mode)
    # ⚠️ 도구들이 `from .client import KciClient` 를 **함수 안에서** 하므로 server 모듈에는
    #    그 이름이 없다. 원본 모듈을 갈아끼워야 도구 경로가 가짜 서버를 탄다.
    monkeypatch.setattr(clientmod, "KciClient", lambda *a, **k: c)
    outs = [srv.kci_status(),
            srv.kci_search("교육격차", rows=5),
            srv.kci_collect(title="교육격차", max_records=5,
                            out_dir=str(tmp_path), formats=["json"])]
    for out in outs:
        assert isinstance(out, dict)
        assert "TypeError" not in str(out.get("error", "")), f"도구 호출 자체가 실패: {out}"
        blob = json.dumps(out, ensure_ascii=False, default=str)
        assert not _leaked(blob), f"[{mode}] 응답에 인증키: {blob[:200]}"


def test_정상_응답의_에코된_key_도_레코드에_남지_않는다(rest):
    """성공 응답의 `<inputData><key>` 는 파싱 대상 밖이지만 `raw` 보존 정책과 겹칠 수 있다."""
    recs = rest("normal", total=5).search("교육격차", max_records=5, display=5)
    blob = json.dumps([r.to_row() for r in recs], ensure_ascii=False, default=str)
    assert not _leaked(blob)


# ══ 전송 계층 ════════════════════════════════════════════════════════════════
def test_charset_헤더가_없어도_한글이_깨지지_않는다(rest):
    """`_call` 의 UTF-8 보정이 **실제 왕복에서도** 듣는지 본다(대조 겸 회귀)."""
    recs = rest("no_charset", total=5).search("교육격차", max_records=5, display=5)
    assert recs and "한글" in (recs[0].title or "")


@pytest.mark.parametrize("fails, ok", [(1, True), (2, True), (3, False)])
def test_일시적_503_재시도(rest, fails, ok):
    from kci_mcp.client import KciError
    c = rest("flaky", total=50, fail=fails)
    if ok:
        assert c.search("교육격차", max_records=5, display=5)
    else:
        with pytest.raises(KciError):
            c.search("교육격차", max_records=5, display=5)


@pytest.mark.parametrize("display", [1, 5, 100])
def test_작은_display_가_호출_폭주를_일으키지_않는다(rest, display):
    """🔴 `display=1`·`max_records=1000` 이 **1,000회 요청**을 유발했다.

    `display` 는 전송 단위일 뿐 결과를 바꾸지 않는다. 여러 페이지가 필요하면 최대로 올린다.
    (nl·scienceon 에서 각각 499회·300회로 나온 것과 같은 결함이다 — 세 번째 반복.)
    """
    c = rest("normal", total=1000)
    recs = c.search("교육격차", max_records=1000, display=display)
    assert len(recs) == 1000
    assert len(STATE["calls"]) <= 15, f"display={display} → {len(STATE['calls'])}회 요청"


def test_인증키는_쿼리로는_정상_전달된다(rest):
    """누출 검사가 과해서 **정상 전달까지 막지는 않았는지** 확인(대조군)."""
    rest("normal", total=5).search("교육격차", max_records=5, display=5)
    assert STATE["calls"] and STATE["calls"][0]["q"].get("key") == API_KEY


# ══ OAI-PMH resumptionToken 루프 ═════════════════════════════════════════════
def test_OAI_수확이_토큰_체인을_따라간다(oai):
    """대조군 — 정상 토큰 체인에서 실제로 여러 페이지를 걷는지."""
    arts = oai("normal").list_records(max_records=300)
    assert len(arts) == 300
    assert len(STATE["calls"]) >= 3


def _bounded(fn, cap=40):
    """호출 상한을 걸고 실행한 뒤 (예외, 호출수) 를 돌려준다.

    상한에 닿았다는 것은 **클라이언트가 스스로 멈추지 못했다**는 뜻이다.
    """
    STATE["cap"] = cap
    try:
        fn()
        return None, len(STATE["calls"])
    except Exception as e:  # noqa: BLE001
        return e, len(STATE["calls"])
    finally:
        STATE["cap"] = None


@pytest.mark.parametrize("verb", ["list_identifiers", "list_records"])
def test_레코드_0건_토큰이_무한루프를_만들지_않는다(oai, verb):
    """🔴 `list_identifiers` 가 **영영 끝나지 않았다.**

    종료 조건이 `len(out) < max_records` 뿐이라, 서버가 토큰은 주면서 header 를 0건 주면
    `out` 이 자라지 않아 루프가 끝나지 않는다. `list_records` 는 `max_pages` 가 있으나
    기본 100,000 이라 throttle 0.5s 로 **13시간**이다 — 사실상 같은 결함이다.
    """
    c = oai("oai_token_empty")
    exc, n = _bounded(lambda: getattr(c, verb)(max_records=100))
    assert exc is None, f"{verb}: 상한({n}회)까지 멈추지 못했다 — {exc}"
    assert n <= 40, f"{verb}: {n}회 요청"


@pytest.mark.parametrize("verb", ["list_identifiers", "list_records"])
def test_같은_레코드가_반복돼도_무한루프를_만들지_않는다(oai, verb):
    """진짜 순환 — 서버가 같은 레코드를 토큰과 함께 영원히 되돌려준다."""
    c = oai("oai_repeat")
    exc, n = _bounded(lambda: getattr(c, verb)(max_records=50))
    assert exc is None, f"{verb}: 상한({n}회)까지 멈추지 못했다 — {exc}"
    assert n <= 5, f"{verb}: {n}회 요청 — 진전 없음을 늦게 알아챘다"


@pytest.mark.parametrize("verb", ["list_identifiers", "list_records"])
def test_토큰_문자열이_매번_같아도_수확이_끊기지_않는다(oai, verb):
    """⚠️ 순환 방지를 **토큰 반복**으로 구현하면 여기서 조용히 잘린다.

    커서를 서버가 들고 있으면 매 페이지 같은 토큰이 와도 정상이다. 첫 처방이 이것이었고,
    이 하네스에서 정상 수확 300건이 **200건으로 잘렸다**. 그래서 진전 판정을
    토큰이 아니라 **새 레코드 유무**로 바꿨다 — 이 테스트가 그 회귀다.
    """
    got = getattr(oai("oai_same_token"), verb)(max_records=20)
    assert len(got) == 20, f"{verb}: {len(got)}건만 회수 — 토큰 반복을 순환으로 오판했다"


def test_OAI_오류_봉투는_구조화된_예외가_된다(oai):
    from kci_mcp.parser import OaiError
    with pytest.raises(OaiError) as ei:
        oai("oai_error_xml").list_records(max_records=10)
    assert ei.value.code == "badArgument"


@pytest.mark.parametrize("mode", ["http_500", "http_429", "malformed", "empty"])
def test_OAI_오류_경로가_예외로_수렴한다(oai, mode):
    """OAI 는 무인증이라 누출 위험은 없지만, 예외 타입이 새면 `_safe` 밖에서 죽는다."""
    from kci_mcp.parser import OaiError, ParseError
    with pytest.raises((OaiError, ParseError)):
        oai(mode).list_records(max_records=10)
