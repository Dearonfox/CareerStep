import { create } from 'zustand';
import { listJobs } from '../api/jobs';
import { jobs as initialJobs } from '../data/mockData';
import type { Job, PageKey } from '../types';

type CareerState = {
  currentPage: PageKey;
  jobs: Job[];
  isLoadingJobs: boolean;
  jobsError: string;
  query: string;
  selectedSkill: string;
  setPage: (page: PageKey) => void;
  loadJobs: () => Promise<void>;
  setQuery: (query: string) => void;
  setSelectedSkill: (skill: string) => void;
  toggleSaved: (jobId: number) => void;
};

export const useCareerStore = create<CareerState>((set) => ({
  currentPage: 'home',
  jobs: initialJobs,
  isLoadingJobs: false,
  jobsError: '',
  query: '',
  selectedSkill: '전체',
  setPage: (page) => set({ currentPage: page }),
  loadJobs: async () => {
    set({ isLoadingJobs: true, jobsError: '' });
    try {
      const jobs = await listJobs();
      set({ jobs, isLoadingJobs: false });
    } catch {
      set({
        isLoadingJobs: false,
        jobsError: '채용공고를 불러오지 못해 예시 데이터를 표시하고 있습니다.',
      });
    }
  },
  setQuery: (query) => set({ query }),
  setSelectedSkill: (skill) => set({ selectedSkill: skill }),
  toggleSaved: (jobId) =>
    set((state) => ({
      jobs: state.jobs.map((job) =>
        job.id === jobId ? { ...job, saved: !job.saved } : job,
      ),
    })),
}));
