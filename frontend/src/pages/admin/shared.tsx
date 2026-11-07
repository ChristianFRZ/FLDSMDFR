/** Arma la consulta sin los filtros vacíos. */
export function query(params: Record<string, string | number | null | undefined>): string {
  const pairs = Object.entries(params).filter(([, value]) => value !== "" && value != null);
  return new URLSearchParams(pairs.map(([key, value]) => [key, String(value)])).toString();
}

const dateFormat = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });
export const formatDate = (value: string) => dateFormat.format(new Date(value));

type PagerProps = { page: number; size: number; total: number; onPage: (page: number) => void };

export function Pager({ page, size, total, onPage }: PagerProps) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages < 2) return null;
  return (
    <nav className="pager" aria-label="Páginas">
      <button className="ghost" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>Anterior</button>
      <span>Página {page} de {pages}</span>
      <button className="ghost" type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>Siguiente</button>
    </nav>
  );
}
