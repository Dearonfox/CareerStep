from datetime import date
from unittest.mock import MagicMock, patch

from crawler import (
    categorize,
    clean_url,
    fetch_article_detail,
    fetch_article_list,
    fetch_board_articles,
    is_excluded_title,
    is_relevant_activity,
    parse_post_date,
)

# 실제 DevTools에서 확인한 K2Web 게시판 목록 구조를 그대로 재현한 샘플 HTML
LIST_HTML = """
<html><body>
<table class="artclTable artclHorNum1">
  <tbody>
    <tr class="headline _artclEven">
      <td class="_artclTdNum"></td>
      <td class="_artclTdTitle">
        <a href="/bbs/csai/4928/383477/artclView.do" class="artclLinkView">
          <strong>학년별 비교과(취업역량) 관련 안내</strong>
        </a>
      </td>
      <td class="_artclTdRdate">2026.03.05</td>
    </tr>
    <tr>
      <td class="_artclTdNum">972</td>
      <td class="_artclTdTitle">
        <a href="/bbs/csai/4930/394268/artclView.do" onclick="jf_viewArtcl('csai','4930','394268')" class="artclLinkView">
          <strong>[WISET] 2026년 여성과학기술인 커리어 리부트 프로그램</strong>
          <span class="newArtcl">새글</span>
        </a>
      </td>
      <td class="_artclTdWriter"></td>
      <td class="_artclTdRdate">2026.06.19</td>
      <td class="_artclTdAtchFile"></td>
      <td class="_artclTdAccess"></td>
    </tr>
    <tr>
      <td class="_artclTdNum">971</td>
      <td class="_artclTdTitle">
        <a href="/bbs/csai/4930/394275/artclView.do" class="artclLinkView">
          <strong>2026년 하반기 백엔드 개발 인턴 모집</strong>
        </a>
      </td>
      <td class="_artclTdRdate">2026.06.18</td>
    </tr>
    <tr>
      <td class="_artclTdNum">970</td>
      <td class="_artclTdTitle">
        <a href="/bbs/csai/4930/394260/artclView.do" class="artclLinkView">
          <strong>2026학년도 1학기 수강신청 안내</strong>
        </a>
      </td>
      <td class="_artclTdRdate">2026.06.17</td>
    </tr>
    <tr>
      <td class="_artclTdNum">969</td>
      <td class="_artclTdTitle">
        <a href="/bbs/csai/4930/394255/artclView.do" class="artclLinkView">
          <strong>학과 행사 일정 변경 안내</strong>
        </a>
      </td>
      <td class="_artclTdRdate">2026.06.16</td>
    </tr>
  </tbody>
</table>
</body></html>
"""

DETAIL_HTML_TEXT = """
<html><body>
<div id="artclViewBody">
  <p>모집 기간: 2026.06.19 ~ 2026.06.30</p>
  <p>지원 대상: 컴퓨터인공지능학부 재학생</p>
  <table><tr><td>구분</td><td>내용</td></tr><tr><td>장소</td><td>온라인</td></tr></table>
</div>
</body></html>
"""

DETAIL_HTML_IMAGE_ONLY = """
<html><body>
<div id="artclViewBody">
  <img src="/upload/poster1.png" />
  <img src="/upload/poster2.png" />
</div>
</body></html>
"""


def test_categorize_matches_known_keywords():
    assert categorize("백엔드 개발 인턴 모집") == "인턴십"
    assert categorize("AI 해커톤 참가자 모집") == "공모전"
    assert categorize("여름 방학 부트캠프 특강") == "캠프/특강"
    assert categorize("국가장학금 신청 안내") == "장학금"
    assert categorize("교내 자원봉사 모집 안내") == "봉사활동"
    assert categorize("2026 글로벌 교환학생 프로그램") == "교육/프로그램"
    assert categorize("학과 서포터즈 모집") == "서포터즈/홍보대사"
    assert categorize("채용설명회 개최 안내") == "취업연계행사"
    assert categorize("학생 교류회 네트워킹 행사") == "교류/네트워킹"


