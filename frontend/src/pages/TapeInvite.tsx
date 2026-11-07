import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { TapeSummary } from "../api/types";
import { Note } from "../components/Note";
import { Tape } from "../components/Tape";

type Preview = {
  title: string;
  color: TapeSummary["color"];
  inviter: string | null;
  already_member: boolean;
  tape_id: string | null;
};

export function TapeInvite() {
  const { token } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const preview = useQuery({
    queryKey: ["invite", token],
    queryFn: () => api<Preview>(`/api/tapes/invites/${token}`),
    retry: false,
    staleTime: Infinity,
  });
  const refresh = () => {
    for (const queryKey of [["invites"], ["tapes"], ["notices"]]) void client.invalidateQueries({ queryKey });
  };
  const join = useMutation({
    mutationFn: () => api<{ tape_id: string }>(`/api/tapes/join/${token}`, { method: "POST" }),
    onSuccess: (body) => {
      refresh();
      navigate(`/tapes/${body.tape_id}`, { replace: true });
    },
  });
  const dismiss = useMutation({
    mutationFn: () => api(`/api/tapes/invites/${token}/dismiss`, { method: "POST" }),
    onSuccess: () => {
      refresh();
      navigate("/", { replace: true });
    },
  });

  if (preview.isError) {
    return (
      <div className="invite-page">
        <p className="form-error" role="alert">{preview.error.message}</p>
        <p className="muted">Pídele a quien te invitó un enlace nuevo.</p>
        <Link className="ghost" to="/">Volver a Inicio</Link>
      </div>
    );
  }
  if (!preview.data) return <p role="status">Cargando…</p>;
  if (preview.data.already_member) return <Navigate to={`/tapes/${preview.data.tape_id}`} replace />;

  const { title, color, inviter } = preview.data;
  return (
    <div className="invite-page">
      <Tape title={title} color={color} tilt={-3} />
      <Note tape color="yellow" className="invite invite-wide">
        {inviter} te invitó a «{title}»
        <div className="invite-actions">
          <button type="button" disabled={join.isPending} onClick={() => join.mutate()}>Unirme al casete</button>
          <button type="button" onClick={() => dismiss.mutate()}>Ahora no</button>
        </div>
      </Note>
      {join.error && <p className="form-error" role="alert">{join.error.message}</p>}
    </div>
  );
}
