"""공식 가이드(PDF) 예제 기반 샘플 응답 XML — 파서 오프라인 검증용.

PDF 예시의 전각 따옴표(lang=“…”)·속성은 실제 응답 기준(표준 따옴표)으로 정규화해 작성.
"""

# ── REST articleSearch (KCI_API_GUIDE §1-3) ──────────────────────────────────
REST_ARTICLE_SEARCH = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData>
    <key>00000001</key><apiCode>articleSearch</apiCode>
    <title><![CDATA[컴퓨터]]></title><page>1</page><displayCount>10</displayCount>
  </inputData>
  <outputData>
    <result><total>3779</total></result>
    <record>
      <journalInfo>
        <journal-name>컴퓨터교육학회논문지</journal-name>
        <publisher-name>한국컴퓨터교육학회</publisher-name>
        <foreign-listed />
        <pub-year>2004</pub-year><pub-mon>09</pub-mon>
        <volume>8</volume><issue>3</issue>
      </journalInfo>
      <articleInfo article-id="ART001143784">
        <article-categories>컴퓨터교육</article-categories>
        <article-regularity>Y</article-regularity>
        <title-group>
          <article-title lang="original"><![CDATA[초등학교 컴퓨터 교과서에 나온 컴퓨터 용어 분석]]></article-title>
          <article-title lang="english"><![CDATA[An Analysis of Computer Terms]]></article-title>
        </title-group>
        <author-group>
          <author english="KIM KAP SU" orc-id="0000-0000-0000-0000">김갑수(서울교육대학교)</author>
          <author english="Myunghui Hong">홍명희(서울교육대학교)</author>
          <author>이순영(인천계산초등학교)</author>
        </author-group>
        <abstract-group>
          <abstract lang="original"><![CDATA[컴퓨터를 잘 활용하려면 컴퓨터 용어를 알아야 한다.]]></abstract>
          <abstract lang="english"><![CDATA[We must know computer terms to use.]]></abstract>
        </abstract-group>
        <fpage>433</fpage><lpage>448</lpage>
        <orte-open-yn>Y</orte-open-yn>
        <doi /><uci />
        <citation-count kci="4" wos="0">4</citation-count>
        <fwci create-dt="2023-07-26" fwci="0.0">0.0</fwci>
        <url><![CDATA[https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001143784]]></url>
        <verified>N</verified>
      </articleInfo>
    </record>
  </outputData>
</MetaData>
"""

# ── REST articleDetail (KCI_API_GUIDE §2) ────────────────────────────────────
REST_ARTICLE_DETAIL = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData><key>00000001</key><apiCode>articleDetail</apiCode><id>ART002358582</id></inputData>
  <outputData>
    <result><total>1</total></result>
    <record>
      <journalInfo journal-id="SER000004015">
        <issn>2383-5281</issn>
        <journal-name>한국융합학회논문지</journal-name>
        <publisher-name>한국융합학회</publisher-name>
        <kci-registration>등재</kci-registration>
        <foreign-registration />
        <pub-year>2018</pub-year><pub-mon>06</pub-mon><volume>8</volume><issue>6</issue>
      </journalInfo>
      <articleInfo article-id="ART002358582">
        <article-categories>공학 &gt; 컴퓨터학</article-categories>
        <article-regularity>Y</article-regularity>
        <article-language>한국어</article-language>
        <title-group>
          <article-title lang="original"><![CDATA[컴퓨터 학습을 통한 디지털 에이징]]></article-title>
          <article-title lang="english"><![CDATA[Digital Aging Through Computer Learning]]></article-title>
        </title-group>
        <author-group>
          <author author-id="CRT002007609" author-division="1" author-part="단독" orc-id="0000-0000-0000-0000">
            <name><![CDATA[김정진]]></name>
            <name-eng><![CDATA[KIM JUNG JIN]]></name-eng>
            <institution>백석대학교</institution>
          </author>
        </author-group>
        <abstract lang="original"><![CDATA[이 연구는 노인의 디지털 에이징 연구이다.]]></abstract>
        <keyword-group>
          <keyword><![CDATA[Digital aging]]></keyword>
          <keyword><![CDATA[Active aging]]></keyword>
          <keyword><![CDATA[Computer]]></keyword>
        </keyword-group>
        <fpage>297</fpage><lpage>304</lpage>
        <doi><![CDATA[http://dx.doi.org/10.35873/ajmahs.2018.8.6.026]]></doi>
        <citation-count kci="0" wos="0">0</citation-count>
        <url><![CDATA[https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002358582]]></url>
        <verified>Y</verified>
      </articleInfo>
      <!-- ⚠️ 실제 응답 구조(2026-08-11 라이브 확인). 공식 가이드 복구본 §2-2 에는 누락돼 있었다.
           원소명 오타(isseue / pubilisher / pubi-year)는 **API 원본 그대로**다 — 고쳐 쓰면 값이 빈다.
           arti-id 는 KCI 등재 참고문헌에만 붙는다(단행본·보고서 등에는 없음). -->
      <referenceInfo>
        <reference refebibl-id="REF077422048" arti-id="ART002687726" type-code="01" type-name="학술지(정기간행물)">
          <title><![CDATA[호네트의 인정이론적 정의관과 도덕교육]]></title>
          <author><![CDATA[고미숙]]></author>
          <journal-name><![CDATA[도덕윤리과교육]]></journal-name>
          <pubi-year>2021</pubi-year>
          <volume>70</volume>
          <isseue></isseue>
          <page>291-322</page>
        </reference>
        <reference refebibl-id="REF077422050" type-code="04" type-name="보고서">
          <title><![CDATA[대입제도 공정성 강화 방안]]></title>
          <author><![CDATA[교육부]]></author>
          <pubilisher><![CDATA[교육부]]></pubilisher>
          <pubi-year>2019</pubi-year>
          <page>-</page>
        </reference>
      </referenceInfo>
    </record>
  </outputData>
</MetaData>
"""

