import { apiClient } from './client';

export type ProfileResponse = {
  id: number;
  user_id: number;
  desired_role: string;
  skills: string[];
  certificates: string[];
  projects: string[];
};

export type ProfilePayload = {
  desired_role: string;
  skills: string[];
  certificates: string[];
  projects: string[];
};

export async function getMyProfile(): Promise<ProfileResponse | null> {
  const response = await apiClient.get<ProfileResponse | null>('/profiles/me');
  return response.data;
}

export async function saveMyProfile(payload: ProfilePayload): Promise<ProfileResponse> {
  const response = await apiClient.put<ProfileResponse>('/profiles/me', payload);
  return response.data;
}
