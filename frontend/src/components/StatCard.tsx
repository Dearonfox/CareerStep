import type { Stat } from '../types';

type StatCardProps = {
  stat: Stat;
};

export function StatCard({ stat }: StatCardProps) {
  const Icon = stat.icon;

  return (
    <article className={`stat-card stat-card-${stat.tone}`}>
      <div className="stat-icon">
        <Icon size={20} />
      </div>
      <span>{stat.label}</span>
      <strong>{stat.value}</strong>
    </article>
  );
}
