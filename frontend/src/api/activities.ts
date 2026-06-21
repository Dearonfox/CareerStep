import { apiClient } from './client';

export type ActivityItem = {
  id: number;
  title: string;
  organizer: string;
  period: string;
  category: string;
  tags: string[];
  status: string;
  url: string;
  description: string;
};

export async function listActivities(): Promise<ActivityItem[]> {
  const response = await apiClient.get<ActivityItem[]>('/activities');
  return response.data;
}
