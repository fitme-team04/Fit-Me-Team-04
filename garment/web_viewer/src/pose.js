// 역할: 신체와 의류 소매의 자세 차이를 검사합니다.
// Vectors in fit_anchor axes, metres, +Y up, +X toward the avatar's left.
export function compareSleeves(body, garment, policy = { angle: 45, tolerance: 1 }) {
  return ['L', 'R'].map(side => {
    const unit = v => {
      const len = Math.hypot(...v);
      if (!Number.isFinite(len) || len < 1e-7) throw Error('Invalid arm landmarks: ' + side);
      return v.map(x => x / len);
    };
    const b = unit(body[side]), g = unit(garment[side]);
    const angle = v => Math.atan2((side === 'L' ? 1 : -1) * v[0], -v[1]) * 180 / Math.PI;
    const difference = Math.acos(Math.min(1, Math.max(-1, b.reduce((sum, x, i) => sum + x*g[i], 0)))) * 180 / Math.PI;
    const ok = [b,g].every(v => Math.abs(angle(v)-policy.angle)<=policy.tolerance) && difference<=policy.tolerance;
    return {side,body:angle(b),garment:angle(g),difference,ok};
  });
}
