"""KCI 응답(XML) → 정규화 레코드.

두 소스를 모두 흡수한다.
  - REST  : <MetaData><outputData><result><total/></result><record><journalInfo/><articleInfo/></record>
  - OAI    : <OAI-PMH>…<record><header/><metadata><oai_kci|oai_dc:dc/></metadata></record>…<resumptionToken/>

네임스페이스는 localname 으로 제거해 처리한다. PDF 예시의 전각 따옴표(lang=“…”)는 실제 응답에선 표준 따옴표.
⚠️ 라이브 미검증 — 첫 응답으로 태그/속성 확정 후 갱신.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from .models import Article


# ── XML 헬퍼 ────────────────────────────────────────────────────────────────
def _ln(tag: str) -> str:
    return tag.split("}", 1)[-1]  # 네임스페이스 제거


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None and el.text else ""


def _child(el: ET.Element | None, name: str) -> ET.Element | None:
    if el is None:
        return None
    for c in el:
        if _ln(c.tag) == name:
            return c
    return None


def _children(el: ET.Element | None, name: str) -> list[ET.Element]:
    if el is None:
        return []
    return [c for c in el if _ln(c.tag) == name]


def _desc(el: ET.Element | None, name: str) -> ET.Element | None:
    """후손 중 localname 일치하는 첫 요소."""
    if el is None:
        return None
    for x in el.iter():
        if x is not el and _ln(x.tag) == name:
            return x
    return None


def _desc_all(el: ET.Element, name: str) -> list[ET.Element]:
    return [x for x in el.iter() if x is not el and _ln(x.tag) == name]


def _elem_to_dict(rec: ET.Element) -> dict[str, Any]:
    """레코드 하위 leaf 텍스트/주요 속성을 평탄 dict 로 보존(raw)."""
    d: dict[str, Any] = {}
    for el in rec.iter():
        if el is rec:
            continue
        key = _ln(el.tag)
        val = _text(el)
        for ak, av in el.attrib.items():
            d.setdefault(f"{key}@{_ln(ak)}", av)
        if not val:
            continue
        if key in d:
            d[key] = d[key] + [val] if isinstance(d[key], list) else [d[key], val]
        else:
            d[key] = val
    return d


def _apply_titles(tg: ET.Element | None, a: Article) -> None:
    titles = _children(tg, "article-title")
    for t in titles:
        lang = t.attrib.get("lang")
        if lang == "english":
            a.title_en = _text(t)
        elif lang == "original":
            a.title = _text(t)
        elif lang == "foreign" and not a.title_en:
            a.title_en = _text(t)
    if not a.title and titles:
        a.title = _text(titles[0])


def _split_creators(val: str) -> list[str]:
    return [p.strip() for p in val.split(";") if p.strip()]


# ── 공통 에러 ────────────────────────────────────────────────────────────────
class ParseError(RuntimeError):
    pass


# ── REST ────────────────────────────────────────────────────────────────────
def _parse_xml(xml_text: str) -> ET.Element:
    """ET.fromstring 래퍼 — 파싱 실패를 ParseError 로 매핑(원시 ET.ParseError 누출 방지)."""
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ParseError(f"XML 파싱 실패: {e}") from e


def check_rest_error(root: ET.Element) -> None:
    """성공 응답엔 outputData 가 있다. 없으면 에러 응답으로 보고 본문을 담아 예외.

    (화이트리스트 의존 없이 'outputData 부재 = 에러' 로 판정 — 미등록 에러문구·신규 에러도 포착.)

    🔴 **`inputData` 는 반드시 제외한다 — 거기에 인증키가 들어 있다.**
       KCI 오류 봉투는 요청을 그대로 되돌려주므로(`<inputData><key>…`), 전 요소 텍스트를
       이어붙이면 **인증키가 예외 메시지에 실려 `_safe` 를 타고 MCP 응답까지 나간다**
       (2026-08-12 실제 HTTP 왕복으로 재현: `{"error": "<키> articleSearch …"}`).
       이 저장소는 `raise_for_status()` 가 URL 을 노출한다는 것을 알고 처음부터 피했는데,
       **누출은 그 문이 아니라 이 문에서 났다.** 전송 계층만 잠그는 것으로는 부족하다.
       되돌아온 요청 에코는 진단 가치도 없다(우리가 보낸 값이다).
       ※ 2차 방어로 client 가 인증키 문자열을 한 번 더 지운다(`KciClient._scrub`) —
         오류 문구 자체에 키가 박혀 오는 경우까지 덮기 위해서다.
    """
    if _desc(root, "outputData") is not None:
        return
    skip = {id(e) for node in root.iter() if _ln(node.tag) == "inputData"
            for e in node.iter()}
    joined = " ".join((e.text or "").strip() for e in root.iter()
                      if id(e) not in skip and (e.text or "").strip())
    raise ParseError(joined[:300] or "KCI REST 오류 응답(outputData 없음)")


# articleDetail <referenceInfo><reference> 의 하위 요소명 → 정규화 키.
# ⚠️ **API 원본 철자를 그대로 쓴다** — `isseue`·`pubilisher`·`pubi-year` 는 KCI 쪽 오타이며
#    추정으로 `issue`·`publisher`·`pub-year` 를 쓰면 값이 통째로 비어버린다(2026-08-11 라이브 확인).
_REF_FIELD_MAP = {
    "title": "title", "author": "author", "journal-name": "journal",
    "pubilisher": "publisher", "pubi-year": "pub_year",
    "volume": "volume", "isseue": "issue", "page": "page",
}


def _references_from_rest_record(rec: ET.Element) -> list[dict[str, str]]:
    """<referenceInfo> → 참고문헌 목록. 이 논문이 **인용한** 쪽이다.

    `arti-id` 는 KCI 에 등재된 참고문헌에만 붙는다(단행본·보고서·해외문헌 등은 없음).
    이 값이 인용 네트워크 구성의 유일한 연결고리다 — 없으면 텍스트 대조밖에 못 한다.
    """
    ri = _child(rec, "referenceInfo")
    if ri is None:
        return []
    out: list[dict[str, str]] = []
    for r in _children(ri, "reference"):
        d: dict[str, str] = {
            "arti_id": r.attrib.get("arti-id", ""),      # 빈 문자열 = KCI 미연결
            "refebibl_id": r.attrib.get("refebibl-id", ""),
            "type_code": r.attrib.get("type-code", ""),
            "type_name": r.attrib.get("type-name", ""),
        }
        for ch in r:
            key = _REF_FIELD_MAP.get(_ln(ch.tag))
            if key:
                d[key] = _text(ch)
        out.append(d)
    return out


def _article_from_rest_record(rec: ET.Element) -> Article:
    a = Article(source="rest")
    ji = _child(rec, "journalInfo")
    if ji is not None:
        a.journal = _text(_child(ji, "journal-name"))
        a.issn = _text(_child(ji, "issn"))
        a.publisher = _text(_child(ji, "publisher-name"))
        a.pub_year = _text(_child(ji, "pub-year"))
        a.pub_mon = _text(_child(ji, "pub-mon"))
        a.volume = _text(_child(ji, "volume"))
        a.issue = _text(_child(ji, "issue"))
    ai = _child(rec, "articleInfo")
    if ai is not None:
        a.arti_id = ai.attrib.get("article-id", "")
        a.categories = _text(_child(ai, "article-categories"))
        _apply_titles(_child(ai, "title-group"), a)
        ag = _child(ai, "author-group")
        if ag is not None:
            authors: list[str] = []
            for au in _children(ag, "author"):
                nm = _text(au)
                if not nm:  # articleDetail: 중첩 name/institution
                    name = _text(_child(au, "name"))
                    inst = _text(_child(au, "institution"))
                    nm = f"{name}({inst})" if inst else name
                if nm:
                    authors.append(nm)
            a.authors = authors
        # 초록: articleSearch=abstract-group, articleDetail=직속 abstract
        abg = _child(ai, "abstract-group")
        abs_els = _children(abg, "abstract") if abg is not None else _children(ai, "abstract")
        for ab in abs_els:
            if ab.attrib.get("lang") == "english":
                a.abstract_en = _text(ab)
            else:
                a.abstract = _text(ab)
        kg = _child(ai, "keyword-group")
        if kg is not None:
            a.keywords = [_text(k) for k in _children(kg, "keyword") if _text(k)]
        a.doi = _text(_child(ai, "doi"))
        a.uci = _text(_child(ai, "uci"))
        cc = _child(ai, "citation-count")
        if cc is not None:
            a.citation_count = _text(cc) or cc.attrib.get("kci", "")
        a.url = _text(_child(ai, "url"))
    a.references = _references_from_rest_record(rec)  # articleDetail 에만 존재
    a.raw = _elem_to_dict(rec)
    return a


def parse_rest_articles(xml_text: str) -> tuple[int, list[Article]]:
    root = _parse_xml(xml_text)
    check_rest_error(root)
    total = 0
    res = _desc(root, "result")
    if res is not None:
        t = _child(res, "total")
        if t is not None and _text(t).isdigit():
            total = int(_text(t))
    out = _desc(root, "outputData")
    scope = out if out is not None else root
    arts: list[Article] = []
    for rec in _desc_all(scope, "record"):
        if _child(rec, "articleInfo") is None and _child(rec, "journalInfo") is None:
            continue  # 참고문헌 레코드 등은 건너뜀
        arts.append(_article_from_rest_record(rec))
    return total, arts


def parse_rest_references(xml_text: str) -> tuple[int, list[dict[str, str]]]:
    root = _parse_xml(xml_text)
    check_rest_error(root)
    total = 0
    res = _desc(root, "result")
    if res is not None:
        t = _child(res, "total")
        if t is not None and _text(t).isdigit():
            total = int(_text(t))
    out = _desc(root, "outputData")
    scope = out if out is not None else root
    refs: list[dict[str, str]] = []
    for rec in _desc_all(scope, "record"):
        if list(rec):  # 자식 있는 record(논문 레코드)는 제외
            continue
        refs.append({"article_id": rec.attrib.get("article-id", ""), "text": _text(rec)})
    return total, refs


def parse_rest_citation(xml_text: str) -> tuple[int, list[dict[str, Any]]]:
    root = _parse_xml(xml_text)
    check_rest_error(root)
    total = 0
    res = _desc(root, "result")
    if res is not None:
        t = _child(res, "total")
        if t is not None and _text(t).isdigit():
            total = int(_text(t))
    out = _desc(root, "outputData")
    scope = out if out is not None else root
    rows: list[dict[str, Any]] = []
    for rec in _desc_all(scope, "record"):
        d = _elem_to_dict(rec)
        ji = _child(rec, "journalInfo")
        if ji is not None and ji.attrib.get("journal-id"):
            d["journal-id"] = ji.attrib["journal-id"]
        rows.append(d)
    return total, rows


# ── OAI-PMH ──────────────────────────────────────────────────────────────────
class OaiError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def check_oai_error(root: ET.Element) -> None:
    err = _desc(root, "error")
    if err is not None:
        raise OaiError(err.attrib.get("code", "error"), _text(err) or "OAI 오류")


def _article_from_oai_dc(dc: ET.Element) -> Article:
    a = Article(source="oai")
    for ch in dc:
        name = _ln(ch.tag)
        val = _text(ch)
        lang = ch.attrib.get("lang")
        typ = ch.attrib.get("type")
        if name == "title":
            if lang == "english":
                a.title_en = val
            elif not a.title:
                a.title = val
        elif name == "creator":
            a.authors.extend(_split_creators(val))
        elif name == "subject":
            if not a.categories:
                a.categories = val
        elif name == "identifier":
            if typ == "artiId":
                a.arti_id = val
            elif typ == "doi":
                a.doi = val
            elif typ == "uci":
                a.uci = val
            elif typ == "citedCnt":
                a.citation_count = val
            elif typ == "journalInfo":
                a.journal = val.split(",")[0].strip()
                if ch.attrib.get("issn"):
                    a.issn = ch.attrib["issn"]
        elif name == "description":
            if lang == "english":
                a.abstract_en = val
            elif not a.abstract:
                a.abstract = val
        elif name == "publisher":
            a.publisher = val
        elif name == "date" and val:
            m = re.match(r"(\d{4})\D*(\d{1,2})?", val)  # YYYY / YYYY-MM / YYYYMM 등 변형 견고
            if m:
                a.pub_year = m.group(1)
                a.pub_mon = m.group(2).zfill(2) if m.group(2) else ""
        elif name == "url":
            a.url = val
    return a


def _article_from_oai_kci(kci: ET.Element) -> Article:
    a = Article(source="oai")
    ji = _child(kci, "journalInfo")
    if ji is not None:
        a.journal = _text(_child(ji, "journal-name"))
        a.issn = _text(_child(ji, "pissn")) or _text(_child(ji, "eissn"))
        a.publisher = _text(_child(ji, "publisher-name"))
        a.pub_year = _text(_child(ji, "pub-year"))
        a.pub_mon = _text(_child(ji, "pub-mon"))
        a.volume = _text(_child(ji, "volume"))
        a.issue = _text(_child(ji, "issue"))
    ai = _child(kci, "articleInfo")
    if ai is not None:
        a.arti_id = ai.attrib.get("article-id", "")
        a.categories = _text(_child(ai, "article-categories"))
        _apply_titles(_child(ai, "title-group"), a)
        # 저자: author-name(이름+소속 분리) 우선, 없으면 author-group
        an = _child(ai, "author-name")
        if an is not None:
            for au in _children(an, "author"):
                name = _text(_child(au, "name"))
                aff = _text(_child(au, "affiliation"))
                if name:
                    a.authors.append(f"{name}({aff})" if aff else name)
        if not a.authors:
            ag = _child(ai, "author-group")
            a.authors = [_text(x) for x in _children(ag, "author") if _text(x)]
        abg = _child(ai, "abstract-group")
        for ab in _children(abg, "abstract"):
            if ab.attrib.get("lang") == "english":
                a.abstract_en = _text(ab)
            else:
                a.abstract = _text(ab)
        a.doi = _text(_child(ai, "doi"))
        a.uci = _text(_child(ai, "uci"))
        a.citation_count = _text(_child(ai, "citation-count"))
        a.url = _text(_child(ai, "url"))
    return a


def parse_oai_records(xml_text: str) -> tuple[list[Article], str | None]:
    """ListRecords/GetRecord 응답 → (Article 목록, resumptionToken|None)."""
    root = _parse_xml(xml_text)
    check_oai_error(root)
    arts: list[Article] = []
    for rec in _desc_all(root, "record"):
        meta = _child(rec, "metadata")
        art: Article | None = None
        if meta is not None:
            # metadata 직속 자식만 검사(후손 over-match 방지): oai_kci 래퍼/oai_dc:dc 래퍼 모두 직속
            kci = _child(meta, "oai_kci")
            dc = _child(meta, "dc")
            if kci is not None:
                art = _article_from_oai_kci(kci)
            elif dc is not None:
                art = _article_from_oai_dc(dc)
        if art is None:
            continue
        hdr = _child(rec, "header")
        if hdr is not None:
            art.raw["oai_identifier"] = _text(_child(hdr, "identifier"))
            art.raw["datestamp"] = _text(_child(hdr, "datestamp"))
            art.raw["setSpec"] = _text(_child(hdr, "setSpec"))
        arts.append(art)
    rt = _desc(root, "resumptionToken")
    token = _text(rt) if rt is not None else None
    return arts, (token or None)


def parse_oai_identify(xml_text: str) -> dict[str, str]:
    root = _parse_xml(xml_text)
    check_oai_error(root)
    idn = _desc(root, "Identify") or root
    keys = ["repositoryName", "baseURL", "protocolVersion", "adminEmail",
            "earliestDatestamp", "deletedRecord", "granularity"]
    return {k: _text(_desc(idn, k)) for k in keys}


def parse_oai_sets(xml_text: str) -> list[dict[str, str]]:
    root = _parse_xml(xml_text)
    check_oai_error(root)
    return [{"setSpec": _text(_child(s, "setSpec")), "setName": _text(_child(s, "setName"))}
            for s in _desc_all(root, "set")]


def parse_oai_formats(xml_text: str) -> list[dict[str, str]]:
    root = _parse_xml(xml_text)
    check_oai_error(root)
    return [{"metadataPrefix": _text(_child(f, "metadataPrefix")),
             "schema": _text(_child(f, "schema")),
             "metadataNamespace": _text(_child(f, "metadataNamespace"))}
            for f in _desc_all(root, "metadataFormat")]


def parse_oai_identifiers(xml_text: str) -> tuple[list[dict[str, str]], str | None]:
    root = _parse_xml(xml_text)
    check_oai_error(root)
    headers = [{"identifier": _text(_child(h, "identifier")),
                "datestamp": _text(_child(h, "datestamp")),
                "setSpec": _text(_child(h, "setSpec"))}
               for h in _desc_all(root, "header")]
    rt = _desc(root, "resumptionToken")
    return headers, (_text(rt) if rt is not None else None) or None
