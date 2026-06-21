import { Bookmark, Building2, MapPin } from 'lucide-react';
import type { Job } from '../types';
import { Button } from './Button';
import { MatchScoreBadge } from './MatchScoreBadge';
import { SkillTag } from './SkillTag';

type JobCardProps = {
  job: Job;
  onToggleSaved: (jobId: number) => void;
};

export function JobCard({ job, onToggleSaved }: JobCardProps) {
  return (
    <article className="job-card">
      <div className="job-card-header">
        <div>
          <p className="eyebrow">{job.employmentType}</p>
          <h3>{job.title}</h3>
          <div className="meta-row">
            <span>
              <Building2 size={15} />
              {job.company}
            </span>
            <span>
              <MapPin size={15} />
              {job.location}
            </span>
          </div>
        </div>
        {job.matchScore > 0 ? <MatchScoreBadge score={job.matchScore} /> : null}
      </div>

      <div className="tag-row">
        {job.skills.map((skill) => (
          <SkillTag key={skill} label={skill} />
        ))}
      </div>

      <p className="reason">{job.reason}</p>

      {job.gaps.length ? (
        <div className="gap-row">
          <span>보강 필요</span>
          {job.gaps.map((gap) => (
            <SkillTag key={gap} label={gap} tone="gap" />
          ))}
        </div>
      ) : null}

      <div className="card-actions">
        <Button
          variant={job.saved ? 'ai' : 'secondary'}
          icon={Bookmark}
          onClick={() => onToggleSaved(job.id)}
        >
          {job.saved ? '저장됨' : '관심공고'}
        </Button>
        <Button variant="primary">상세보기</Button>
      </div>
    </article>
  );
}
