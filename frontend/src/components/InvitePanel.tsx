import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { TapeDetail } from "../api/types";
import { Icon } from "./Icon";

type Created = { id: string; token: string };

const dateFormat = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });

export function InvitePanel({ tape }: { tape: TapeDetail }) {
  const client = useQueryClient();
  const [kind, setKind] = useState<"single" | "many">("single");
  const [uses, setUses] = useState(5);
  const [hours, setHours] = useState(48);
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const refresh = () => void client.invalidateQueries({ queryKey: ["tape", tape.id] });

  const create = useMutation({
    mutationFn: () =>
      api<Created>(`/api/tapes/${tape.id}/invites`, {
        method: "POST",
        json: kind === "single" ? { max_uses: 1 } : { max_uses: uses, expires_in_hours: hours },
      }),
    onSuccess: (invite) => {
      setLink(`${window.location.origin}/invite/${invite.token}`);
      setCopied(false);
      refresh();
    },
  });

  const revoke = useMutation({
    mutationFn: (inviteId: string) => api(`/api/tapes/${tape.id}/invites/${inviteId}`, { method: "DELETE" }),
    onSuccess: refresh,
  });

  async function copy() {
    if (!link) return;
    await navigator.clipboard?.writeText(link).catch(() => undefined);
    setCopied(true);
  }

  return (
    <section className="invite-panel">
      <h2>Invitar por enlace</h2>
      <p className="muted">{tape.members.length} de {tape.max_members} personas: {tape.members.map((m) => m.name).join(", ")}</p>
      <fieldset>
        <legend>Tipo de enlace</legend>
        <label><input type="radio" name="kind" checked={kind === "single"} onChange={() => setKind("single")} /> Un solo uso</label>
        <label><input type="radio" name="kind" checked={kind === "many"} onChange={() => setKind("many")} /> Varios usos, con caducidad</label>
      </fieldset>
      {kind === "many" && (
        <div className="filters">
          <label>
            Usos
            <input type="number" min={1} max={100} value={uses} onChange={(e) => setUses(Number(e.target.value))} />
          </label>
          <label>
            Horas
            <input type="number" min={1} max={720} value={hours} onChange={(e) => setHours(Number(e.target.value))} />
          </label>
        </div>
      )}
      <button className="ghost" type="button" disabled={create.isPending} onClick={() => create.mutate()}>
        <Icon name="link" />Crear enlace
      </button>
      {create.error instanceof ApiError && <p className="form-error" role="alert">{create.error.message}</p>}
      {link && (
        <div className="invite-link">
          <input readOnly aria-label="Enlace de invitación" value={link} onFocus={(e) => e.target.select()} />
          <button className="ghost" type="button" onClick={() => void copy()}>{copied ? "Copiado" : "Copiar"}</button>
          <small>Guárdalo ahora: por seguridad no se vuelve a mostrar.</small>
        </div>
      )}
      {tape.is_creator && tape.invites.length > 0 && (
        <>
          <h3>Enlaces activos</h3>
          <ul className="invite-rows">
            {tape.invites.map((invite) => (
              <li key={invite.id}>
                <span>
                  {invite.uses} de {invite.max_uses} usos
                  {invite.expires_at ? ` · caduca ${dateFormat.format(new Date(invite.expires_at))}` : ""}
                </span>
                <button className="ghost" type="button" onClick={() => revoke.mutate(invite.id)}>Revocar</button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
