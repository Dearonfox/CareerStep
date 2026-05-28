import { create } from 'zustand';
import { jobs as initialJobs } from '../data/mockData';
import type { Job } from '../types';

type JobState = {
  jobs: Job[];
  savedJobIds: number[];
  setJobs: (jobs: Job[]) => void;
  toggleSavedJob: (jobId: number) => void;
};

export const useJobStore = create<JobState>((set) => ({
  jobs: initialJobs,
  savedJobIds: initialJobs.filter((job) => job.saved).map((job) => job.id),
  setJobs: (jobs) => set({ jobs }),
  toggleSavedJob: (jobId) =>
    set((state) => ({
      savedJobIds: state.savedJobIds.includes(jobId)
        ? state.savedJobIds.filter((id) => id !== jobId)
        : [...state.savedJobIds, jobId],
      jobs: state.jobs.map((job) =>
        job.id === jobId ? { ...job, saved: !job.saved } : job,
      ),
    })),
}));