# ── REST referenceSearch (KCI_API_GUIDE §3) ──────────────────────────────────
REST_REFERENCES = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData><key>00000001</key><apiCode>referenceSearch</apiCode><title><![CDATA[컴퓨터]]></title></inputData>
  <outputData>
    <result><total>82557</total></result>
    <record article-id="ART002703100"><![CDATA[최유찬, 문학과 컴퓨터 게임, 인문과학 85집, 연세대 인문과학연구소, 2003. 12, 1쪽.]]></record>
    <record article-id="ART001917640"><![CDATA[조아미(1998). 청소년의 컴퓨터 경험에 따른 컴퓨터 불안. 한국청소년연구. 27. 17-41.]]></record>
  </outputData>
</MetaData>
"""

# ── REST citation (KCI_API_GUIDE §4) ─────────────────────────────────────────
REST_CITATION = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData><key>00000001</key><apiCode>citation</apiCode><years>2</years><year>2021</year></inputData>
  <outputData>
    <result><total>2678</total><year>2021</year><years>2년분</years></result>
    <record>
      <journalInfo journal-id="SER000002778">
        <journal-name>영유아교육과정연구</journal-name>
        <publisher-name>한국영유아교육과정학회</publisher-name>
        <major>사회과학</major>
        <url><![CDATA[https://www.kci.go.kr/kciportal/po/search/poCitaView.kci?sereId=SER000002778&year=2021]]></url>
      </journalInfo>
      <citationInfo>
        <impactFactor>8.167</impactFactor>
        <wosImpactFactor>0</wosImpactFactor>
        <exImpactFactor>8</exImpactFactor>
        <immediacyIndex>0.4</immediacyIndex>
        <selfCitedRate>2.04</selfCitedRate>
      </citationInfo>
    </record>
  </outputData>
</MetaData>
"""

# ── REST citationDetail (KCI_API_GUIDE §5) ───────────────────────────────────
REST_CITATION_DETAIL = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData><key>00000001</key><apiCode>citationDetail</apiCode><id>001223</id></inputData>
  <outputData>
    <result><total>1</total></result>
    <record>
      <journalInfo journal-id="001223">
        <registration><kci-registration>KCI 등재</kci-registration></registration>
        <journal-kor-name>현대유럽철학연구</journal-kor-name>
        <major>인문학 &gt; 철학 &gt; 서양철학</major>
        <issn>2093-4440</issn>
      </journalInfo>
      <journal-citation-index-history>
        <journal-citation-index year="2021">
          <impactFactor>0.61</impactFactor>
          <sjr>1.104</sjr>
        </journal-citation-index>
      </journal-citation-index-history>
    </record>
  </outputData>
</MetaData>
"""

# ── REST 에러 ────────────────────────────────────────────────────────────────
REST_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData><key>BAD</key><apiCode>articleSearch</apiCode></inputData>
  <error>등록되지 않은 key 입니다.</error>
</MetaData>
"""

