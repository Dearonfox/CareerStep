type SkillTagProps = {
  label: string;
  tone?: 'default' | 'gap' | 'ai' | 'success';
};

export function SkillTag({ label, tone = 'default' }: SkillTagProps) {
  return <span className={`skill-tag skill-tag-${tone}`}>{label}</span>;
}
