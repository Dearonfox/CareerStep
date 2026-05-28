import type { ReactNode } from 'react';

type DashboardCardProps = {
  title: string;
  subtitle?: string;
  className?: string;
  children: ReactNode;
};

export function DashboardCard({ title, subtitle, className = '', children }: DashboardCardProps) {
  return (
    <section className={`dashboard-card ${className}`}>
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}
