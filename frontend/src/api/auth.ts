import { apiClient } from './client';
import type { User } from '../types';

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user: User;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type SignupPayload = LoginPayload & {
  name: string;
};

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/login', payload);
  return response.data;
}

export async function signup(payload: SignupPayload): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/signup', payload);
  return response.data;
}

export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post('/auth/logout', null, {
    params: { refresh_token: refreshToken },
  });
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  await apiClient.patch('/auth/password', payload);
}
