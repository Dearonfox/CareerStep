import pytest
from app.services.router import score_position
from app.services.alias_dict import normalize_text

def test_normalize_text():
    assert normalize_text(" React.js ") == "react"
    assert normalize_text("스프링부트") == "springboot"
    assert normalize_text("Node.js") == "nodejs"
    assert normalize_text(" elk 스택 ") == "elk"

def test_score_position_backend():
    position = {
        "position_title": "자바 백엔드 개발자 (경력)",
        "tech_stack": ["Java", "Spring Boot", "MySQL", "AWS"],
        "main_tasks": ["REST API 개발", "서버 성능 최적화"]
    }
    
    roles = score_position(position)
    assert len(roles) > 0
    assert roles[0]["role"] == "백엔드개발자"
    assert roles[0]["rank"] == 1
    
    # 2순위로 클라우드엔지니어나 웹개발자가 잡힐 수도 있음
    role_names = [r["role"] for r in roles]
    assert "백엔드개발자" in role_names

def test_score_position_frontend():
    position = {
        "position_title": "프론트엔드 (React)",
        "tech_stack": ["React.js", "TypeScript", "Redux"],
        "main_tasks": ["UI 컴포넌트 개발", "SPA 구현"]
    }
    
    roles = score_position(position)
    assert roles[0]["role"] == "프론트엔드개발자"

def test_score_position_fallback_other():
    position = {
        "position_title": "인사 기획 및 채용 담당자",
        "tech_stack": [],
        "main_tasks": ["채용 공고 작성", "면접 일정 조율", "조직 문화 개선"]
    }
    
    roles = score_position(position)
    assert roles[0]["role"] == "기타/비개발"

def test_score_position_multilabel_fullstack():
    position = {
        "position_title": "풀스택 웹개발자",
        "tech_stack": ["Node.js", "React", "MongoDB", "Express"],
        "main_tasks": ["백엔드 API 개발", "프론트엔드 UI 연동"]
    }
    
    roles = score_position(position)
    role_names = [r["role"] for r in roles]
    # 백엔드, 프론트엔드가 모두 상위에 있어야 함
    assert "백엔드개발자" in role_names
    assert "프론트엔드개발자" in role_names
    assert len(roles) <= 3
