type MatchScoreBadgeProps = {
  score: number;
};

export function MatchScoreBadge({ score }: MatchScoreBadgeProps) {
  const tone = score >= 90 ? 'excellent' : score >= 80 ? 'good' : 'steady';

  return (
    <div className={`match-score match-score-${tone}`} aria-label={`AI 적합도 ${score}점`}>
      <span>{score}</span>
      <small>AI 적합도</small>
    </div>
  );
}
