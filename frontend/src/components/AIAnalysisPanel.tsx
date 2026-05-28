import { Bot, CheckCircle2, Sparkles, Wand2 } from 'lucide-react';
import { roadmap } from '../data/mockData';
import { RoadmapStep } from './RoadmapStep';
import { SkillTag } from './SkillTag';

export function AIAnalysisPanel() {
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

      <div className="analysis-block">
        <h3>
          <CheckCircle2 size={18} />
          내 강점
        </h3>
        <p>React 기반 화면 구현, API 연동, 사용자 플로우를 고려한 컴포넌트 설계가 강점입니다.</p>
        <div className="tag-row">
          {['UI 구현', 'TypeScript', 'API 연동'].map((skill) => (
            <SkillTag key={skill} label={skill} tone="success" />
          ))}
        </div>
      </div>

      <div className="analysis-block">
        <h3>
          <Sparkles size={18} />
          부족 역량
        </h3>
        <div className="tag-row">
          {['테스트 코드', 'AWS 배포', '접근성'].map((skill) => (
            <SkillTag key={skill} label={skill} tone="gap" />
          ))}
        </div>
      </div>

      <div className="analysis-block">
        <h3>
          <Wand2 size={18} />
          추천 학습 로드맵
        </h3>
        <div className="roadmap-list">
          {roadmap.map((item) => (
            <RoadmapStep key={item.step} item={item} />
          ))}
        </div>
      </div>

      <div className="next-action">
        <strong>다음 액션</strong>
        <p>이번 주에는 관심 공고 3개를 기준으로 자기소개서 문항을 먼저 정리하세요.</p>
      </div>
    </aside>
  );
}
