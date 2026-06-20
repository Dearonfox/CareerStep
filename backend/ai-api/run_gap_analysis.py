import json
import sys
import argparse
from pathlib import Path

from app.services.gap_analyzer import analyze_gap, render_markdown

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    
    parser = argparse.ArgumentParser(description="Run Gap Analyzer Demo")
    parser.add_argument("--source", type=str, default="demand_profiles.json",
                        help="Path to demand_profiles.json (default: demand_profiles.json)")
    args = parser.parse_args()
    
    source_path = Path(args.source)
    if not source_path.exists():
        if args.source == "samples":
            print("[에러] samples 즉석 집계는 현재 지원하지 않습니다. demand_profiles.json을 명시하세요.")
        else:
            print(f"[에러] 수요 데이터 파일이 없습니다: {source_path}")
        sys.exit(1)
        
    with open(source_path, "r", encoding="utf-8") as f:
        demand = json.load(f)
        
    # 데모용 프로필 3종
    sample_profiles = [
        {
            "name": "백엔드 지망생 A",
            "desired_role": "서버 개발",
            "skills": ["Java", "스프링부트", "MySQL", "React"],
            "certificates": ["정보처리기사"],
            "projects": ["쇼핑몰 백엔드 API 개발"]
        },
        {
            "name": "데이터 지망생 B",
            "desired_role": "데이터분석가",
            "skills": ["Python", "SQL", "Tableau", "Excel"],
            "certificates": ["ADsP"],
            "projects": ["매출 데이터 시각화"]
        },
        {
            "name": "초보 프론트엔드 C",
            "desired_role": "프론트엔드개발자",
            "skills": ["HTML", "CSS", "JavaScript"],
            "certificates": [],
            "projects": ["토이 프로젝트"]
        }
    ]
    
    reports_md = []
    
    for prof in sample_profiles:
        print(f"\n{'='*50}\n[{prof['name']}] 프로필 분석 중...")
        report = analyze_gap(prof, demand)
        md_text = render_markdown(report)
        
        print("\n" + md_text)
        
        reports_md.append(f"<!-- Profile: {prof['name']} -->\n" + md_text)
        
    output_path = Path("gap_report.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n---\n\n".join(reports_md))
        
    print(f"\n{'='*50}\n[완료] 결과를 {output_path} 파일에 저장했습니다.")

if __name__ == "__main__":
    main()
