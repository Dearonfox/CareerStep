"""
시장 수요 집계 실행 스크립트.

사용법 (backend/ai-api 디렉터리에서 실행):
    python run_demand_agg.py                 # MongoDB job_raw 전체 집계 (기본)
    python run_demand_agg.py --source samples # summarized_samples/ 로 오프라인 집계
    python run_demand_agg.py --rank1          # 1순위 직군에만 집계 반영

결과:
    demand_profiles.json  (매칭 엔진이 소비할 구조화 데이터)
    demand_profiles.md    (사람이 보는 리포트)
"""

import argparse
import asyncio
import glob
import json
import os
import sys

from app.services.demand_aggregator import aggregate_demand, render_markdown


def load_samples(sample_dir: str) -> list[dict]:
    jobs = []
    for path in sorted(glob.glob(os.path.join(sample_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            jobs.append(json.load(f))
    return jobs


async def load_from_mongo() -> list[dict]:
    from app.core.config import settings
    from app.core.mongo import mongo

    await mongo.connect(settings.mongodb_uri)
    cursor = mongo.job_raw.find({"summary": {"$exists": True}})
    jobs = await cursor.to_list(length=None)
    await mongo.close()
    return jobs


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["mongo", "samples"], default="mongo")
    parser.add_argument("--sample-dir", default="summarized_samples")
    parser.add_argument("--rank1", action="store_true", help="1순위 직군에만 집계")
    args = parser.parse_args()

    if args.source == "samples":
        print(f"Loading samples from {args.sample_dir}/ ...")
        jobs = load_samples(args.sample_dir)
    else:
        print("Connecting to MongoDB and loading summarized jobs ...")
        jobs = asyncio.run(load_from_mongo())

    print(f"Loaded {len(jobs)} jobs. Aggregating market demand ...")
    demand = aggregate_demand(jobs, rank1_only=args.rank1)

    with open("demand_profiles.json", "w", encoding="utf-8") as f:
        json.dump(demand, f, ensure_ascii=False, indent=2)
    with open("demand_profiles.md", "w", encoding="utf-8") as f:
        f.write(render_markdown(demand))

    meta = demand["meta"]
    print(
        f"Done. {len(demand['roles'])} roles, "
        f"{meta['position_count']} positions aggregated."
    )
    print("→ demand_profiles.json / demand_profiles.md")


if __name__ == "__main__":
    main()
