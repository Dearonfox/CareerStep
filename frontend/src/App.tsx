import {
  Activity,
  Bot,
  BriefcaseBusiness,
  CalendarDays,
  ClipboardList,
  Copy,
  ExternalLink,
  FileText,
  LockKeyhole,
  LogIn,
  LogOut,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserPlus,
  UserRound,
} from 'lucide-react';
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import {
  deleteAdminUser,
  listAdminUsers,
  updateAdminUserRole,
  type AdminUser,
} from './api/admin';
import { listActivities, type ActivityItem } from './api/activities';
import { changePassword, logout as requestLogout } from './api/auth';
import { getMyProfile, saveMyProfile } from './api/profile';
import { AdminSidebar, type AdminSection } from './components/AdminSidebar';
import { AIAnalysisPanel } from './components/AIAnalysisPanel';
import { Button } from './components/Button';
import { DashboardCard } from './components/DashboardCard';
import { JobCard } from './components/JobCard';
import { ProfileProgressCard } from './components/ProfileProgressCard';
import { ProtectedRoute } from './components/ProtectedRoute';
import { SearchFilterBar } from './components/SearchFilterBar';
import { SkillTag } from './components/SkillTag';
import { adminStats, dashboardSignals } from './data/mockData';
import { AuthPage } from './pages/AuthPage';
import { useCareerStore } from './store/useCareerStore';
import { useRecommendStore } from './store/useRecommendStore';
import { useUserStore } from './store/useUserStore';
import type { Job, UserRole } from './types';
const navItems: Array<{ to: string; label: string; requiredRole?: UserRole }> = [
  { to: '/', label: '홈' },
  { to: '/dashboard', label: '내 스펙' },
  { to: '/jobs', label: '채용공고' },
  { to: '/activities', label: '대외활동' },
  { to: '/admin', label: '관리자', requiredRole: 'ADMIN' },
];

const filterSkills = ['전체', 'React', 'Spring Boot', 'LLM API', 'AWS'];

const emptyProfileForm = {
  desiredRoles: [] as string[],
  skills: [] as string[],
  certificates: [] as string[],
  languages: [] as string[],
  projects: [] as string[],
};

const roleOptions = [
  '백엔드개발자',
  '프론트엔드개발자',
  '웹개발자',
  '앱개발자',
  '시스템엔지니어',
  '네트워크엔지니어',
  'DBA',
  '데이터엔지니어',
  '데이터사이언티스트',
  '보안엔지니어',
  '소프트웨어개발자',
  '게임개발자',
  '하드웨어개발자',
  'AI/ML엔지니어',
  '블록체인개발자',
  '클라우드엔지니어',
  '웹퍼블리셔',
  'IT컨설팅',
  'QA',
  'AI/ML연구원',
  '데이터분석가',
  '데이터라벨러',
  '프롬프트엔지니어',
  'AI보안전문가',
  'MLOps엔지니어',
  'AI서비스개발자',
];
const skillOptions = ['React', 'TypeScript', 'JavaScript', 'Spring Boot', 'Node.js', 'Python', 'MySQL', 'PostgreSQL', 'AWS', 'Docker', 'Git'];
const projectTypeOptions = ['개인 프로젝트', '팀 프로젝트', '기업·인턴 프로젝트', '공모전·해커톤', '오픈소스 기여'];
const responsibilityOptions = ['프론트엔드 개발', '백엔드 개발', '풀스택 개발', 'AI 모델·데이터 처리', '기획·프로젝트 관리', 'UI/UX 설계'];
const languageTestOptions = ['TOEIC', 'TOEIC Speaking', 'OPIc', 'IELTS', 'JLPT', 'HSK'];

