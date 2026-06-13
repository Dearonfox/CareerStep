import requests
from bs4 import BeautifulSoup
import time
import urllib.parse
from datetime import datetime

BASE_URL = "https://www.jobkorea.co.kr/Recruit/Home/_GI_List/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.jobkorea.co.kr",
    "Referer": "https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1"
}

def clean_url(url_path: str) -> str:
    if not url_path:
        return ""
    if url_path.startswith("http"):
        return url_path
    return urllib.parse.urljoin("https://www.jobkorea.co.kr", url_path)

def parse_job_row(row, category_name: str) -> dict:
    """잡코리아 공고 tr 요소를 받아 가공된 딕셔너리로 반환"""
    job_id = row.get("data-gno") or row.get("data-no", "")
    if not job_id:
        return None

    # 회사 정보 파싱
    company_tag = row.select_one("td.tplCo a")
    company_name = company_tag.get_text(strip=True) if company_tag else "회사명 없음"
    company_url = clean_url(company_tag.get("href")) if company_tag else ""

    # 제목 및 상세 정보 파싱
    title_tag = row.select_one("td.tplTit strong a")
    title = title_tag.get_text(strip=True) if title_tag else "제목 없음"
    detail_url = clean_url(title_tag.get("href")) if title_tag else ""

    # p.etc 메타데이터 파싱 (경력, 학력, 지역, 고용형태)
    meta_info = {
        "experience_level": "N/A",
        "education": "N/A",
        "location": "N/A",
        "employment_type": "N/A"
    }
    
    etc_spans = row.select("td.tplTit p.etc span.cell")
    if etc_spans:
        # 안전한 순서별 매핑
        texts = [span.get_text(strip=True) for span in etc_spans]
        if len(texts) >= 1:
            meta_info["experience_level"] = texts[0]
        if len(texts) >= 2:
            meta_info["education"] = texts[1]
        if len(texts) >= 3:
            meta_info["location"] = texts[2]
        if len(texts) >= 4:
            meta_info["employment_type"] = texts[3]

    # p.dsc 직무/기술 태그 키워드 파싱
    dsc_tag = row.select_one("td.tplTit p.dsc")
    tags = []
    if dsc_tag:
        raw_tags = dsc_tag.get_text(strip=True).split(",")
        tags = [t.strip() for t in raw_tags if t.strip()]

    # 마감일 및 등록일 (td.odd)
    post_date_raw = "N/A"
    deadline_raw = "N/A"
    
    time_tag = row.select_one("td.odd span.time")
    if time_tag:
        post_date_raw = time_tag.get_text(strip=True)
        
    date_tag = row.select_one("td.odd span.date")
    if date_tag:
        deadline_raw = date_tag.get_text(strip=True)

    return {
        "category": category_name,
        "job_id": job_id,
        "company_name": company_name,
        "company_url": company_url,
        "title": title,
        "detail_url": detail_url,
        "meta": meta_info,
        "tags": tags,
        "post_date_raw": post_date_raw,
        "deadline_raw": deadline_raw,
        "scraped_at": datetime.now().isoformat()
    }

def fetch_category_jobs(category_name: str, duty_code: str, target_count: int = 10) -> list[dict]:
    """특정 직무 카테고리의 상위 target_count개 공고를 가져옴"""
    payload = {
        "isDefault": "true",
        "condition[duty]": duty_code,
        "page": 1,
        "pagesize": 20,  # 넉넉하게 20개 가져와서 파싱 오류 등을 거르고 10개 슬라이싱
        "order": "20",
        "direct": "0",
        "tabindex": "0",
        "onePick": "0",
        "confirm": "0",
        "profile": "0"
    }

    try:
        response = requests.post(BASE_URL, data=payload, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [오류] HTTP {response.status_code} 발생")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("tr.devloopArea") or soup.select("tr[data-gno]")
        
        jobs = []
        for row in rows:
            parsed = parse_job_row(row, category_name)
            if parsed:
                jobs.append(parsed)
            if len(jobs) >= target_count:
                break
                
        return jobs

    except Exception as e:
        print(f"  [예외 발생] {e}")
        return []
