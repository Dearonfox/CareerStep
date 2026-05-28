import { create } from 'zustand';
import { jobs as initialJobs } from '../data/mockData';
import type { Job, PageKey } from '../types';

type CareerState = {
  currentPage: PageKey;
  jobs: Job[];
  query: string;
  selectedSkill: string;
  setPage: (page: PageKey) => void;
  setQuery: (query: string) => void;
  setSelectedSkill: (skill: string) => void;
  toggleSaved: (jobId: number) => void;
};

export const useCareerStore = create<CareerState>((set) => ({
  currentPage: 'home',
  jobs: initialJobs,
  query: '',
  selectedSkill: '전체',
  setPage: (page) => set({ currentPage: page }),
  setQuery: (query) => set({ query }),
  setSelectedSkill: (skill) => set({ selectedSkill: skill }),
  toggleSaved: (jobId) =>
    set((state) => ({
      jobs: state.jobs.map((job) =>
        job.id === jobId ? { ...job, saved: !job.saved } : job,
      ),
    })),
}));
