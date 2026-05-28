import {
  Activity,
  BarChart3,
  Bookmark,
  CheckCircle2,
  FileCheck2,
  Target,
} from 'lucide-react';
import type { Job, RoadmapItem, Stat } from '../types';

export const jobs: Job[] = [
  {
    id: 1,
    title: '주니어 프론트엔드 개발자',
    company: 'Nexora Labs',
    location: '서울 강남구',
    employmentType: '정규직',
    skills: ['React', 'TypeScript', 'Zustand', 'REST API'],
    matchScore: 92,
    reason: 'React 프로젝트 경험과 컴포넌트 설계 이력이 요구사항과 높게 맞습니다.',
    gaps: ['테스트 코드', '접근성'],
    saved: true,
  },
  {
    id: 2,
    title: '웹 서비스 백엔드 인턴',
    company: 'Cloud Bridge',
    location: '경기 성남시',
    employmentType: '인턴',
    skills: ['Java', 'Spring Boot', 'MySQL', 'AWS'],
    matchScore: 78,
    reason: 'API 설계 경험은 좋지만 배포 자동화 경험을 보강하면 경쟁력이 높아집니다.',
    gaps: ['AWS', 'CI/CD'],
    saved: false,
  },
  {
    id: 3,
    title: 'AI 서비스 풀스택 엔지니어',
    company: 'Prompt Works',
    location: '서울 마포구',
    employmentType: '계약직',
    skills: ['Next.js', 'Node.js', 'LLM API', 'PostgreSQL'],
    matchScore: 84,
    reason: 'AI 기능 구현 관심사와 웹 앱 경험이 잘 맞고, DB 모델링 보완이 필요합니다.',
    gaps: ['PostgreSQL', '서비스 모니터링'],
    saved: false,
  },
];

export const stats: Stat[] = [
  { label: '프로필 완성도', value: '86%', tone: 'blue', icon: CheckCircle2 },
  { label: '추천 공고', value: '24개', tone: 'purple', icon: Target },
  { label: '관심 공고', value: '7개', tone: 'green', icon: Bookmark },
  { label: '지원 준비도', value: 'B+', tone: 'orange', icon: FileCheck2 },
];

export const roadmap: RoadmapItem[] = [
  {
    step: '01',
    title: 'React 상태관리 정리',
    description: 'Zustand 기반 전역 상태와 서버 상태 분리 기준을 포트폴리오 README에 정리하세요.',
    status: 'done',
  },
  {
    step: '02',
    title: '테스트 코드 3개 추가',
    description: '공고 필터, 지원 상태 변경, AI 결과 복사 기능을 중심으로 테스트를 작성하세요.',
    status: 'active',
  },
  {
    step: '03',
    title: '배포 경험 보강',
    description: 'Vercel 또는 AWS Amplify 배포 과정과 장애 대응 기록을 짧은 회고로 남기세요.',
    status: 'next',
  },
];

export const adminStats = [
  { label: '오늘 가입자', value: '128', trend: '+12.4%' },
  { label: '등록 공고', value: '1,482', trend: '+5.8%' },
  { label: 'AI 분석 요청', value: '3,904', trend: '+18.1%' },
  { label: '신고 처리 대기', value: '16', trend: '-3건' },
];

export const dashboardSignals = [
  { label: '최근 AI 분석 결과', value: '프론트엔드 적합도가 상승 중입니다.', icon: BarChart3 },
  { label: '추천 대외활동', value: '오픈소스 컨트리뷰션 챌린지 2건', icon: Activity },
];
