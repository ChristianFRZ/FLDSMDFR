export const LINK_FIELDS = [
  { key: "web", label: "Sitio web" },
  { key: "instagram", label: "Instagram" },
  { key: "bandcamp", label: "Bandcamp" },
];

const labelFor = (key: string) => LINK_FIELDS.find((field) => field.key === key)?.label ?? key;

export function ArtistLinks({ links }: { links: Record<string, string> | null }) {
  const web = Object.entries(links ?? {}).filter(([, url]) => /^https?:\/\//i.test(url));
  if (!web.length) return null;
  return (
    <ul className="artist-links">
      {web.map(([key, url]) => (
        <li key={key}><a href={url} target="_blank" rel="noopener noreferrer">{labelFor(key)}</a></li>
      ))}
    </ul>
  );
}
