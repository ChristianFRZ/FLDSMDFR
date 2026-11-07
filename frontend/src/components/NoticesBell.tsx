import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Notices } from "../api/types";
import { Icon } from "./Icon";

const POLL_MS = 30_000;

export function NoticesBell() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const notices = useQuery({
    queryKey: ["notices"],
    queryFn: () => api<Notices>("/api/notices"),
    refetchInterval: POLL_MS,
    staleTime: 0,
  });
  const seen = useMutation({
    mutationFn: () => api("/api/notices/seen", { method: "POST" }),
    onSettled: () => void client.invalidateQueries({ queryKey: ["notices"] }),
  });
  const unread = notices.data?.unread ?? 0;

  useEffect(() => {
    if (!open) return;
    const close = (event: Event) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <div className="pop" ref={root}>
      <button
        className="round"
        type="button"
        aria-label={unread ? `Avisos, ${unread} sin leer` : "Avisos"}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <Icon name="bell" />
        {unread > 0 && <em className="badge" aria-hidden="true">{unread}</em>}
      </button>
      {open && (
        <div className="pop-body pop-down" role="group" aria-label="Avisos">
          {notices.data?.degraded && <p className="muted">Los lanzamientos no están disponibles por ahora.</p>}
          {notices.data?.items.length ? (
            <>
              <ul className="notices">
                {notices.data.items.map((item) =>
                  item.type === "invite" ? (
                    <li key={item.invite_id}>
                      <Link to="/library" onClick={() => setOpen(false)}>
                        <b>{item.inviter} te invitó a «{item.title}»</b>
                      </Link>
                    </li>
                  ) : (
                    <li key={item.song.id}>
                      <Link to={`/artists/${item.song.artist_id}`} onClick={() => setOpen(false)}>
                        <b>{item.song.title}</b>
                        <small>Nuevo de {item.song.artist}</small>
                      </Link>
                    </li>
                  ),
                )}
              </ul>
              <button className="ghost" type="button" onClick={() => seen.mutate()}>Marcar como vistos</button>
            </>
          ) : (
            !notices.data?.degraded && <p className="pop-empty">No tienes avisos nuevos.</p>
          )}
        </div>
      )}
    </div>
  );
}
