import type { Job } from '../types';
import { apiClient } from './client';

type JobResponse = {
  id: number;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  skills: string[];
  description: string;
};

function toJob(response: JobResponse): Job {
  return {
    id: response.id,
    title: response.title,
    company: response.company,
    location: response.location,
    employmentType: response.employment_type,
    skills: response.skills,
    matchScore: 0,
    reason: response.description || 'MongoDB에 수집된 실제 채용공고입니다. 프로필 기반 추천 점수는 추천 로직 연동 후 표시됩니다.',
    gaps: [],
    saved: false,
  };
}

export async function listJobs(): Promise<Job[]> {
  const response = await apiClient.get<JobResponse[]>('/jobs');
  return response.data.map(toJob);
}
