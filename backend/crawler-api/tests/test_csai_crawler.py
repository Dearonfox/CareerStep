from unittest.mock import MagicMock, patch

from csai_crawler import categorize, fetch_article_list

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
          <strong>2026년 하반기 신입 채용 공고</strong>
        </a>
      </td>
      <td class="_artclTdRdate">2026.06.18</td>
    </tr>
  </tbody>
</table>
</body></html>
"""


def test_categorize_matches_known_keywords():
    assert categorize("2026년 상반기 신입 공채 안내") == "채용공고"
    assert categorize("백엔드 개발 인턴 모집") == "인턴십"
    assert categorize("AI 해커톤 참가자 모집") == "공모전"
    assert categorize("여름 방학 부트캠프 특강") == "캠프/특강"
    assert categorize("국가장학금 신청 안내") == "장학금"
    assert categorize("교내 자원봉사 모집 안내") == "봉사활동"


def test_categorize_falls_back_to_etc_for_unmatched_title():
    assert categorize("학과 행사 일정 변경 안내") == "기타"


def test_categorize_is_case_insensitive():
    assert categorize("Backend Internship Program") == "인턴십"


@patch("csai_crawler.requests.post")
def test_fetch_article_list_excludes_headline_rows(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    articles = fetch_article_list("취업정보", "4930", page=1)

    # headline 클래스가 붙은 상단 고정 공지는 제외되어야 함
    assert len(articles) == 2
    assert all(a["board_code"] == "4930" for a in articles)


@patch("csai_crawler.requests.post")
def test_fetch_article_list_parses_title_id_and_date(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    articles = fetch_article_list("취업정보", "4930", page=1)
    first = next(a for a in articles if a["article_id"] == "394268")

    assert first["title"] == "[WISET] 2026년 여성과학기술인 커리어 리부트 프로그램"
    assert first["post_date"] == "2026.06.19"
    assert first["detail_url"] == "https://csai.jbnu.ac.kr/bbs/csai/4930/394268/artclView.do"


@patch("csai_crawler.requests.post")
def test_fetch_article_list_sends_post_with_page_param(mock_post):
    mock_response = MagicMock()
    mock_response.text = LIST_HTML
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    fetch_article_list("취업정보", "4930", page=3)

    _, kwargs = mock_post.call_args
    assert kwargs["data"] == {"page": "3"}


@patch("csai_crawler.requests.post")
def test_fetch_article_list_returns_empty_on_request_failure(mock_post):
    mock_post.side_effect = Exception("network error")

    articles = fetch_article_list("취업정보", "4930", page=1)

    assert articles == []
