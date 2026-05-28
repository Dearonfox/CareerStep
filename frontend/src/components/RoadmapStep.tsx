import type { RoadmapItem } from '../types';

type RoadmapStepProps = {
  item: RoadmapItem;
};

export function RoadmapStep({ item }: RoadmapStepProps) {
  return (
    <div className={`roadmap-step roadmap-step-${item.status}`}>
      <span>{item.step}</span>
      <div>
        <h4>{item.title}</h4>
        <p>{item.description}</p>
      </div>
    </div>
  );
}
