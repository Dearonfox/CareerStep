import {
  Bot,
  BriefcaseBusiness,
  ClipboardList,
  Copy,
  FileText,
  LayoutDashboard,
  Sparkles,
} from 'lucide-react';
import { NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { AdminSidebar } from './components/AdminSidebar';
import { AIAnalysisPanel } from './components/AIAnalysisPanel';
import { Button } from './components/Button';
import { DashboardCard } from './components/DashboardCard';
import { JobCard } from './components/JobCard';
import { ProfileProgressCard } from './components/ProfileProgressCard';
import { SearchFilterBar } from './components/SearchFilterBar';
import { SkillTag } from './components/SkillTag';
import { StatCard } from './components/StatCard';
import { adminStats, dashboardSignals, stats } from './data/mockData';
import { useCareerStore } from './store/useCareerStore';
const navItems = [
  { to: '/', label: '홈' },
  { to: '/dashboard', label: '마이페이지' },
  { to: '/jobs', label: '채용공고' },
  { to: '/recommendations', label: 'AI 추천' },
  { to: '/ai-tools', label: '자소서/면접 AI' },
  { to: '/admin', label: '관리자' },
];

const filterSkills = ['전체', 'React', 'Spring Boot', 'LLM API', 'AWS'];

function Header() {
  return (
    <header className="topbar">
      <NavLink className="brand" to="/">
        <span className="brand-mark">CS</span>
        <span>CareerStep</span>
      </NavLink>
      <nav className="topnav">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'}>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

function HomePage() {
  const navigate = useNavigate();
  const { jobs } = useCareerStore();

  return (
    <main className="page-shell hero-grid">
      <section className="hero-copy">
        <p className="eyebrow">AI Career Intelligence Dashboard</p>
        <h1>AI가 분석하는 나만의 IT 취업 로드맵</h1>
        <p>
          이력, 기술스택, 관심 직무를 바탕으로 적합한 공고와 부족 역량을 한 화면에서
          분석합니다. 이제 공고를 찾는 일이 아니라 준비 상태를 관리하세요.
        </p>
        <div className="hero-actions">
          <Button variant="ai" icon={Sparkles} onClick={() => navigate('/recommendations')}>
            AI 추천 시작하기
          </Button>
          <Button variant="secondary" icon={BriefcaseBusiness} onClick={() => navigate('/jobs')}>
            공고 둘러보기
          </Button>
        </div>
      </section>

      <section className="preview-panel">
        <div className="preview-header">
          <div>
            <p className="eyebrow">Preview</p>
            <h2>오늘의 AI 추천 결과</h2>
          </div>
          <span className="preview-score">92</span>
        </div>
        <div className="preview-stats">
          <div>
            <strong>{jobs.length * 8}</strong>
            <span>추천 공고</span>
          </div>
          <div>
            <strong>3개</strong>
            <span>부족 역량</span>
          </div>
          <div>
            <strong>A-</strong>
            <span>지원 준비도</span>
          </div>
        </div>
        <div className="preview-section">
          <span>추천 기술스택</span>
          <div className="tag-row">
            {['React', 'TypeScript', 'Zustand', 'AWS'].map((skill) => (
              <SkillTag key={skill} label={skill} tone="ai" />
            ))}
          </div>
        </div>
        <div className="insight-card">
          <Bot size={20} />
          <p>프론트엔드 공고 적합도가 높습니다. 테스트 코드와 접근성 경험을 보강하세요.</p>
        </div>
      </section>
    </main>
  );
}

function DashboardPage() {
  return (
    <main className="page-shell">
      <div className="page-title">
        <p className="eyebrow">My Career Board</p>
        <h1>나의 취업 현황판</h1>
      </div>

      <section className="stat-grid">
        {stats.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </section>

      <section className="bento-grid">
        <DashboardCard title="프로필 완성도" className="bento-wide">
          <ProfileProgressCard />
        </DashboardCard>
        <DashboardCard title="부족 역량 TOP 3">
          <div className="stack-list">
            {['테스트 코드', 'AWS 배포', '접근성'].map((skill) => (
              <SkillTag key={skill} label={skill} tone="gap" />
            ))}
          </div>
        </DashboardCard>
        {dashboardSignals.map((signal) => {
          const Icon = signal.icon;
          return (
            <DashboardCard key={signal.label} title={signal.label}>
              <div className="signal-row">
                <Icon size={22} />
                <p>{signal.value}</p>
              </div>
            </DashboardCard>
          );
        })}
        <DashboardCard title="지원 준비 상태" className="bento-wide">
          <div className="readiness">
            {['이력서', '포트폴리오', '자기소개서', '면접 준비'].map((item, index) => (
              <div key={item}>
                <span>{item}</span>
                <strong>{index < 2 ? '완료' : '보강 필요'}</strong>
              </div>
            ))}
          </div>
        </DashboardCard>
      </section>
    </main>
  );
}

function JobsPage({ compact = false }: { compact?: boolean }) {
  const {
    jobs,
    query,
    selectedSkill,
    setQuery,
    setSelectedSkill,
    toggleSaved,
  } = useCareerStore();

  const normalizedQuery = query.trim().toLowerCase();
  const filteredJobs = jobs.filter((job) => {
    const matchesQuery =
      !normalizedQuery ||
      [job.title, job.company, job.location, ...job.skills]
        .join(' ')
        .toLowerCase()
        .includes(normalizedQuery);
    const matchesSkill = selectedSkill === '전체' || job.skills.includes(selectedSkill);
    return matchesQuery && matchesSkill;
  });

  return (
    <section className={compact ? 'jobs-pane' : 'page-shell'}>
      {!compact ? (
        <div className="page-title">
          <p className="eyebrow">Smart Job Cards</p>
          <h1>AI 적합도 기반 채용공고</h1>
        </div>
      ) : null}
      <SearchFilterBar
        query={query}
        selectedSkill={selectedSkill}
        skills={filterSkills}
        onQueryChange={setQuery}
        onSkillChange={setSelectedSkill}
      />
      <div className="job-list">
        {filteredJobs.map((job) => (
          <JobCard key={job.id} job={job} onToggleSaved={toggleSaved} />
        ))}
      </div>
    </section>
  );
}

function RecommendationsPage() {
  return (
    <main className="page-shell">
      <div className="page-title">
        <p className="eyebrow">AI Recommendation</p>
        <h1>추천 공고와 분석 결과</h1>
      </div>
      <div className="recommendation-layout">
        <JobsPage compact />
        <AIAnalysisPanel />
      </div>
    </main>
  );
}

function AiToolsPage() {
  return (
    <main className="page-shell split-tool-layout">
      <section className="tool-form">
        <p className="eyebrow">AI Writing Studio</p>
        <h1>자기소개서 / 면접 AI</h1>
        <label>
          지원 직무
          <input placeholder="예: 주니어 프론트엔드 개발자" />
        </label>
        <label>
          핵심 경험
          <textarea placeholder="프로젝트, 역할, 성과를 입력하세요." rows={7} />
        </label>
        <div className="tool-actions">
          <Button variant="ai" icon={FileText}>자기소개서 생성</Button>
          <Button variant="secondary" icon={ClipboardList}>면접 질문 생성</Button>
        </div>
      </section>

      <section className="ai-result">
        <div className="result-header">
          <div>
            <p className="eyebrow">Generated Result</p>
            <h2>AI 생성 결과</h2>
          </div>
          <Button variant="secondary" icon={Copy}>복사하기</Button>
        </div>
        <article>
          <h3>자기소개서 초안</h3>
          <p>
            저는 사용자가 목표를 빠르게 이해하고 행동할 수 있는 화면을 만드는 데 강점이
            있습니다. 최근 프로젝트에서는 React와 TypeScript로 공고 추천 흐름을 구현하며
            상태 관리와 API 연동 구조를 정리했습니다.
          </p>
          <p>
            입사 후에는 제품의 사용 맥락을 분석하고, 데이터 기반으로 개선 우선순위를
            제안하는 프론트엔드 개발자로 성장하겠습니다.
          </p>
        </article>
        <div className="question-grid">
          {['인성 질문', '기술 질문', '프로젝트 질문', '꼬리 질문'].map((category) => (
            <div key={category}>
              <strong>{category}</strong>
              <p>이 경험에서 본인의 의사결정 기준은 무엇이었나요?</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

function AdminPage() {
  return (
    <main className="admin-layout">
      <AdminSidebar />
      <section className="admin-main">
        <div className="page-title">
          <p className="eyebrow">SaaS Admin</p>
          <h1>운영 대시보드</h1>
        </div>
        <div className="admin-stat-grid">
          {adminStats.map((stat) => (
            <article key={stat.label} className="admin-stat-card">
              <span>{stat.label}</span>
              <strong>{stat.value}</strong>
              <small>{stat.trend}</small>
            </article>
          ))}
        </div>
        <section className="admin-table-card">
          <div className="section-heading">
            <div>
              <h2>최근 AI 분석 로그</h2>
              <p>요청 상태와 이상 징후를 빠르게 확인합니다.</p>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>사용자</th>
                <th>분석 유형</th>
                <th>상태</th>
                <th>요청 시간</th>
              </tr>
            </thead>
            <tbody>
              {['김하준', '이지민', '박서연'].map((name, index) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{index === 0 ? '공고 추천' : '자기소개서'}</td>
                  <td><span className="status-pill">정상</span></td>
                  <td>{index + 2}분 전</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </section>
    </main>
  );
}

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/ai-tools" element={<AiToolsPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </>
  );
}