# ── OAI ListRecords (oai_kci) ────────────────────────────────────────────────
OAI_LISTRECORDS_KCI = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <responseDate>2023-03-03T00:38:19Z</responseDate>
  <request verb="ListRecords">http://open.kci.go.kr/oai/request</request>
  <ListRecords>
    <record>
      <header>
        <identifier>oai:kci.go.kr:ARTI/914</identifier>
        <datestamp>2023-01-29</datestamp>
        <setSpec>ARTI</setSpec>
      </header>
      <metadata>
        <oai_kci xmlns="http://www.kci.go.kr/kciportal/OAI/">
          <journalInfo>
            <journal-name>대중서사연구</journal-name>
            <pissn>1738-3188</pissn><eissn/>
            <publisher-name>대중서사학회</publisher-name>
            <pub-year>2015</pub-year><pub-mon>04</pub-mon>
            <volume>21</volume><issue>1</issue><serno>34</serno>
          </journalInfo>
          <articleInfo article-id="ART001985846">
            <article-categories>학제간연구</article-categories>
            <article-regularity>Y</article-regularity>
            <title-group>
              <article-title lang="original">1930년대 기생-가정극 연구</article-title>
              <article-title lang="english">A Study on Kisaeng Domestic Dramas in 1930s</article-title>
            </title-group>
            <author-group><author>백현미(전남대학교)</author></author-group>
            <author-name>
              <author><name>백현미</name><affiliation>전남대학교</affiliation></author>
            </author-name>
            <abstract-group>
              <abstract lang="original">연애와 여성을 키워드로 한 대중 서사 연구.</abstract>
              <abstract lang="english">A study on popular narratives.</abstract>
            </abstract-group>
            <language>한국어</language><fpage>227</fpage><lpage>260</lpage>
            <orte-open-yn>Y</orte-open-yn>
            <doi>http://dx.doi.org/10.18856/jpn.2015.21.1.008</doi>
            <uci>G704-001717.2015.21.1.001</uci>
            <citation-count>0</citation-count>
            <url>https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001985846</url>
            <verified>Y</verified>
          </articleInfo>
        </oai_kci>
      </metadata>
    </record>
  </ListRecords>
  <resumptionToken>2023-01-01:2023-01-31:100:1014</resumptionToken>
</OAI-PMH>
"""

# ── OAI ListRecords (oai_dc) ─────────────────────────────────────────────────
OAI_LISTRECORDS_DC = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <responseDate>2023-03-03T00:30:03Z</responseDate>
  <request verb="ListRecords">http://open.kci.go.kr/oai/request</request>
  <ListRecords>
    <record>
      <header>
        <identifier>oai:kci.go.kr:ARTI/914</identifier>
        <datestamp>2023-01-29</datestamp><setSpec>ARTI</setSpec>
      </header>
      <metadata>
        <oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/">
          <dc:title lang="original">1930년대 기생-가정극 연구</dc:title>
          <dc:title lang="english">A Study on Kisaeng Domestic Dramas</dc:title>
          <dc:creator>백현미(전남대학교)</dc:creator>
          <dc:subject>학제간연구</dc:subject>
          <dc:identifier issn="1738-3188" type="journalInfo">대중서사연구, 21(1), 34, pp.227-260</dc:identifier>
          <dc:identifier type="artiId">ART001985846</dc:identifier>
          <dc:identifier type="citedCnt">0</dc:identifier>
          <dc:identifier type="doi">http://dx.doi.org/10.18856/jpn.2015.21.1.08</dc:identifier>
          <dc:description lang="original">연애와 여성을 키워드로 한 대중 서사.</dc:description>
          <dc:description lang="english">A study on popular narratives.</dc:description>
          <dc:publisher>대중서사학회</dc:publisher>
          <dc:date>2015-04</dc:date>
          <dc:type>Article</dc:type>
          <dc:url>https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001985846</dc:url>
          <dc:language>한국어</dc:language>
        </oai_dc:dc>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>
"""

# ── OAI 에러 ─────────────────────────────────────────────────────────────────
OAI_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <responseDate>2023-03-03T00:00:00Z</responseDate>
  <request>http://open.kci.go.kr/oai/request</request>
  <error code="badArgument">parameter format must have 'YYYY-MM-DD' format.</error>
</OAI-PMH>
"""
