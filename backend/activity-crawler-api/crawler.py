"""
전북대학교 컴퓨터인공지능학부 대외활동 게시판 크롤러
대상: 취업정보(4930), 일반공지(4926), 학과소식(4927)
"""

import re
import time
import urllib.parse
from datetime import date, datetime, timedelta

import html2text
import requests
from bs4 import BeautifulSoup

from config import BASE_URL, CATEGORY_RULES, EXCLUDE_KEYWORDS, HEADERS, RECRUIT_LOOKBACK_DAYS


def parse_post_date(value: str) -> date | None:
    """게시판에 표시되는 'YYYY.MM.DD' 형식의 날짜 문자열을 date로 변환. 실패 시 None."""
    try:
        return datetime.strptime(value.strip(), "%Y.%m.%d").date()
    except (ValueError, AttributeError):
        return None


def clean_url(url_path: str) -> str:
    if not url_path:
        return ""
    if url_path.startswith("http"):
        return url_path
    return urllib.parse.urljoin(BASE_URL, url_path)


def categorize(title: str) -> str:
    lower = title.lower()
    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in lower:
                return category
    return "기타"


def is_excluded_title(title: str) -> bool:
    """휴복학/수강신청/시간표 등 대외활동과 무관한 행정·학사 공지 제목인지 판별"""
    lower = title.lower()
    return any(kw.lower() in lower for kw in EXCLUDE_KEYWORDS)


def is_relevant_activity(title: str) -> bool:
    """
    대외활동 관련 게시글만 통과시킨다.
    - 제외 키워드(행정/학사 공지)에 걸리면 무조건 탈락
    - CATEGORY_RULES 키워드 중 하나도 매칭되지 않아 "기타"로 분류되면 탈락
      (카테고리에 안 걸리는 글은 대외활동인지 확신할 수 없으므로 보수적으로 제외)
    """
    if is_excluded_title(title):
        return False
    return categorize(title) != "기타"


