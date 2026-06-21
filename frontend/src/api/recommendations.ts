import type { Job, RecommendationResult, RecommendationStatus, RoadmapItem } from '../types';
import { apiClient } from './client';

type RecommendedJobResponse = {
  job_id: string;
  position_title: string;
  match_score: number;
  reason: string;
  matched_skills: string[];
  missing_skills: string[];
};

type RoadmapResponse = {
  order: number;
  title: string;
  why: string;
  how: string;
  duration: string;
  outcome: string;
};

type RecommendationsDoneData = {
  recommendations: RecommendedJobResponse[];
  strengths: string[];
  gaps: string[];
  roadmap: RoadmapResponse[];
  policy_violation: boolean;
};

type RecommendationsResponse =
  | { status: Exclude<RecommendationStatus, 'idle' | 'done'>; message: string }
  | { status: 'done'; updated_at?: string; data: RecommendationsDoneData };

export type RecommendationViewResponse = {
  status: RecommendationStatus;
  message?: string;
  result: RecommendationResult | null;
};

function toStableNumberId(jobId: string, index: number): number {
  const parsed = Number.parseInt(jobId, 10);
  return Number.isFinite(parsed) ? parsed : index + 1;
}

function toJob(item: RecommendedJobResponse, index: number): Job {
  return {
    id: toStableNumberId(item.job_id, index),
    title: item.position_title,
    company: 'AI 추천 공고',
    location: '',
    employmentType: '맞춤 추천',
    skills: item.matched_skills,
    matchScore: item.match_score,
    matchedSkills: item.matched_skills,
    reason: item.reason,
    gaps: item.missing_skills,
    saved: false,
  };
}

function toRoadmapItem(item: RoadmapResponse, index: number): RoadmapItem {
  return {
    step: String(item.order).padStart(2, '0'),
    title: item.title,
    description: `${item.why} ${item.how} (${item.duration}) 결과: ${item.outcome}`,
    status: index === 0 ? 'active' : 'next',
  };
}

export async function getMyRecommendations(): Promise<RecommendationViewResponse> {
  const response = await apiClient.get<RecommendationsResponse>('/ai/recommendations/me');
  const body = response.data;

  if (body.status !== 'done') {
    return {
      status: body.status,
      message: body.message,
      result: null,
    };
  }

  const recommendations = [...body.data.recommendations].sort(
    (left, right) => right.match_score - left.match_score,
  );
  const roadmap = [...body.data.roadmap].sort((left, right) => left.order - right.order);

  return {
    status: 'done',
    result: {
      jobs: recommendations.map(toJob),
      strengths: body.data.strengths,
      gaps: body.data.gaps,
      roadmap: roadmap.map(toRoadmapItem),
      policyViolation: body.data.policy_violation,
      updatedAt: body.updated_at,
    },
  };
}
