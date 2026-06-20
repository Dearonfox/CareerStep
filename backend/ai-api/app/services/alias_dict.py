import re

# 가장 흔하게 등장하는 표면형 불일치를 정규화하는 사전
# 모든 키워드는 소문자, 공백 제거 상태로 매칭될 수 있도록 구성합니다.
ALIAS_DICT = {
    "파이썬": "python",
    "python3": "python",
    "py": "python",
    
    "리액트": "react",
    "react.js": "react",
    "reactjs": "react",
    
    "뷰": "vue",
    "vue.js": "vue",
    "vuejs": "vue",
    
    "노드": "nodejs",
    "node": "nodejs",
    "node.js": "nodejs",
    
    "스프링": "spring",
    "스프링부트": "springboot",
    "spring boot": "springboot",
    
    "자바": "java",
    "타입스크립트": "typescript",
    "ts": "typescript",
    
    "자바스크립트": "javascript",
    "js": "javascript",
    
    "시플플": "c++",
    "cpp": "c++",
    
    "씨샵": "c#",
    "csharp": "c#",
    
    "elk 스택": "elk",
    "엘라스틱서치": "elasticsearch",
    
    "엔진엑스": "nginx",
    "도커": "docker",
    "쿠버네티스": "kubernetes",
    "k8s": "kubernetes",
    
    "장고": "django",
    "플라스크": "flask",
    
    "아마존웹서비스": "aws",
    "구글클라우드": "gcp",
    "애저": "azure",
    
    "에스큐엘": "sql",
    "마이에스큐엘": "mysql",
    "포스트그레": "postgresql",
    "postgres": "postgresql",
    
    "안드로이드": "android",
    "아이오에스": "ios",
    "플러터": "flutter",
    "스위프트": "swift",
    "코틀린": "kotlin",
    
    "머신러닝": "ml",
    "딥러닝": "dl",
    "인공지능": "ai",
    
    "텐서플로우": "tensorflow",
    "파이토치": "pytorch",
}

def normalize_text(text: str) -> str:
    """
    텍스트에서 공백을 제거하고 소문자로 변환한 뒤,
    ALIAS_DICT를 참조하여 표준형으로 변환합니다.
    주의: 이 함수는 단일 단어나 스택 항목에 적용하는 것을 권장합니다.
    """
    if not text:
        return ""
        
    # 공백 제거 및 소문자 변환
    normalized = text.lower().strip()
    # 띄어쓰기를 없앤 버전으로도 매칭 시도
    compressed = normalized.replace(" ", "")
    
    # 1순위: 띄어쓰기 유지 버전에 매칭 (예: "spring boot")
    if normalized in ALIAS_DICT:
        return ALIAS_DICT[normalized]
        
    # 2순위: 띄어쓰기 제거 버전에 매칭 (예: "springboot")
    if compressed in ALIAS_DICT:
        return ALIAS_DICT[compressed]
        
    # 매칭 실패 시 원래의 소문자 문자열 반환
    return normalized
