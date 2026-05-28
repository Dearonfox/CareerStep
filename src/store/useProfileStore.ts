import { create } from 'zustand';
import type { CareerProfile } from '../types';

type ProfileState = {
  profile: CareerProfile;
  updateProfile: (profile: Partial<CareerProfile>) => void;
};

export const useProfileStore = create<ProfileState>((set) => ({
  profile: {
    desiredRole: '프론트엔드 개발자',
    skills: ['React', 'TypeScript', 'Zustand'],
    certificates: ['정보처리기사'],
    projects: ['AI 채용 추천 대시보드'],
  },
  updateProfile: (profile) =>
    set((state) => ({
      profile: { ...state.profile, ...profile },
    })),
}));