def _post_list_page(board_code: str, page: int) -> BeautifulSoup:
    """K2Web 게시판은 페이지네이션을 POST로 처리"""
    url = f"{BASE_URL}/bbs/csai/{board_code}/artclList.do"
    resp = requests.post(url, data={"page": str(page)}, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def get_total_pages(board_code: str) -> int:
    try:
        soup = _post_list_page(board_code, 1)

        # _paging 영역의 "_last" 링크: javascript:page_link('98') → 98페이지
        last_tag = soup.select_one("div._paging a._last")
        if last_tag:
            m = re.search(r"page_link\('(\d+)'\)", last_tag.get("href", ""))
            if m:
                return int(m.group(1))

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


def fetch_article_list(board_name: str, board_code: str, page: int = 1, cutoff_date: date | None = None) -> dict:
    """
    게시판 목록 페이지에서 게시글 메타데이터(제목/날짜/링크) 수집.
    cutoff_date가 주어지면 그보다 오래된 게시글(이미 마감됐을 공고)은 결과에서 제외한다.

    반환값: {"articles": [...], "oldest_date": 이 페이지에서 발견된 가장 오래된 날짜 또는 None}
    페이지는 최신글이 먼저 나오는 순서이므로, oldest_date가 cutoff보다 오래되면
    호출 측에서 더 이상 다음 페이지를 수집하지 않아도 된다.
    """
    try:
        soup = _post_list_page(board_code, page)
    except Exception as e:
        print(f"  [오류] 목록 요청 실패 (page {page}): {e}")
        return {"articles": [], "oldest_date": None}

    articles = []
    oldest_date: date | None = None

    # 실제 게시글 행은 클래스가 없고, 상단 고정 공지만 "headline" 클래스를 가짐
    rows = [
        tr for tr in soup.select("table.artclTable tbody tr")
        if "headline" not in tr.get("class", [])
    ]

    for row in rows:
        title_tag = row.select_one("td._artclTdTitle a")
        if not title_tag:
            continue

        strong = title_tag.find("strong")
        title = strong.get_text(strip=True) if strong else title_tag.get_text(strip=True)

        date_td = row.select_one("td._artclTdRdate")
        post_date = date_td.get_text(strip=True) if date_td else ""
        parsed_date = parse_post_date(post_date)

        if parsed_date and (oldest_date is None or parsed_date < oldest_date):
            oldest_date = parsed_date

        # 마감됐을 가능성이 높은 오래된 글은 관련성과 무관하게 제외
        if cutoff_date and parsed_date and parsed_date < cutoff_date:
            continue

        # 대외활동 관련 카테고리에 매칭되지 않는 글은 목록 단계에서 바로 제외 (상세 요청도 아낌)
        if not is_relevant_activity(title):
            continue

        href = title_tag.get("href", "")
        m = re.search(r"/(\d{5,})/artclView", href)
        if not m:
            continue
        article_id = m.group(1)

        articles.append({
            "board_name": board_name,
            "board_code": board_code,
            "article_id": article_id,
            "title": title,
            "post_date": post_date,
            "detail_url": f"{BASE_URL}/bbs/csai/{board_code}/{article_id}/artclView.do",
        })

    return {"articles": articles, "oldest_date": oldest_date}


def fetch_article_detail(article: dict) -> dict:
    """
    게시글 상세 페이지를 요청하여 본문을 마크다운으로 정제하고,
    이미지 공고(본문이 거의 없고 이미지만 있는 경우) 여부를 판별하여 반환.
    잡코리아 크롤러의 fetch_job_detail과 동일한 방식.
    """
    result = {
        **article,
        "detail_markdown": "",
        "is_image_job": False,
        "image_urls": [],
        "attachments": [],
        "error_message": None,
    }

    try:
        resp = requests.get(article["detail_url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        result["error_message"] = str(e)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    content_div = (
        soup.select_one("#artclViewBody")
        or soup.select_one(".board-view-content")
        or soup.select_one(".view-con")
        or soup.select_one(".fr-view")
        or soup.select_one(".artclView")
    )
    if not content_div:
        result["error_message"] = "본문 영역을 찾을 수 없습니다."
        return result

    # 1. 이미지 추출 및 이미지 전용 게시글 판별
    image_urls = []
    for img in content_div.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src:
            cleaned = clean_url(src)
            if cleaned not in image_urls:
                image_urls.append(cleaned)
    result["image_urls"] = image_urls

    plain_text = content_div.get_text(strip=True)
    if len(plain_text) < 150 and len(image_urls) > 0:
        result["is_image_job"] = True
        result["detail_markdown"] = "### 이미지 기반 게시글\n" + "\n".join(
            f"![게시글이미지]({url})" for url in image_urls
        )
    else:
        h = html2text.HTML2Text()
        h.bypass_tables = False
        h.ignore_links = True
        h.ignore_images = True
        h.body_width = 0
        h.ul_item_mark = "*"
        result["detail_markdown"] = h.handle(str(content_div)).strip()

    # 2. 첨부파일 추출
    attachments = []
    for a_tag in soup.select("a[href*='atchFile'], a[href*='fileDown'], .file-list a"):
        fname = a_tag.get_text(strip=True)
        fhref = a_tag.get("href", "")
        if fname:
            attachments.append({"name": fname, "url": clean_url(fhref)})
    result["attachments"] = attachments

    return result


def fetch_board_articles(
    board_name: str,
    board_code: str,
    max_pages: int | None = None,
    delay: float = 1.0,
    lookback_days: int | None = RECRUIT_LOOKBACK_DAYS,
) -> list[dict]:
    """
    단일 게시판의 목록(메타데이터)만 수집.
    lookback_days가 설정되면 그보다 오래된 게시글이 나오는 페이지에서 수집을 멈춘다
    (게시판이 최신글부터 나열되므로, 한 페이지가 전부 기준일보다 오래되면 그 이후 페이지도 전부 오래된 글이다).
    """
    total_pages = get_total_pages(board_code)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    cutoff_date = date.today() - timedelta(days=lookback_days) if lookback_days else None
    if cutoff_date:
        print(f"  [{board_name}] 총 {total_pages}페이지 수집 시작 (기준일 {cutoff_date} 이후 게시글만)")
    else:
        print(f"  [{board_name}] 총 {total_pages}페이지 수집 시작")

    all_articles = []

    for page in range(1, total_pages + 1):
        result = fetch_article_list(board_name, board_code, page, cutoff_date=cutoff_date)
        articles = result["articles"]
        oldest_date = result["oldest_date"]
        print(f"    페이지 {page}/{total_pages} → {len(articles)}건")
        all_articles.extend(articles)

        if cutoff_date and oldest_date and oldest_date < cutoff_date:
            print(f"    → 기준일({cutoff_date})보다 오래된 게시글 도달, 이후 페이지 수집 중단")
            break

        if page < total_pages:
            time.sleep(delay)

    return all_articles
