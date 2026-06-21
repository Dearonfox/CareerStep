import type { LucideIcon } from 'lucide-react';

export type PageKey = 'home' | 'dashboard' | 'jobs' | 'activities' | 'admin';

export type UserRole = 'USER' | 'ADMIN';

export type User = {
  id: number;
  email: string;
  name: string;
  role: UserRole;
};

export type CareerProfile = {
  desiredRole: string;
  skills: string[];
  certificates: string[];
  projects: string[];
};

export type RecommendationResult = {
  jobs: Job[];
  strengths: string[];
  gaps: string[];
  roadmap: RoadmapItem[];
  policyViolation: boolean;
  updatedAt?: string;
};

export type RecommendationStatus = 'idle' | 'no_data' | 'pending' | 'error' | 'done';

export type Job = {
  id: number;
  title: string;
  company: string;
  location: string;
  employmentType: string;
  skills: string[];
  matchScore: number;
  matchedSkills: string[];
  reason: string;
  gaps: string[];
  saved: boolean;
};

export type RoadmapItem = {
  step: string;
  title: string;
  description: string;
  status: 'done' | 'active' | 'next';
};

export type Stat = {
  label: string;
  value: string;
  tone: 'blue' | 'purple' | 'green' | 'orange';
  icon: LucideIcon;
};
