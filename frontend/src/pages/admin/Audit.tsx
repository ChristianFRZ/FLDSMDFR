import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api } from "../../api/client";
import type { Page } from "../../api/types";
import { formatDate, Pager, query } from "./shared";

type Entry = {
  id: string;
  actor_id: string | null;
  action: string;
  target_type: string;
  target_id: string;
  outcome: string;
  created_at: string;
};

export function Audit() {
  const [text, setText] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const entries = useQuery({
    queryKey: ["admin-audit", action, page],
    queryFn: () => api<Page<Entry>>(`/api/admin/audit?${query({ action, page })}`),
    placeholderData: keepPreviousData,
  });

  function search(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setAction(text.trim());
  }

  return (
    <>
      <form className="filters" onSubmit={search}>
        <label>Acción<input placeholder="role_change" value={text} onChange={(e) => setText(e.target.value)} /></label>
      </form>
      {entries.isError && <p className="form-error" role="alert">No se pudo cargar la auditoría.</p>}
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th scope="col">Fecha</th><th scope="col">Acción</th><th scope="col">Objetivo</th><th scope="col">Resultado</th></tr></thead>
          <tbody>
            {entries.data?.items.map((entry) => (
              <tr key={entry.id}>
                <td>{formatDate(entry.created_at)}</td>
                <td>{entry.action}</td>
                <td>{entry.target_type} {entry.target_id.slice(0, 8)}</td>
                <td>{entry.outcome}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {entries.isSuccess && !entries.data.items.length && <p className="muted">Sin registros.</p>}
      {entries.data && <Pager page={entries.data.page} size={entries.data.size} total={entries.data.total} onPage={setPage} />}
    </>
  );
}
