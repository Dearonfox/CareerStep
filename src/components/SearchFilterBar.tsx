import { Search } from 'lucide-react';
import { Button } from './Button';

type SearchFilterBarProps = {
  query: string;
  selectedSkill: string;
  skills: string[];
  onQueryChange: (query: string) => void;
  onSkillChange: (skill: string) => void;
};

export function SearchFilterBar({
  query,
  selectedSkill,
  skills,
  onQueryChange,
  onSkillChange,
}: SearchFilterBarProps) {
  return (
    <div className="search-filter-bar">
      <label className="search-field">
        <Search size={18} />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="직무, 회사, 기술스택 검색"
        />
      </label>
      <div className="segmented-control" aria-label="기술스택 필터">
        {skills.map((skill) => (
          <Button
            key={skill}
            variant={selectedSkill === skill ? 'primary' : 'secondary'}
            onClick={() => onSkillChange(skill)}
          >
            {skill}
          </Button>
        ))}
      </div>
    </div>
  );
}
