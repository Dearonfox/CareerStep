import {
  Activity,
  BarChart3,
  BriefcaseBusiness,
  LayoutDashboard,
  Settings,
  ShieldAlert,
  Sparkles,
  Tags,
  Users,
} from 'lucide-react';

const items = [
  { label: '대시보드', icon: LayoutDashboard },
  { label: '사용자', icon: Users },
  { label: '채용공고', icon: BriefcaseBusiness },
  { label: '대외활동', icon: Activity },
  { label: '스킬', icon: Tags },
  { label: 'AI 로그', icon: Sparkles },
  { label: '신고/검수', icon: ShieldAlert },
  { label: '통계', icon: BarChart3 },
  { label: '설정', icon: Settings },
];

export function AdminSidebar() {
  return (
    <aside className="admin-sidebar">
      <div className="admin-brand">CareerStep 관리자</div>
      <nav>
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.label} className={item.label === '사용자' ? 'active' : ''}>
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
