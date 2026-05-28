import { create } from 'zustand';
import { jobs, roadmap } from '../data/mockData';
import type { RecommendationResult } from '../types';

type RecommendState = {
  result: RecommendationResult | null;
  isLoading: boolean;
  error: string | null;
  setResult: (result: RecommendationResult) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
};

export const useRecommendStore = create<RecommendState>((set) => ({
  result: {
    jobs,
    strengths: ['React UI 구현', 'TypeScript 기반 컴포넌트 설계', 'REST API 연동'],
    gaps: ['테스트 코드', 'AWS 배포', '접근성'],
    roadmap,
  },
  isLoading: false,
  error: null,
  setResult: (result) => set({ result }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
