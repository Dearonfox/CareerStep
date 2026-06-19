"""
전북대학교 컴퓨터인공지능학부 게시판 크롤러
대상: 취업정보(4930), 일반공지(4926), 학과소식(4927)
"""

import re
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://csai.jbnu.ac.kr"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

BOARDS = {
    "취업정보": "4930",
    "일반공지": "4926",
    "학과소식": "4927",
}

# 키워드 기반 카테고리 분류
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("채용공고",  ["채용", "공채", "신입", "경력", "정규직", "계약직", "모집공고", "구인", "JOB"]),
    ("인턴십",   ["인턴", "intern"]),
    ("공모전",   ["공모전", "공모", "대회", "챌린지", "해커톤", "경진", "contest", "competition", "hackathon"]),
    ("캠프/특강", ["캠프", "특강", "세미나", "강연", "강의", "워크샵", "workshop", "camp", "부트캠프"]),
    ("교육/프로그램", ["교육", "프로그램", "과정", "수료", "training", "커리큘럼", "멘토"]),
    ("장학금",   ["장학", "scholarship"]),
    ("봉사활동", ["봉사", "자원봉사", "volunteer"]),
]


def categorize(title: str) -> str:
    lower = title.lower()
    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in lower:
                return category
    return "기타"


def _post_list_page(board_code: str, page: int) -> BeautifulSoup:
    """K2Web 게시판은 페이지네이션을 POST로 처리하므로 공통 요청 함수로 분리"""
    url = f"{BASE_URL}/bbs/csai/{board_code}/artclList.do"
    data = {"page": str(page)}
    resp = requests.post(url, data=data, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _get_total_pages(board_code: str) -> int:
    try:
        soup = _post_list_page(board_code, 1)

        # _paging 영역의 "_last" 링크: javascript:page_link('98') → 98페이지
        last_tag = soup.select_one("div._paging a._last")
        if last_tag:
            m = re.search(r"page_link\('(\d+)'\)", last_tag.get("href", ""))
            if m:
                return int(m.group(1))

        # "_last" 없으면 ul 안 페이지 번호 링크에서 최대값
        page_nums = []
        for tag in soup.select("div._paging ul a"):
            m = re.search(r"page_link\('(\d+)'\)", tag.get("href", ""))
            if m:
                page_nums.append(int(m.group(1)))
        if page_nums:
            return max(page_nums)

        return 1
    except Exception as e:
        print(f"  [경고] 총 페이지 수 파악 실패: {e}")
        return 1


def fetch_article_list(board_name: str, board_code: str, page: int = 1) -> list[dict]:
    try:
        soup = _post_list_page(board_code, page)
    except Exception as e:
        print(f"  [오류] 목록 요청 실패 (page {page}): {e}")
        return []

    articles = []

    # K2Web 실제 구조: table.artclTable tbody tr._artclEven / tr._artclOdd
    # headline 클래스 행은 상단 고정 공지이므로 제외
    rows = [
        tr for tr in soup.select("table.artclTable tbody tr")
        if "headline" not in tr.get("class", [])
    ]

    for row in rows:
        # 제목/링크: td._artclTdTitle a
        title_tag = row.select_one("td._artclTdTitle a")
        if not title_tag:
            continue

        # <strong> 텍스트만 사용 (없으면 전체 텍스트)
        strong = title_tag.find("strong")
        title = strong.get_text(strip=True) if strong else title_tag.get_text(strip=True)

        href = title_tag.get("href", "")

        # article_id: /bbs/csai/4930/394268/artclView.do
        m = re.search(r"/(\d{5,})/artclView", href)
        if not m:
            continue
        article_id = m.group(1)

        # 날짜: td._artclTdRdate
        date_td = row.select_one("td._artclTdRdate")
        post_date = date_td.get_text(strip=True) if date_td else ""

        articles.append({
            "board_name": board_name,
            "board_code": board_code,
            "article_id": article_id,
            "title": title,
            "post_date": post_date,
            "detail_url": f"{BASE_URL}/bbs/csai/{board_code}/{article_id}/artclView.do",
        })

    return articles


def fetch_article_detail(article: dict) -> dict:
    try:
        resp = requests.get(article["detail_url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return {**article, "content": "", "attachments": [], "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")

    # 본문 추출 (K2Web 다중 셀렉터)
    content_div = (
        soup.select_one("#artclViewBody")
        or soup.select_one(".board-view-content")
        or soup.select_one(".view-con")
        or soup.select_one(".fr-view")
        or soup.select_one(".ck-content")
    )
    content = content_div.get_text(separator="\n", strip=True) if content_div else ""

    # 첨부파일 추출
    attachments = []
    for a_tag in soup.select("a[href*='atchFile'], a[href*='fileDown'], .file-list a"):
        fname = a_tag.get_text(strip=True)
        fhref = a_tag.get("href", "")
        if fname:
            attachments.append({"name": fname, "url": BASE_URL + fhref if fhref.startswith("/") else fhref})

    return {
        **article,
        "content": content[:8000],
        "attachments": attachments,
        "error": None,
    }


def crawl_board(
    board_name: str,
    board_code: str,
    max_pages: int | None = None,
    delay: float = 1.0,
) -> list[dict]:
    """단일 게시판 전체 크롤링"""
    total_pages = _get_total_pages(board_code)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    print(f"  [{board_name}] 총 {total_pages}페이지 수집 시작")
    all_articles = []

    for page in range(1, total_pages + 1):
        articles = fetch_article_list(board_name, board_code, page)
        print(f"    페이지 {page}/{total_pages} → {len(articles)}건")

        for article in articles:
            detailed = fetch_article_detail(article)
            detailed["category"] = categorize(article["title"])
            all_articles.append(detailed)
            time.sleep(delay * 0.3)  # 상세 요청 간 짧은 딜레이

        time.sleep(delay)

    return all_articles
