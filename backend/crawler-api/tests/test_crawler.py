from bs4 import BeautifulSoup

from crawler import clean_url, parse_job_row

JOB_ROW_HTML = """
<tr data-gno="123456" class="devloopArea">
  <td class="tplCo"><a href="/co/123">테스트회사</a></td>
  <td class="tplTit">
    <strong><a href="/Recruit/GI_Read/123456">백엔드 개발자 채용</a></strong>
    <p class="etc">
      <span class="cell">경력 3년↑</span>
      <span class="cell">대졸↑</span>
      <span class="cell">서울 강남구</span>
      <span class="cell">정규직</span>
    </p>
    <p class="dsc">Python, FastAPI, MySQL</p>
  </td>
  <td class="odd">
    <span class="time">06/19</span>
    <span class="date">06/30</span>
  </td>
</tr>
"""


def test_clean_url_passes_through_absolute_url():
    assert clean_url("https://example.com/a") == "https://example.com/a"


def test_clean_url_joins_relative_path():
    assert clean_url("/Recruit/GI_Read/1") == "https://www.jobkorea.co.kr/Recruit/GI_Read/1"


def test_clean_url_handles_empty_input():
    assert clean_url("") == ""
    assert clean_url(None) == ""


def test_parse_job_row_extracts_all_fields():
    row = BeautifulSoup(JOB_ROW_HTML, "html.parser").select_one("tr")
    parsed = parse_job_row(row, "백엔드개발자")

    assert parsed["job_id"] == "123456"
    assert parsed["category"] == "백엔드개발자"
    assert parsed["company_name"] == "테스트회사"
    assert parsed["title"] == "백엔드 개발자 채용"
    assert parsed["meta"]["experience_level"] == "경력 3년↑"
    assert parsed["meta"]["location"] == "서울 강남구"
    assert parsed["meta"]["employment_type"] == "정규직"
    assert parsed["tags"] == ["Python", "FastAPI", "MySQL"]
    assert parsed["post_date_raw"] == "06/19"
    assert parsed["deadline_raw"] == "06/30"


def test_parse_job_row_returns_none_without_job_id():
    row = BeautifulSoup("<tr><td>no id here</td></tr>", "html.parser").select_one("tr")
    assert parse_job_row(row, "백엔드개발자") is None