def test_categorize_no_longer_classifies_plain_job_postings():
    # 채용공고는 일반 크롤러(JobKorea)에서 수집하므로 여기서는 카테고리에서 제외됨
    assert categorize("2026년 상반기 신입 공채 안내") == "기타"


def test_categorize_falls_back_to_etc_for_unmatched_title():
    assert categorize("학과 행사 일정 변경 안내") == "기타"


def test_is_excluded_title_filters_administrative_notices():
    assert is_excluded_title("2026학년도 1학기 수강신청 안내") is True
    assert is_excluded_title("휴학 및 복학 신청 기간 안내") is True
    assert is_excluded_title("2026년 하반기 백엔드 개발 인턴 모집") is False


def test_is_relevant_activity_requires_category_match():
    assert is_relevant_activity("2026년 하반기 백엔드 개발 인턴 모집") is True
    assert is_relevant_activity("AI 해커톤 참가자 모집") is True
    # 단순 채용공고는 카테고리에서 제외되어 탈락 (JobKorea 크롤러가 별도로 수집)
    assert is_relevant_activity("2026년 하반기 신입 채용 공고") is False
    # 제외 키워드에 걸리면 탈락
    assert is_relevant_activity("2026학년도 1학기 수강신청 안내") is False
    # 어떤 카테고리에도 안 걸리는 모호한 공지는 "기타"로 분류되어 탈락
    assert is_relevant_activity("학과 행사 일정 변경 안내") is False


