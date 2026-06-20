import { FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LockKeyhole, Mail, UserRound } from 'lucide-react';
import { login, signup } from '../api/auth';
import { Button } from '../components/Button';
import { useUserStore } from '../store/useUserStore';

type AuthPageProps = {
  mode: 'login' | 'signup';
};

type LocationState = {
  from?: string;
};

export function AuthPage({ mode }: AuthPageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useUserStore((state) => state.setAuth);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const isSignup = mode === 'signup';
  const title = isSignup ? '회원가입' : '로그인';
  const description = isSignup
    ? '커리어 목표와 스펙을 저장하면 CareerStep이 나에게 맞는 채용공고와 준비 방향을 함께 정리해드려요.'
    : '내 스펙, 관심 직무, 준비 현황을 한곳에서 확인하고 AI 추천으로 다음 지원 전략을 빠르게 잡아보세요.';
  const benefits = [
    '내 프로필 기반 채용공고 추천',
    '부족한 역량과 준비 우선순위 분석',
    '대외활동부터 지원 준비까지 한 번에 관리',
  ];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const auth = isSignup
        ? await signup({ name, email, password })
        : await login({ email, password });
      setAuth(auth.user, auth.access_token, auth.refresh_token);
      const state = location.state as LocationState | null;
      navigate(state?.from ?? '/dashboard', { replace: true });
    } catch {
      setError(isSignup ? '회원가입에 실패했습니다.' : '이메일 또는 비밀번호를 확인해주세요.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-shell auth-layout">
      <section className="auth-copy">
        <p className="eyebrow">CareerStep AI Matching</p>
        <h1>{title}</h1>
        <p>{description}</p>
        <div className="auth-benefits">
          {benefits.map((benefit) => (
            <span key={benefit}>{benefit}</span>
          ))}
        </div>
      </section>

      <section className="auth-card">
        <form onSubmit={handleSubmit}>
          {isSignup ? (
            <label className="auth-field">
              이름
              <span>
                <UserRound size={18} />
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  minLength={2}
                  maxLength={100}
                  required
                  placeholder="홍길동"
                />
              </span>
            </label>
          ) : null}

          <label className="auth-field">
            이메일
            <span>
              <Mail size={18} />
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                placeholder="career@example.com"
              />
            </span>
          </label>

          <label className="auth-field">
            비밀번호
            <span>
              <LockKeyhole size={18} />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                required
                placeholder="8자 이상"
              />
            </span>
          </label>

          {error ? <p className="auth-error">{error}</p> : null}

          <Button variant="primary" className="auth-submit" disabled={isSubmitting}>
            {isSubmitting ? '처리 중...' : title}
          </Button>
        </form>

        <p className="auth-switch">
          {isSignup ? '이미 계정이 있나요?' : '아직 계정이 없나요?'}
          <Link to={isSignup ? '/login' : '/signup'}>
            {isSignup ? '로그인' : '회원가입'}
          </Link>
        </p>
      </section>
    </main>
  );
}
