import { create } from 'zustand';
import type { User } from '../types';

const AUTH_STORAGE_KEY = 'careerstep-auth';

type UserState = {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
};

function loadStoredAuth(): Pick<UserState, 'user' | 'accessToken' | 'refreshToken' | 'isAuthenticated'> {
  const fallback = {
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
  };

  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return fallback;
    }
    const parsed = JSON.parse(raw) as {
      user: User;
      accessToken: string;
      refreshToken: string;
    };
    return {
      user: parsed.user,
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
      isAuthenticated: Boolean(parsed.accessToken),
    };
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return fallback;
  }
}

const storedAuth = loadStoredAuth();

export const useUserStore = create<UserState>((set) => ({
  ...storedAuth,
  setAuth: (user, accessToken, refreshToken) => {
    window.localStorage.setItem(
      AUTH_STORAGE_KEY,
      JSON.stringify({ user, accessToken, refreshToken }),
    );
    set({ user, accessToken, refreshToken, isAuthenticated: true });
  },
  clearAuth: () => {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
  },
}));