@patch("crawler.requests.post")
def test_fetch_article_list_excludes_administrative_titles(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    articles = fetch_article_list("취업정보", "4930", page=1)["articles"]

    titles = [a["title"] for a in articles]
    assert not any("수강신청" in title for title in titles)


@patch("crawler.requests.post")
def test_fetch_article_list_excludes_uncategorized_titles(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    articles = fetch_article_list("취업정보", "4930", page=1)["articles"]

    titles = [a["title"] for a in articles]
    assert not any("행사 일정 변경" in title for title in titles)
    # 카테고리에 매칭되는 것만 남아야 함 (WISET 프로그램, 신입 채용 공고)
    assert len(articles) == 2


def test_parse_post_date_parses_valid_format():
    assert parse_post_date("2026.06.19") == date(2026, 6, 19)


def test_parse_post_date_returns_none_for_invalid_format():
    assert parse_post_date("") is None
    assert parse_post_date("invalid") is None
    assert parse_post_date(None) is None


@patch("crawler.requests.post")
def test_fetch_article_list_excludes_articles_older_than_cutoff(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    # 2026.06.18 이후만 허용 -> 2026.06.18(인턴 모집)은 포함, 그 이전 날짜는 제외
    result = fetch_article_list("취업정보", "4930", page=1, cutoff_date=date(2026, 6, 18))
    articles = result["articles"]

    dates = [a["post_date"] for a in articles]
    assert all(d >= "2026.06.18" for d in dates)
    assert result["oldest_date"] == date(2026, 6, 16)


@patch("crawler.requests.post")
def test_fetch_article_list_tracks_oldest_date_regardless_of_relevance(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    # 가장 오래된 행(수강신청 안내, 행사 일정 변경 안내)은 관련성 필터에 걸리지만
    # oldest_date 계산에는 포함되어야 함 (페이지 중단 판단의 기준이 되므로)
    result = fetch_article_list("취업정보", "4930", page=1)
    assert result["oldest_date"] == date(2026, 6, 16)


@patch("crawler.fetch_article_list")
@patch("crawler.get_total_pages")
def test_fetch_board_articles_stops_early_when_page_exceeds_cutoff(mock_total_pages, mock_fetch_list):
    mock_total_pages.return_value = 5

    # 1페이지는 기준일 이내, 2페이지부터는 전부 기준일보다 오래됨 -> 2페이지 처리 후 중단
    mock_fetch_list.side_effect = [
        {"articles": [{"title": "최신 공고"}], "oldest_date": date(2026, 6, 1)},
        {"articles": [], "oldest_date": date(2025, 1, 1)},
    ]

    articles = fetch_board_articles(
        "취업정보", "4930", delay=0, lookback_days=180
    )

    assert mock_fetch_list.call_count == 2
    assert len(articles) == 1


def test_clean_url_passes_through_absolute_url():
    assert clean_url("https://example.com/a") == "https://example.com/a"


def test_clean_url_joins_relative_path():
    assert clean_url("/upload/poster.png") == "https://csai.jbnu.ac.kr/upload/poster.png"


def test_clean_url_handles_empty_input():
    assert clean_url("") == ""
    assert clean_url(None) == ""


@patch("crawler.requests.post")
def test_fetch_article_list_excludes_headline_rows(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    articles = fetch_article_list("취업정보", "4930", page=1)["articles"]

    assert len(articles) == 2
    assert all(a["board_code"] == "4930" for a in articles)


@patch("crawler.requests.post")
def test_fetch_article_list_parses_title_id_and_date(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    articles = fetch_article_list("취업정보", "4930", page=1)["articles"]
    first = next(a for a in articles if a["article_id"] == "394268")

    assert first["title"] == "[WISET] 2026년 여성과학기술인 커리어 리부트 프로그램"
    assert first["post_date"] == "2026.06.19"
    assert first["detail_url"] == "https://csai.jbnu.ac.kr/bbs/csai/4930/394268/artclView.do"


@patch("crawler.requests.post")
def test_fetch_article_list_sends_post_with_page_param(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    fetch_article_list("취업정보", "4930", page=3)

    _, kwargs = mock_post.call_args
    assert kwargs["data"] == {"page": "3"}


@patch("crawler.requests.post")
def test_fetch_article_list_returns_empty_on_request_failure(mock_post):
    mock_post.side_effect = Exception("network error")

    result = fetch_article_list("취업정보", "4930", page=1)

    assert result["articles"] == []
    assert result["oldest_date"] is None


@patch("crawler.requests.get")
def test_fetch_article_detail_converts_text_to_markdown(mock_get):
    mock_response = MagicMock()
    mock_response.text = DETAIL_HTML_TEXT
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    article = {
        "board_name": "취업정보",
        "board_code": "4930",
        "article_id": "394268",
        "title": "테스트 공고",
        "post_date": "2026.06.19",
        "detail_url": "https://csai.jbnu.ac.kr/bbs/csai/4930/394268/artclView.do",
    }
    detail = fetch_article_detail(article)

    assert detail["is_image_job"] is False
    assert "모집 기간" in detail["detail_markdown"]
    assert detail["error_message"] is None


@patch("crawler.requests.get")
def test_fetch_article_detail_detects_image_only_post(mock_get):
    mock_response = MagicMock()
    mock_response.text = DETAIL_HTML_IMAGE_ONLY
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    article = {
        "board_name": "취업정보",
        "board_code": "4930",
        "article_id": "394268",
        "title": "이미지 공고",
        "post_date": "2026.06.19",
        "detail_url": "https://csai.jbnu.ac.kr/bbs/csai/4930/394268/artclView.do",
    }
    detail = fetch_article_detail(article)

    assert detail["is_image_job"] is True
    assert len(detail["image_urls"]) == 2
    assert detail["image_urls"][0] == "https://csai.jbnu.ac.kr/upload/poster1.png"


@patch("crawler.requests.get")
def test_fetch_article_detail_returns_error_message_on_request_failure(mock_get):
    mock_get.side_effect = Exception("timeout")

    article = {
        "board_name": "취업정보",
        "board_code": "4930",
        "article_id": "394268",
        "title": "오류 케이스",
        "post_date": "2026.06.19",
        "detail_url": "https://csai.jbnu.ac.kr/bbs/csai/4930/394268/artclView.do",
    }
    detail = fetch_article_detail(article)

    assert detail["error_message"] == "timeout"
    assert detail["detail_markdown"] == ""
