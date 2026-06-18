import { apiClient } from './client';
import type { User, UserRole } from '../types';

export type AdminUser = User & {
  created_at: string;
};

export async function listAdminUsers(): Promise<AdminUser[]> {
  const response = await apiClient.get<AdminUser[]>('/admin/users');
  return response.data;
}

export async function bootstrapFirstAdmin(): Promise<AdminUser> {
  const response = await apiClient.post<AdminUser>('/admin/bootstrap');
  return response.data;
}

export async function updateAdminUserRole(userId: number, role: UserRole): Promise<AdminUser> {
  const response = await apiClient.patch<AdminUser>(`/admin/users/${userId}/role`, { role });
  return response.data;
}

export async function deleteAdminUser(userId: number): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}`);
}
