import { Bot, CheckCircle2, Sparkles, Wand2 } from 'lucide-react';
import type { RecommendationResult, RecommendationStatus } from '../types';
import { RoadmapStep } from './RoadmapStep';
import { SkillTag } from './SkillTag';

type AIAnalysisPanelProps = {
  result: RecommendationResult | null;
  status: RecommendationStatus;
  message?: string;
  error?: string | null;
};

export function AIAnalysisPanel({ result, status, message, error }: AIAnalysisPanelProps) {
  const isWaiting = status === 'idle' || status === 'pending';

  return (
    <aside className="ai-panel">
      <div className="ai-panel-header">
        <div className="ai-avatar">
          <Bot size={22} />
        </div>
        <div>
          <p className="eyebrow">Career Intelligence</p>
          <h2>AI 분석 패널</h2>
        </div>
      </div>

      {isWaiting ? (
        <div className="analysis-block">
          <h3>
            <Sparkles size={18} />
            추천 생성 중
          </h3>
          <p>{message || '추천 결과를 생성 중입니다.'}</p>
        </div>
      ) : null}

      {status === 'no_data' ? (
        <div className="analysis-block">
          <h3>
            <Sparkles size={18} />
            프로필 필요
          </h3>
          <p>{message || '프로필을 저장하면 추천이 생성됩니다.'}</p>
        </div>
      ) : null}

      {status === 'error' ? (
        <div className="analysis-block">
          <h3>
            <Sparkles size={18} />
            추천 오류
          </h3>
          <p>{error || message || '추천 생성 중 오류가 발생했습니다.'}</p>
        </div>
      ) : null}

      {status === 'done' && result ? (
        <>
          {result.policyViolation ? (
            <div className="analysis-block">
              <h3>
                <Sparkles size={18} />
                안내
              </h3>
              <p>추천 결과를 표시할 수 없습니다. 프로필 내용을 확인해 주세요.</p>
            </div>
          ) : null}

          <div className="analysis-block">
            <h3>
              <CheckCircle2 size={18} />
              강점
            </h3>
            <div className="tag-row">
              {result.strengths.map((strength) => (
                <SkillTag key={strength} label={strength} tone="success" />
              ))}
            </div>
          </div>

          <div className="analysis-block">
            <h3>
              <Sparkles size={18} />
              핵심 갭
            </h3>
            <div className="tag-row">
              {result.gaps.map((gap) => (
                <SkillTag key={gap} label={gap} tone="gap" />
              ))}
            </div>
          </div>

          <div className="analysis-block">
            <h3>
              <Wand2 size={18} />
              추천 학습 로드맵
            </h3>
            <div className="roadmap-list">
              {result.roadmap.map((item) => (
                <RoadmapStep key={item.step} item={item} />
              ))}
            </div>
          </div>

          {result.updatedAt ? (
            <div className="next-action">
              <strong>마지막 업데이트</strong>
              <p>{new Date(result.updatedAt).toLocaleString()}</p>
            </div>
          ) : null}
        </>
      ) : null}
    </aside>
  );
}
