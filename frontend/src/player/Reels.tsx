/** Carretes que pasan la cinta de uno al otro según el avance. */
export function Reels({ progress, spinning, children }: { progress: number; spinning: boolean; children: React.ReactNode }) {
  const left = 26 - 14 * progress;
  const right = 12 + 14 * progress;
  const className = spinning ? "reel reel-spin" : "reel";
  return (
    <div className="reels">
      <span className={className} style={{ width: left, height: left }} aria-hidden="true" />
      {children}
      <span className={className} style={{ width: right, height: right }} aria-hidden="true" />
    </div>
  );
}
