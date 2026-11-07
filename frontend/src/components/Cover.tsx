const gradients = [
  "linear-gradient(135deg,#FF7A1A,#FF3D8B)",
  "linear-gradient(135deg,#00D1BE,#4A5CFF)",
  "linear-gradient(135deg,#FFD233,#00D1BE)",
  "linear-gradient(135deg,#FF3D8B,#4A5CFF)",
];

function pick(id: string): string {
  let sum = 0;
  for (const char of id) sum += char.charCodeAt(0);
  return gradients[sum % gradients.length];
}

/** Sin portada se usa un degradado estable por pista: la misma pista siempre se ve igual. */
export function Cover({ id, url, className = "cover" }: { id: string; url: string | null; className?: string }) {
  return <div className={className} style={{ background: url ? `center / cover url("${url}")` : pick(id) }} />;
}
