import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, ApiError } from "../../api/client";

type Request = { id: string; status: string; reason: string | null };

const statusText: Record<string, string> = {
  pending: "Tu solicitud está en revisión.",
  approved: "Tu solicitud fue aprobada.",
  rejected: "Tu solicitud fue rechazada.",
};

export function ComposerRequest() {
  const client = useQueryClient();
  const [message, setMessage] = useState("");
  const requests = useQuery({
    queryKey: ["composer-requests"],
    queryFn: () => api<Request[]>("/api/composer-requests/mine"),
  });
  const send = useMutation({
    mutationFn: () => api("/api/composer-requests", { method: "POST", json: { message } }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["composer-requests"] }),
  });
  const latest = requests.data?.[0];

  function submit(event: FormEvent) {
    event.preventDefault();
    send.mutate();
  }

  return (
    <section>
      <h2>Publica tu música</h2>
      {latest && <p className="muted">{statusText[latest.status]}{latest.reason ? ` Motivo: ${latest.reason}` : ""}</p>}
      {requests.isSuccess && latest?.status !== "pending" && (
        <form className="stack-form" onSubmit={submit}>
          <label>
            Cuéntanos sobre tu música
            <textarea rows={3} maxLength={500} value={message} onChange={(e) => setMessage(e.target.value)} />
          </label>
          {send.error instanceof ApiError && <p className="form-error" role="alert">{send.error.message}</p>}
          <button className="primary" type="submit" disabled={send.isPending}>Solicitar ser Compositor</button>
        </form>
      )}
    </section>
  );
}
