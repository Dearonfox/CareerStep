import re
from typing import List, Dict, Any
from app.services.alias_dict import normalize_text

# 잡코리아 26개 표준 직군 및 관련 키워드
ROLE_KEYWORDS = {
    "백엔드개발자": {"java", "spring", "springboot", "nodejs", "python", "django", "flask", "c#", "php", "ruby", "api", "server", "backend", "백엔드", "서버", "rest"},
    "프론트엔드개발자": {"react", "vue", "javascript", "typescript", "html", "css", "frontend", "프론트엔드", "프론트", "spa", "ui", "ux"},
    "웹개발자": {"web", "웹", "웹개발", "jsp", "asp"},
    "앱개발자": {"android", "ios", "flutter", "reactnative", "swift", "kotlin", "objective-c", "app", "mobile", "모바일", "앱"},
    "시스템엔지니어": {"linux", "unix", "windows", "system", "시스템", "os", "서버운영"},
    "네트워크엔지니어": {"network", "네트워크", "cisco", "tcp", "ip", "dns", "vpn", "router", "switch", "라우터", "스위치"},
    "DBA": {"dba", "database", "데이터베이스", "oracle", "mysql", "postgresql", "sql", "nosql", "mongodb", "redis"},
    "데이터엔지니어": {"data", "pipeline", "etl", "spark", "hadoop", "kafka", "데이터", "파이프라인", "airflow"},
    "데이터사이언티스트": {"r", "python", "numpy", "pandas", "scipy", "머신러닝", "ml", "ai", "데이터사이언스", "통계", "분석모델"},
    "데이터분석가": {"sql", "excel", "tableau", "powerbi", "분석", "analyst", "데이터분석", "시각화"},
    "보안엔지니어": {"security", "보안", "해킹", "취약점", "방화벽", "관제", "백신", "모의해킹"},
    "소프트웨어개발자": {"sw", "소프트웨어", "c", "c++", "알고리즘", "자료구조", "응용소프트웨어"},
    "게임개발자": {"game", "게임", "unity", "unreal", "유니티", "언리얼", "directx", "opengl"},
    "하드웨어개발자": {"hw", "하드웨어", "회로", "설계", "pcb", "verilog", "vhdl", "fpga", "임베디드", "펌웨어"},
    "AI/ML엔지니어": {"ai", "ml", "인공지능", "머신러닝", "딥러닝", "tensorflow", "pytorch", "keras", "vision", "nlp", "cv"},
    "AI/ML연구원": {"research", "연구", "논문", "알고리즘", "ai", "ml", "인공지능"},
    "블록체인개발자": {"blockchain", "블록체인", "smartcontract", "solidity", "ethereum", "web3", "nft", "crypto", "코인"},
    "클라우드엔지니어": {"cloud", "클라우드", "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "devops", "terraform", "ci", "cd"},
    "웹퍼블리셔": {"퍼블리셔", "publisher", "html", "css", "마크업", "웹표준", "웹접근성"},
    "IT컨설팅": {"consulting", "컨설팅", "erp", "sap", "crm", "전략", "isp"},
    "QA": {"qa", "테스트", "test", "quality", "assurance", "자동화", "selenium", "appium", "제어", "버그"},
    "데이터라벨러": {"라벨링", "라벨러", "labeling", "annotation", "태깅"},
    "프롬프트엔지니어": {"prompt", "프롬프트", "chatgpt", "llm", "생성형", "generative"},
    "AI보안전문가": {"ai", "security", "보안", "인공지능", "위협"},
    "MLOps엔지니어": {"mlops", "devops", "pipeline", "모델", "배포", "서빙"},
    "AI서비스개발자": {"ai", "service", "api", "통합", "개발", "서비스"}
}

def extract_tokens(text: str) -> List[str]:
    """텍스트를 단어 단위로 분할하여 정규화된 토큰 리스트 반환"""
    if not text:
        return []
    # 특수문자 제거 후 공백 분할
    cleaned = re.sub(r'[^a-zA-Z0-9가-힣\s\+\#\.]', ' ', text)
    tokens = cleaned.split()
    return [normalize_text(t) for t in tokens if t.strip()]

def score_position(position: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    단일 포지션에 대해 26개 직군의 점수를 계산하여 상위 결과를 반환합니다.
    """
    scores = {role: 0.0 for role in ROLE_KEYWORDS.keys()}
    
    # 텍스트 추출
    title = position.get("position_title", "")
    tech_stack = position.get("tech_stack", [])
    main_tasks = position.get("main_tasks", [])
    
    title_tokens = extract_tokens(title)
    
    # tech_stack은 배열이므로 문자열로 합친 뒤 파싱
    tech_text = " ".join(tech_stack) if isinstance(tech_stack, list) else str(tech_stack)
    tech_tokens = extract_tokens(tech_text)
    
    # main_tasks도 배열
    task_text = " ".join(main_tasks) if isinstance(main_tasks, list) else str(main_tasks)
    task_tokens = extract_tokens(task_text)
    
    # 점수 계산
    for role, keywords in ROLE_KEYWORDS.items():
        role_score = 0.0
        
        # 1. Title 매칭 (가중치 3.0)
        for token in title_tokens:
            if token in keywords:
                role_score += 3.0
                
        # 2. Tech Stack 매칭 (가중치 2.0)
        for token in tech_tokens:
            if token in keywords:
                role_score += 2.0
                
        # 3. Main Tasks 매칭 (가중치 1.0)
        for token in task_tokens:
            if token in keywords:
                role_score += 1.0
                
        scores[role] = role_score

    # 0점 초과 직군 필터링 (Raw Score)
    raw_scores = {role: score for role, score in scores.items() if score > 0}
    
    # 절대 컷: 총합이 2.0 미만이면 (예: 본문 우연히 1번 매칭) 정보 부족/오분류 방지
    if sum(raw_scores.values()) < 2.0:
        return [{"role": "기타/비개발", "score": 1.0, "rank": 1}]
        
    total_score = sum(raw_scores.values())
    
    # 상대컷(Share) 정규화: 총합을 분모로 나누어 점유율 계산 (합=1.0)
    normalized_scores = {r: round(s / total_score, 3) for r, s in raw_scores.items()}

    # 정렬
    ranked = [{"role": role, "score": score} for role, score in normalized_scores.items()]
    ranked.sort(key=lambda x: x["score"], reverse=True)
    
    # Threshold: 점유율 10% (0.1) 이상만 유효 (상대컷)
    threshold = 0.1
    valid_roles = [r for r in ranked if r["score"] >= threshold]
    
    # Top-K: 최대 3개
    top_k = 3
    result_roles = valid_roles[:top_k]
    
    # 순위 부여
    for idx, r in enumerate(result_roles):
        r["rank"] = idx + 1
        
    if not result_roles:
        return [{"role": "기타/비개발", "score": 1.0, "rank": 1}]
        
    return result_roles

def process_routing_for_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    MongoDB job_raw 문서 내의 summary.relevant_positions에 routed_roles를 추가합니다.
    (멱등성 보장: 여러 번 실행해도 동일한 결과)
    """
    summary = job.get("summary", {})
    if not summary:
        return job
        
    relevant_positions = summary.get("relevant_positions", [])
    
    for pos in relevant_positions:
        pos["routed_roles"] = score_position(pos)
        
    return job
