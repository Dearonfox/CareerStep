import type { CSSProperties } from 'react';

export function ProfileProgressCard() {
  return (
    <div className="profile-progress">
      <div className="progress-copy">
        <span>프로필 완성도</span>
        <strong>86%</strong>
        <p>프로젝트 설명과 배포 링크를 보강하면 추천 정확도가 더 좋아집니다.</p>
      </div>
      <div className="progress-ring" style={{ '--progress': '86%' } as CSSProperties}>
        <span>86</span>
      </div>
    </div>
  );
}