function splitCommaValues(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function stripProfilePrefix(value: string, prefix: string) {
  return value.startsWith(prefix) ? value.slice(prefix.length).trim() : value;
}

function pickPrefixedValues(values: string[], prefix: string) {
  return values.filter((value) => value.startsWith(prefix)).map((value) => stripProfilePrefix(value, prefix));
}

function Header() {
  const navigate = useNavigate();
  const { user, refreshToken, isAuthenticated, clearAuth } = useUserStore();
  const visibleNavItems = navItems.filter((item) => !item.requiredRole || user?.role === item.requiredRole);

  async function handleLogout() {
    if (refreshToken) {
      try {
        await requestLogout(refreshToken);
      } catch {
        // Client logout should still clear local auth state even if the server request fails.
      }
    }
    clearAuth();
    navigate('/');
  }

  return (
    <header className="topbar">
      <NavLink className="brand" to="/">
        <span className="brand-mark">CS</span>
        <span>CareerStep</span>
      </NavLink>
      <nav className="topnav">
        {visibleNavItems.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="auth-actions">
        {isAuthenticated ? (
          <>
            <span className="auth-user">{user?.name}</span>
            <Button variant="secondary" icon={UserRound} onClick={() => navigate('/account')}>
              내 정보
            </Button>
            <Button variant="secondary" icon={LogOut} onClick={handleLogout}>
              로그아웃
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" icon={LogIn} onClick={() => navigate('/login')}>
              로그인
            </Button>
            <Button variant="primary" icon={UserPlus} onClick={() => navigate('/signup')}>
              회원가입
            </Button>
          </>
        )}
      </div>
    </header>
  );
}

function AccountPage() {
  const user = useUserStore((state) => state.user);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage('');
    setError('');

    if (newPassword !== confirmPassword) {
      setError('새 비밀번호가 서로 일치하지 않습니다.');
      return;
    }

    setIsSubmitting(true);
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setMessage('비밀번호가 변경되었습니다.');
    } catch {
      setError('현재 비밀번호를 확인해주세요.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell account-layout">
      <section className="page-title">
        <p className="eyebrow">My Account</p>
        <h1>내 정보</h1>
        <p>계정 정보를 확인하고 로그인 비밀번호를 변경할 수 있습니다.</p>
      </section>

      <section className="account-grid">
        <article className="auth-card account-card">
          <h2>계정 정보</h2>
          <dl className="account-info">
            <div>
              <dt>이름</dt>
              <dd>{user?.name ?? '-'}</dd>
            </div>
            <div>
              <dt>이메일</dt>
              <dd>{user?.email ?? '-'}</dd>
            </div>
            <div>
              <dt>권한</dt>
              <dd>{user?.role === 'ADMIN' ? '관리자' : '일반 사용자'}</dd>
            </div>
          </dl>
        </article>

        <article className="auth-card account-card">
          <h2>비밀번호 변경</h2>
          <form onSubmit={handlePasswordSubmit}>
            <label className="auth-field">
              현재 비밀번호
              <span>
                <LockKeyhole size={18} />
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  minLength={8}
                  required
                  autoComplete="current-password"
                />
              </span>
            </label>

            <label className="auth-field">
              새 비밀번호
              <span>
                <LockKeyhole size={18} />
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  minLength={8}
                  maxLength={72}
                  required
                  autoComplete="new-password"
                  placeholder="8자 이상"
                />
              </span>
            </label>

            <label className="auth-field">
              새 비밀번호 확인
              <span>
                <LockKeyhole size={18} />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  minLength={8}
                  maxLength={72}
                  required
                  autoComplete="new-password"
                />
              </span>
            </label>

            {error ? <p className="auth-error">{error}</p> : null}
            {message ? <p className="profile-success">{message}</p> : null}

            <Button variant="primary" className="auth-submit" disabled={isSubmitting}>
              {isSubmitting ? '변경 중...' : '비밀번호 변경'}
            </Button>
          </form>
        </article>
      </section>
    </main>
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
          <Button variant="ai" icon={Sparkles} onClick={() => navigate('/activities')}>
            대외활동 보러가기
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

function ProfileSpecPage() {
  const [form, setForm] = useState(emptyProfileForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [certificateInput, setCertificateInput] = useState('');
  const [languageDraft, setLanguageDraft] = useState({
    testName: languageTestOptions[0],
    score: '',
  });

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      setIsLoading(true);
      setError('');
      try {
        const profile = await getMyProfile();
        if (!isMounted) {
          return;
        }
        if (profile) {
          const storedCertificates = profile.certificates ?? [];
          const storedProjects = profile.projects ?? [];
          setForm({
            desiredRoles: splitCommaValues(profile.desired_role),
            skills: profile.skills,
            certificates: pickPrefixedValues(storedCertificates, '자격증:'),
            languages: pickPrefixedValues(storedCertificates, '어학:'),
            projects: storedProjects.map((value) =>
              stripProfilePrefix(stripProfilePrefix(value, '프로젝트 형태:'), '담당 경험:'),
            ),
          });
        }
      } catch {
        if (isMounted) {
          setError('프로필 정보를 불러오지 못했습니다.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadProfile();
    return () => {
      isMounted = false;
    };
  }, []);

  function toggleSelection(field: 'desiredRoles' | 'skills' | 'projects', value: string) {
    setForm((current) => {
      const selectedValues = current[field];
      const nextValues = selectedValues.includes(value)
        ? selectedValues.filter((item) => item !== value)
        : [...selectedValues, value];
      return { ...current, [field]: nextValues };
    });
    setMessage('');
  }

  function addCustomValue(field: 'desiredRoles' | 'skills' | 'projects') {
    const label = field === 'desiredRoles' ? '직군' : field === 'skills' ? '기술' : '개발 경험';
    const value = window.prompt(`추가할 ${label}을 입력하세요.`);
    const trimmedValue = value?.trim();
    if (!trimmedValue) {
      return;
    }

    setForm((current) => {
      if (current[field].includes(trimmedValue)) {
        return current;
      }
      return { ...current, [field]: [...current[field], trimmedValue] };
    });
    setMessage('');
  }

  function addCertificate() {
    const trimmedValue = certificateInput.trim();
    if (!trimmedValue) {
      return;
    }

    setForm((current) => {
      if (current.certificates.includes(trimmedValue)) {
        return current;
      }
      return { ...current, certificates: [...current.certificates, trimmedValue] };
    });
    setCertificateInput('');
    setMessage('');
  }

  function removeCertificate(value: string) {
    setForm((current) => ({
      ...current,
      certificates: current.certificates.filter((certificate) => certificate !== value),
    }));
    setMessage('');
  }

  function addLanguage() {
    const normalizedTestName = languageDraft.testName.trim();
    const normalizedScore = languageDraft.score.trim();
    if (!normalizedTestName || !normalizedScore) {
      return;
    }

    const language = `${normalizedTestName} ${normalizedScore}`;
    setForm((current) => {
      if (current.languages.includes(language)) {
        return current;
      }
      return { ...current, languages: [...current.languages, language] };
    });
    setLanguageDraft((current) => ({ ...current, score: '' }));
    setMessage('');
  }

  function removeLanguage(value: string) {
    setForm((current) => ({
      ...current,
      languages: current.languages.filter((language) => language !== value),
    }));
    setMessage('');
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError('');
    setMessage('');

    try {
      const certificatesForSave = [
        ...form.certificates.map((certificate) => `자격증: ${certificate}`),
        ...form.languages.map((language) => `어학: ${language}`),
      ];
      const projectsForSave = form.projects.map((project) => {
        if (projectTypeOptions.includes(project)) {
          return `프로젝트 형태: ${project}`;
        }
        if (responsibilityOptions.includes(project)) {
          return `담당 경험: ${project}`;
        }
        return project;
      });
      const savedProfile = await saveMyProfile({
        desired_role: form.desiredRoles.join(', '),
        skills: form.skills,
        certificates: certificatesForSave,
        projects: projectsForSave,
      });
      const savedCertificates = savedProfile.certificates ?? [];
      const savedProjects = savedProfile.projects ?? [];
      setForm({
        desiredRoles: splitCommaValues(savedProfile.desired_role),
        skills: savedProfile.skills,
        certificates: pickPrefixedValues(savedCertificates, '자격증:'),
        languages: pickPrefixedValues(savedCertificates, '어학:'),
        projects: savedProjects.map((value) =>
          stripProfilePrefix(stripProfilePrefix(value, '프로젝트 형태:'), '담당 경험:'),
        ),
      });
      setMessage('스펙 정보가 저장되었습니다.');
    } catch {
      setError('스펙 정보를 저장하지 못했습니다.');
    } finally {
      setIsSaving(false);
    }
  }

  const desiredRoles = form.desiredRoles;
  const skills = form.skills;
  const certificates = form.certificates;
  const languages = form.languages;
  const projects = form.projects;
  const projectTypes = projects.filter((project) => projectTypeOptions.includes(project));
  const responsibilities = projects.filter((project) => responsibilityOptions.includes(project));
  const customExperiences = projects.filter(
    (project) => !projectTypeOptions.includes(project) && !responsibilityOptions.includes(project),
  );

  return (
    <main className="page-shell">
      <div className="page-title">
        <p className="eyebrow">My Career Profile</p>
        <h1>내 스펙 관리</h1>
        <p>추천에 사용할 기본 스펙을 직접 입력하고 저장하세요.</p>
      </div>

      <section className="profile-editor-layout">
        <form className="profile-form-card" onSubmit={handleSubmit}>
          <div className="section-heading">
            <div>
              <h2>추천용 기본 스펙</h2>
              <p>쉼표 또는 줄바꿈으로 여러 항목을 입력할 수 있습니다.</p>
            </div>
            <Button variant="primary" icon={FileText} disabled={isLoading || isSaving}>
              {isSaving ? '저장 중' : '저장'}
            </Button>
          </div>

          {error ? <p className="auth-error">{error}</p> : null}
          {message ? <p className="profile-success">{message}</p> : null}

          <section className="profile-choice-section">
            <div>
              <h3>원하는 직군</h3>
              <p>관심 있는 직군을 모두 선택하세요.</p>
            </div>
            <div className="choice-grid">
              {roleOptions.map((role) => (
                <button
                  type="button"
                  key={role}
                  className={`choice-chip ${desiredRoles.includes(role) ? 'choice-chip-active' : ''}`}
                  onClick={() => toggleSelection('desiredRoles', role)}
                  disabled={isLoading}
                >
                  {role}
                </button>
              ))}
            </div>
          </section>

          <section className="profile-choice-section">
            <div>
              <h3>기술</h3>
              <p>해당하는 기술을 모두 선택하세요.</p>
            </div>
            <div className="choice-grid">
              {skillOptions.map((skill) => (
                <button
                  type="button"
                  key={skill}
                  className={`choice-chip ${form.skills.includes(skill) ? 'choice-chip-active' : ''}`}
                  onClick={() => toggleSelection('skills', skill)}
                  disabled={isLoading}
                >
                  {skill}
                </button>
              ))}
              <button type="button" className="choice-chip choice-chip-add" onClick={() => addCustomValue('skills')}>
                + 직접 추가
              </button>
            </div>
          </section>

          <section className="profile-choice-section">
            <div>
              <h3>자격증</h3>
              <p>선택지 없이 보유한 자격증명을 직접 입력하세요.</p>
            </div>
            <div className="choice-grid">
              {certificates.map((certificate) => (
                <button
                  type="button"
                  key={certificate}
                  className="choice-chip choice-chip-active"
                  onClick={() => removeCertificate(certificate)}
                  disabled={isLoading}
                >
                  {certificate}
                </button>
              ))}
            </div>
            <div className="inline-add-row">
              <input
                type="text"
                value={certificateInput}
                onChange={(event) => setCertificateInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    addCertificate();
                  }
                }}
                placeholder="자격증명을 입력하세요"
                disabled={isLoading}
              />
              <button type="button" className="choice-chip choice-chip-add" onClick={addCertificate} disabled={isLoading}>
                추가
              </button>
            </div>
          </section>

          <section className="profile-choice-section">
            <div>
              <h3>어학</h3>
              <p>시험 항목을 고르고 점수나 등급을 입력하세요.</p>
            </div>
            <div className="choice-grid">
              {languages.map((language) => (
                <button
                  type="button"
                  key={language}
                  className="choice-chip choice-chip-active"
                  onClick={() => removeLanguage(language)}
                  disabled={isLoading}
                >
                  {language}
                </button>
              ))}
            </div>
            <div className="inline-add-row inline-add-row-wide">
              <select
                value={languageDraft.testName}
                onChange={(event) => setLanguageDraft((current) => ({ ...current, testName: event.target.value }))}
                disabled={isLoading}
              >
                {languageTestOptions.map((testName) => (
                  <option key={testName} value={testName}>
                    {testName}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={languageDraft.score}
                onChange={(event) => setLanguageDraft((current) => ({ ...current, score: event.target.value }))}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    addLanguage();
                  }
                }}
                placeholder="점수/등급 예: 850, IH, N2"
                disabled={isLoading}
              />
              <button type="button" className="choice-chip choice-chip-add" onClick={addLanguage} disabled={isLoading}>
                추가
              </button>
            </div>
          </section>

          <section className="profile-choice-section">
            <div>
              <h3>개발 경험</h3>
              <p>추천 로직에서 활용하기 쉽게 프로젝트 형태와 담당 경험을 나눠 선택하세요.</p>
            </div>
            <div className="profile-subsection">
              <strong>프로젝트 형태</strong>
              <div className="choice-grid">
                {projectTypeOptions.map((project) => (
                  <button
                    type="button"
                    key={project}
                    className={`choice-chip ${projects.includes(project) ? 'choice-chip-active' : ''}`}
                    onClick={() => toggleSelection('projects', project)}
                    disabled={isLoading}
                  >
                    {project}
                  </button>
                ))}
              </div>
            </div>
            <div className="profile-subsection">
              <strong>담당 경험</strong>
              <div className="choice-grid">
                {responsibilityOptions.map((project) => (
                  <button
                    type="button"
                    key={project}
                    className={`choice-chip ${projects.includes(project) ? 'choice-chip-active' : ''}`}
                    onClick={() => toggleSelection('projects', project)}
                    disabled={isLoading}
                  >
                    {project}
                  </button>
                ))}
                <button type="button" className="choice-chip choice-chip-add" onClick={() => addCustomValue('projects')}>
                  + 직접 추가
                </button>
              </div>
            </div>
          </section>
        </form>

        <aside className="profile-preview-card">
          <p className="eyebrow">Preview</p>
          <h2>추천에 사용될 정보</h2>
          <div className="profile-preview-block">
            <span>원하는 직군</span>
            <div className="tag-row">
              {desiredRoles.length ? desiredRoles.map((role) => (
                <SkillTag key={role} label={role} tone="ai" />
              )) : <small>미입력</small>}
            </div>
          </div>
          <div className="profile-preview-block">
            <span>기술</span>
            <div className="tag-row">
              {skills.length ? skills.map((skill) => (
                <SkillTag key={skill} label={skill} tone="ai" />
              )) : <small>미입력</small>}
            </div>
          </div>
          <div className="profile-preview-block">
            <span>자격증</span>
            <div className="tag-row">
              {certificates.length ? certificates.map((certificate) => (
                <SkillTag key={certificate} label={certificate} tone="success" />
              )) : <small>미입력</small>}
            </div>
          </div>
          <div className="profile-preview-block">
            <span>어학</span>
            <div className="tag-row">
              {languages.length ? languages.map((language) => (
                <SkillTag key={language} label={language} tone="success" />
              )) : <small>미입력</small>}
            </div>
          </div>
          <div className="profile-preview-block">
            <span>개발 경험</span>
            <div className="stack-list">
              {projectTypes.length ? <strong>프로젝트 형태</strong> : null}
              {projectTypes.map((project) => (
                <span key={project}>{project}</span>
              ))}
              {responsibilities.length ? <strong>담당 경험</strong> : null}
              {responsibilities.map((project) => (
                <span key={project}>{project}</span>
              ))}
              {customExperiences.length ? <strong>직접 추가</strong> : null}
              {customExperiences.map((project) => (
                <span key={project}>{project}</span>
              ))}
              {!projects.length ? <small>미입력</small> : null}
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}

function RecommendationResultsSection() {
  const isAuthenticated = useUserStore((state) => state.isAuthenticated);
  const {
    result,
    status,
    isLoading,
    message,
    error,
    loadRecommendations,
  } = useRecommendStore();

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let timeoutId: number | undefined;
    let isMounted = true;
    const startedAt = Date.now();

    async function pollRecommendations() {
      const nextStatus = await loadRecommendations();
      if (!isMounted) {
        return;
      }
      if (nextStatus === 'pending' && Date.now() - startedAt < 60_000) {
        timeoutId = window.setTimeout(pollRecommendations, 3000);
      }
    }

    void pollRecommendations();

    return () => {
      isMounted = false;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [isAuthenticated, loadRecommendations]);

  return (
    <section className="recommendation-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AI Recommendation</p>
          <h2>AI 맞춤추천</h2>
          <p>프로필을 저장하면 유저 스펙 기반 추천 공고와 부족 역량, 로드맵을 함께 보여줍니다.</p>
        </div>
      </div>

      {!isAuthenticated ? (
        <div className="empty-state">
          <strong>로그인 후 맞춤추천을 확인할 수 있습니다.</strong>
          <span>프로필을 입력하면 추천 결과가 자동으로 생성됩니다.</span>
        </div>
      ) : (
        <>
          {isLoading && status === 'idle' ? (
            <div className="loading-panel">
              <span className="loading-dot" />
              <p>추천 결과를 불러오는 중입니다.</p>
            </div>
          ) : null}
          <div className="recommendation-layout">
            <JobsPage compact jobsOverride={result?.jobs ?? []} />
            <AIAnalysisPanel result={result} status={status} message={message} error={error} />
          </div>
        </>
      )}
    </section>
  );
}

function JobsPage({ compact = false, jobsOverride }: { compact?: boolean; jobsOverride?: Job[] }) {
  const {
    jobs,
    isLoadingJobs,
    jobsError,
    loadJobs,
    query,
    selectedSkill,
    setQuery,
    setSelectedSkill,
    toggleSaved,
  } = useCareerStore();

  useEffect(() => {
    if (!jobsOverride) {
      void loadJobs();
    }
  }, [jobsOverride, loadJobs]);

  const normalizedQuery = query.trim().toLowerCase();
  const sourceJobs = jobsOverride ?? jobs;
  const filteredJobs = sourceJobs.filter((job) => {
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
      {!compact ? <RecommendationResultsSection /> : null}
      {!compact ? (
        <div className="section-heading jobs-section-heading">
          <div>
            <p className="eyebrow">All Jobs</p>
            <h2>전체 채용공고</h2>
          </div>
        </div>
      ) : null}
      <SearchFilterBar
        query={query}
        selectedSkill={selectedSkill}
        skills={filterSkills}
        onQueryChange={setQuery}
        onSkillChange={setSelectedSkill}
      />
      {isLoadingJobs ? (
        <div className="loading-panel">
          <span className="loading-dot" />
          <p>채용공고를 불러오는 중입니다.</p>
        </div>
      ) : null}
      {!isLoadingJobs && jobsError ? <p className="auth-error">{jobsError}</p> : null}
      {!isLoadingJobs && !jobsError ? (
        <div className="job-list">
          {filteredJobs.map((job) => (
            <JobCard key={job.id} job={job} onToggleSaved={toggleSaved} />
          ))}
          {filteredJobs.length === 0 ? (
            <div className="empty-state">
              <strong>조건에 맞는 채용공고가 없습니다.</strong>
              <span>검색어나 기술스택 필터를 조정해보세요.</span>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function ActivitiesPage() {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadActivities() {
    setIsLoading(true);
    setError('');
    try {
      setActivities(await listActivities());
    } catch {
      setError('대외활동을 불러오지 못했습니다.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadActivities();
  }, []);

  return (
    <main className="page-shell">
      <div className="page-title">
        <p className="eyebrow">External Activities</p>
        <h1>대외활동</h1>
        <p>DB에 등록된 대외활동을 확인하고, 이후 사용자 스펙 기반 추천에 활용합니다.</p>
      </div>

      <section className="activity-toolbar">
        <div>
          <strong>{isLoading ? '대외활동을 불러오는 중입니다.' : `전체 ${activities.length}개`}</strong>
          <span>해커톤, 공모전, 교육, 커뮤니티 활동 데이터를 카드로 보여줍니다.</span>
        </div>
        <Button variant="secondary" icon={Activity} onClick={loadActivities} disabled={isLoading}>
          새로고침
        </Button>
      </section>

      {error ? <p className="auth-error">{error}</p> : null}
      {isLoading ? (
        <div className="empty-state">
          <strong>대외활동을 불러오는 중입니다.</strong>
          <span>잠시만 기다려주세요.</span>
        </div>
      ) : (
        <section className="activity-grid">
          {activities.map((activity) => (
            <article className="activity-card" key={activity.id}>
              <div className="activity-card-header">
                <span className="status-pill">{activity.category}</span>
                <small>{activity.status || '모집 정보'}</small>
              </div>
              <h3>{activity.title}</h3>
              <div className="meta-row">
                <span>
                  <ExternalLink size={15} />
                  {activity.organizer}
                </span>
                <span>
                  <CalendarDays size={15} />
                  {activity.period}
                </span>
              </div>
              {activity.description ? <p className="reason">{activity.description}</p> : null}
              <div className="tag-row">
                {(activity.tags.length ? activity.tags : ['대외활동']).map((tag) => (
                  <SkillTag key={tag} label={tag} tone="ai" />
                ))}
              </div>
              {activity.url ? (
                <Button variant="secondary" icon={ExternalLink} onClick={() => window.open(activity.url, '_blank', 'noopener,noreferrer')}>
                  자세히 보기
                </Button>
              ) : null}
            </article>
          ))}
          {activities.length === 0 ? (
            <div className="empty-state">
              <strong>표시할 대외활동이 없습니다.</strong>
              <span>DB 컬렉션 이름이나 저장된 데이터를 확인해주세요.</span>
            </div>
          ) : null}
        </section>
      )}
    </main>
  );
}

function RecommendationsPage() {
  const {
    result,
    status,
    isLoading,
    message,
    error,
    loadRecommendations,
  } = useRecommendStore();

  useEffect(() => {
    let timeoutId: number | undefined;
    let isMounted = true;
    const startedAt = Date.now();

    async function pollRecommendations() {
      const nextStatus = await loadRecommendations();
      if (!isMounted) {
        return;
      }
      if (nextStatus === 'pending' && Date.now() - startedAt < 60_000) {
        timeoutId = window.setTimeout(pollRecommendations, 3000);
      }
    }

    void pollRecommendations();

    return () => {
      isMounted = false;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [loadRecommendations]);

  return (
    <main className="page-shell">
      <div className="page-title">
        <p className="eyebrow">AI Recommendation</p>
        <h1>추천 공고와 분석 결과</h1>
      </div>
      {isLoading && status === 'idle' ? (
        <div className="loading-panel">
          <span className="loading-dot" />
          <p>추천 결과를 불러오는 중입니다.</p>
        </div>
      ) : null}
      <div className="recommendation-layout">
        <JobsPage compact jobsOverride={result?.jobs ?? []} />
        <AIAnalysisPanel result={result} status={status} message={message} error={error} />
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

const adminSectionCopy: Record<AdminSection, { title: string; description: string }> = {
  dashboard: {
    title: '운영 대시보드',
    description: '서비스의 핵심 운영 현황을 한눈에 확인합니다.',
  },
  users: {
    title: '사용자 관리',
    description: '가입한 사용자를 확인하고 관리자 권한을 관리합니다.',
  },
  jobs: {
    title: '채용공고 관리',
    description: '수집된 채용공고를 검수하고 노출 상태를 관리하는 영역입니다.',
  },
  activities: {
    title: '대외활동 관리',
    description: '추천에 사용할 대외활동 데이터를 관리하는 영역입니다.',
  },
  skills: {
    title: '스킬 관리',
    description: '추천과 유사도 계산에 쓰이는 기술 키워드를 관리하는 영역입니다.',
  },
  aiLogs: {
    title: 'AI 로그',
    description: 'AI 추천, 분석 요청, 응답 상태를 확인하는 영역입니다.',
  },
  reports: {
    title: '신고/검수',
    description: '부적절한 데이터나 사용자 신고를 검토하는 영역입니다.',
  },
  statistics: {
    title: '통계',
    description: '사용자, 공고, 추천 사용량을 지표로 확인하는 영역입니다.',
  },
  settings: {
    title: '설정',
    description: '서비스 운영 정책과 관리자 설정을 조정하는 영역입니다.',
  },
};

function AdminDashboardOverview({ totalUsers, admins, members }: { totalUsers: number; admins: number; members: number }) {
  return (
    <>
      <div className="admin-stat-grid">
        <article className="admin-stat-card">
          <span>전체 사용자</span>
          <strong>{totalUsers}</strong>
          <small>가입 계정 기준</small>
        </article>
        <article className="admin-stat-card">
          <span>관리자</span>
          <strong>{admins}</strong>
          <small>운영 권한 계정</small>
        </article>
        <article className="admin-stat-card">
          <span>일반 사용자</span>
          <strong>{members}</strong>
          <small>서비스 이용 계정</small>
        </article>
        <article className="admin-stat-card">
          <span>운영 상태</span>
          <strong>정상</strong>
          <small>관리 기능 연결됨</small>
        </article>
      </div>
      <section className="admin-table-card">
        <div className="section-heading">
          <div>
            <h2>관리 메뉴 안내</h2>
            <p>현재 사용자 관리는 바로 사용할 수 있고, 나머지 메뉴는 기능 확장 예정입니다.</p>
          </div>
        </div>
        <div className="admin-module-grid">
          {[
            ['사용자', '계정 목록 조회, 권한 변경, 계정 삭제'],
            ['채용공고', '공고 검수, 숨김 처리, 추천 노출 관리 예정'],
            ['대외활동', '대외활동 데이터 검수 및 추천 노출 관리 예정'],
            ['AI 로그', '추천 요청 및 분석 결과 추적 예정'],
          ].map(([title, description]) => (
            <article key={title} className="admin-module-card">
              <strong>{title}</strong>
              <span>{description}</span>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function AdminComingSoon({ section }: { section: { title: string; description: string } }) {
  return (
    <section className="admin-table-card admin-empty-state">
      <p className="eyebrow">Coming Soon</p>
      <h2>{section.title}</h2>
      <p>{section.description}</p>
      <span>아직 관리 기능은 준비 중입니다. 지금은 사용자 관리와 운영 대시보드를 사용할 수 있습니다.</span>
    </section>
  );
}

function UserAdminPage() {
  const currentUser = useUserStore((state) => state.user);
  const [activeSection, setActiveSection] = useState<AdminSection>('users');
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [busyUserId, setBusyUserId] = useState<number | null>(null);

  const userStats = useMemo(() => {
    const admins = users.filter((user) => user.role === 'ADMIN').length;
    return {
      total: users.length,
      admins,
      members: users.length - admins,
    };
  }, [users]);
  const activeCopy = adminSectionCopy[activeSection];

  async function loadUsers() {
    if (currentUser?.role !== 'ADMIN') {
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      setUsers(await listAdminUsers());
    } catch {
      setError('사용자 목록을 불러오지 못했습니다. 관리자 권한을 확인해주세요.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadUsers();
  }, [currentUser?.role]);

  async function handleRoleChange(userId: number, role: UserRole) {
    setBusyUserId(userId);
    setError('');
    try {
      const updatedUser = await updateAdminUserRole(userId, role);
      setUsers((items) => items.map((user) => (user.id === userId ? updatedUser : user)));
    } catch {
      setError('사용자 권한을 변경하지 못했습니다.');
    } finally {
      setBusyUserId(null);
    }
  }

  async function handleDeleteUser(userId: number) {
    const target = users.find((user) => user.id === userId);
    if (!target || !window.confirm(`${target.email} 계정을 삭제할까요?`)) {
      return;
    }

    setBusyUserId(userId);
    setError('');
    try {
      await deleteAdminUser(userId);
      setUsers((items) => items.filter((user) => user.id !== userId));
    } catch {
      setError('사용자를 삭제하지 못했습니다.');
    } finally {
      setBusyUserId(null);
    }
  }

  return (
    <main className="admin-layout">
      <AdminSidebar activeSection={activeSection} onSectionChange={setActiveSection} />
      <section className="admin-main">
        <div className="page-title">
          <p className="eyebrow">CareerStep Admin</p>
          <h1>{activeCopy.title}</h1>
          <p>{activeCopy.description}</p>
        </div>
        {currentUser?.role === 'ADMIN' ? (
          activeSection === 'users' ? (
            <>
            <div className="admin-stat-grid">
              <article className="admin-stat-card">
                <span>전체 사용자</span>
                <strong>{userStats.total}</strong>
                <small>실시간 계정 현황</small>
              </article>
              <article className="admin-stat-card">
                <span>관리자</span>
                <strong>{userStats.admins}</strong>
                <small>권한 보호 계정</small>
              </article>
              <article className="admin-stat-card">
                <span>일반 사용자</span>
                <strong>{userStats.members}</strong>
                <small>서비스 이용 계정</small>
              </article>
              <article className="admin-stat-card">
                <span>연동 상태</span>
                <strong>{isLoading ? '동기화 중' : '정상'}</strong>
                <small>관리 API 연결됨</small>
              </article>
            </div>
            <section className="admin-table-card">
              <div className="section-heading">
                <div>
                  <h2>사용자 목록</h2>
                  <p>가입한 사용자를 확인하고 관리자 권한을 관리할 수 있습니다.</p>
                </div>
                <Button variant="secondary" icon={RefreshCw} onClick={loadUsers} disabled={isLoading}>
                  새로고침
                </Button>
              </div>
              {error ? <p className="auth-error">{error}</p> : null}
              <table>
                <thead>
                  <tr>
                    <th>이름</th>
                    <th>이메일</th>
                    <th>권한</th>
                    <th>가입일</th>
                    <th>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td>{user.name}</td>
                      <td>{user.email}</td>
                      <td>
                        <select
                          className="admin-select"
                          value={user.role}
                          disabled={busyUserId === user.id}
                          onChange={(event) => handleRoleChange(user.id, event.target.value as UserRole)}
                        >
                          <option value="USER">일반 사용자</option>
                          <option value="ADMIN">관리자</option>
                        </select>
                      </td>
                      <td>{user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</td>
                      <td>
                        <div className="admin-actions">
                          <Button
                            variant="ghost"
                            icon={ShieldCheck}
                            disabled={busyUserId === user.id || user.role === 'ADMIN'}
                            onClick={() => handleRoleChange(user.id, 'ADMIN')}
                          >
                            관리자 지정
                          </Button>
                          <Button
                            variant="ghost"
                            icon={Trash2}
                            disabled={busyUserId === user.id || user.id === currentUser.id}
                            onClick={() => handleDeleteUser(user.id)}
                          >
                            삭제
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!isLoading && users.length === 0 ? (
                    <tr>
                      <td colSpan={5}>표시할 사용자가 없습니다.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </section>
            </>
          ) : activeSection === 'dashboard' ? (
            <AdminDashboardOverview totalUsers={userStats.total} admins={userStats.admins} members={userStats.members} />
          ) : (
            <AdminComingSoon section={activeCopy} />
          )
        ) : (
          <section className="admin-table-card">
            <div className="section-heading">
              <div>
                <h2>관리자 권한이 필요합니다</h2>
                <p>사용자 관리는 관리자 계정으로 로그인한 경우에만 접근할 수 있습니다.</p>
              </div>
            </div>
            {error ? <p className="auth-error">{error}</p> : null}
          </section>
        )}
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
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/signup" element={<AuthPage mode="signup" />} />
        <Route
          path="/account"
          element={
            <ProtectedRoute>
              <AccountPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <ProfileSpecPage />
            </ProtectedRoute>
          }
        />
        <Route path="/jobs" element={<JobsPage />} />
        <Route
          path="/recommendations"
          element={<Navigate to="/jobs" replace />}
        />
        <Route path="/activities" element={<ActivitiesPage />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="ADMIN">
              <UserAdminPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  );
}
