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
  { label: 'Dashboard', icon: LayoutDashboard },
  { label: 'Users', icon: Users },
  { label: 'Jobs', icon: BriefcaseBusiness },
  { label: 'Activities', icon: Activity },
  { label: 'Skills', icon: Tags },
  { label: 'AI Logs', icon: Sparkles },
  { label: 'Violations', icon: ShieldAlert },
  { label: 'Statistics', icon: BarChart3 },
  { label: 'Settings', icon: Settings },
];

export function AdminSidebar() {
  return (
    <aside className="admin-sidebar">
      <div className="admin-brand">CareerStep Admin</div>
      <nav>
        {items.map((item, index) => {
          const Icon = item.icon;
          return (
            <button key={item.label} className={index === 0 ? 'active' : ''}>
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
