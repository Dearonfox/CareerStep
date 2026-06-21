import { create } from 'zustand';
import { getMyRecommendations } from '../api/recommendations';
import type { RecommendationResult, RecommendationStatus } from '../types';

type RecommendState = {
  result: RecommendationResult | null;
  status: RecommendationStatus;
  isLoading: boolean;
  message: string;
  error: string | null;
  loadRecommendations: () => Promise<RecommendationStatus>;
  clearRecommendations: () => void;
};

export const useRecommendStore = create<RecommendState>((set) => ({
  result: null,
  status: 'idle',
  isLoading: false,
  message: '',
  error: null,
  loadRecommendations: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await getMyRecommendations();
      set({
        result: response.result,
        status: response.status,
        message: response.message ?? '',
        isLoading: false,
      });
      return response.status;
    } catch {
      set({
        result: null,
        status: 'error',
        message: '',
        error: '추천 결과를 불러오지 못했습니다.',
        isLoading: false,
      });
      return 'error';
    }
  },
  clearRecommendations: () =>
    set({ result: null, status: 'idle', isLoading: false, message: '', error: null }),
}));
