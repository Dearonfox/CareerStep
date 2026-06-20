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
  type LucideIcon,
} from 'lucide-react';

export type AdminSection = 'dashboard' | 'users' | 'jobs' | 'activities' | 'skills' | 'aiLogs' | 'reports' | 'statistics' | 'settings';

type AdminSidebarItem = {
  id: AdminSection;
  label: string;
  icon: LucideIcon;
};

type AdminSidebarProps = {
  activeSection?: AdminSection;
  onSectionChange?: (section: AdminSection) => void;
};

const items: AdminSidebarItem[] = [
  { id: 'dashboard', label: '대시보드', icon: LayoutDashboard },
  { id: 'users', label: '사용자', icon: Users },
  { id: 'jobs', label: '채용공고', icon: BriefcaseBusiness },
  { id: 'activities', label: '대외활동', icon: Activity },
  { id: 'skills', label: '스킬', icon: Tags },
  { id: 'aiLogs', label: 'AI 로그', icon: Sparkles },
  { id: 'reports', label: '신고/검수', icon: ShieldAlert },
  { id: 'statistics', label: '통계', icon: BarChart3 },
  { id: 'settings', label: '설정', icon: Settings },
];

export function AdminSidebar({ activeSection = 'users', onSectionChange }: AdminSidebarProps) {
  return (
    <aside className="admin-sidebar">
      <div className="admin-brand">CareerStep 관리자</div>
      <nav>
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={activeSection === item.id ? 'active' : ''}
              onClick={() => onSectionChange?.(item.id)}
              type="button"
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
