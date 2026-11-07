import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Page } from "../../api/types";
import { formatDate, Pager, query } from "./shared";

type Request = {
  id: string;
  user_name?: string;
  user_email?: string;
  message: string;
  status: string;
  reason: string | null;
  created_at: string;
};

const labels: Record<string, string> = { pending: "Pendiente", approved: "Aprobada", rejected: "Rechazada" };

function Item({ request, onError }: { request: Request; onError: (message: string | null) => void }) {
  const client = useQueryClient();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const decide = useMutation({
    mutationFn: ({ path, json }: { path: string; json: object }) =>
      api(`/api/admin/composer-requests/${request.id}/${path}`, { method: "POST", json }),
    onMutate: () => onError(null),
    onError: (error) => onError(error instanceof ApiError ? error.message : "No se pudo. Intenta de nuevo."),
    onSettled: () => void client.invalidateQueries({ queryKey: ["admin-requests"] }),
  });
  return (
    <li className="request">
      <div>
        <b>{request.user_name}</b> <small>{request.user_email} · {formatDate(request.created_at)}</small>
        <p>{request.message || "Sin mensaje."}</p>
        {request.status !== "pending" && (
          <small>{labels[request.status]}{request.reason ? `: ${request.reason}` : ""}</small>
        )}
      </div>
      {request.status === "pending" && !rejecting && (
        <div className="row-actions">
          <button className="primary" type="button" disabled={decide.isPending} onClick={() => decide.mutate({ path: "approve", json: {} })}>Aprobar</button>
          <button className="ghost" type="button" onClick={() => setRejecting(true)}>Rechazar</button>
        </div>
      )}
      {rejecting && (
        <div className="stack-form">
          <label>
            Motivo del rechazo
            <textarea rows={2} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <div className="row-actions">
            <button
              className="ghost danger"
              type="button"
              disabled={!reason.trim() || decide.isPending}
              onClick={() => decide.mutate({ path: "reject", json: { reason: reason.trim() } })}
            >
              Confirmar rechazo
            </button>
            <button className="ghost" type="button" onClick={() => setRejecting(false)}>Cancelar</button>
          </div>
        </div>
      )}
    </li>
  );
}

export function Requests() {
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(1);
  const [problem, setProblem] = useState<string | null>(null);
  const requests = useQuery({
    queryKey: ["admin-requests", status, page],
    queryFn: () => api<Page<Request>>(`/api/admin/composer-requests?${query({ status, page })}`),
    placeholderData: keepPreviousData,
  });
  return (
    <>
      <div className="filters">
        <label>
          Estado
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="pending">Pendientes</option>
            <option value="approved">Aprobadas</option>
            <option value="rejected">Rechazadas</option>
            <option value="">Todas</option>
          </select>
        </label>
      </div>
      {problem && <p className="form-error" role="alert">{problem}</p>}
      {requests.isError && <p className="form-error" role="alert">No se pudieron cargar las solicitudes.</p>}
      {requests.isSuccess && !requests.data.items.length && <p className="muted">No hay solicitudes aquí.</p>}
      <ul className="requests">
        {requests.data?.items.map((request) => <Item key={request.id} request={request} onError={setProblem} />)}
      </ul>
      {requests.data && <Pager page={requests.data.page} size={requests.data.size} total={requests.data.total} onPage={setPage} />}
    </>
  );
}
