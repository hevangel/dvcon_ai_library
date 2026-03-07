from backend.services.tei_parser import parse_tei_document


SAMPLE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Structured Verification Flows for DVCon</title>
      </titleStmt>
      <sourceDesc>
        <biblStruct>
          <analytic>
            <author>
              <persName>
                <forename>Alice</forename>
                <surname>Example</surname>
              </persName>
              <affiliation>
                <orgName>Example Semiconductor</orgName>
                <address>
                  <settlement>Austin</settlement>
                  <country>USA</country>
                </address>
              </affiliation>
              <email>alice@example.com</email>
            </author>
            <author>
              <persName>
                <forename>Bob</forename>
                <surname>Verifier</surname>
              </persName>
              <affiliation>
                <orgName>Verification Labs</orgName>
              </affiliation>
            </author>
          </analytic>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract>
        <p>This paper improves metadata extraction quality for technical PDFs.</p>
      </abstract>
    </profileDesc>
  </teiHeader>
  <text>
    <back>
      <listBibl>
        <biblStruct>
          <analytic>
            <title level="a">Reference Paper One</title>
            <author>
              <persName>
                <forename>Carol</forename>
                <surname>Writer</surname>
              </persName>
            </author>
          </analytic>
          <monogr>
            <title level="j">IEEE Design Journal</title>
            <imprint>
              <date when="2024"/>
            </imprint>
          </monogr>
          <idno type="DOI">10.1000/example</idno>
        </biblStruct>
      </listBibl>
    </back>
  </text>
</TEI>
"""


def test_parse_tei_document_extracts_structured_metadata() -> None:
    document = parse_tei_document(SAMPLE_TEI)

    assert document.title == "Structured Verification Flows for DVCon"
    assert "metadata extraction quality" in (document.abstract or "")
    assert [author.full_name for author in document.authors] == ["Alice Example", "Bob Verifier"]
    assert "Example Semiconductor, Austin, USA" in document.affiliations
    assert len(document.references) == 1
    assert document.references[0].normalized_title == "Reference Paper One"
    assert document.references[0].publication_year == 2024
    assert document.references[0].doi == "10.1000/example"
