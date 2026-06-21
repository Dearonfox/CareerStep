import type { Job } from '../types';
import { apiClient } from './client';

type MatchBadgeResponse = {
  score: number;
  matched_skills: string[];
};

type JobResponse = {
  id: number;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  skills: string[];
  description: string;
  match_badge: MatchBadgeResponse | null;
};

function toJob(response: JobResponse): Job {
  const matchBadge = response.match_badge;

  return {
    id: response.id,
    title: response.title,
    company: response.company,
    location: response.location,
    employmentType: response.employment_type,
    skills: response.skills,
    matchScore: matchBadge?.score ?? 0,
    matchedSkills: matchBadge?.matched_skills ?? [],
    reason: response.description || 'MongoDB에 수집된 실제 채용공고입니다.',
    gaps: [],
    saved: false,
  };
}

export async function listJobs(): Promise<Job[]> {
  const response = await apiClient.get<JobResponse[]>('/jobs', { params: { sort: 'match' } });
  return response.data.map(toJob);
}
