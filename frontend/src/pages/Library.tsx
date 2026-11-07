import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useFollows, useInviteActions, usePendingInvites, usePlaylists, useTapes } from "../api/queries";
import type { PlaylistSummary } from "../api/types";
import { Note } from "../components/Note";
import { Icon } from "../components/Icon";
import { TapePile } from "../components/TapePile";

function NewPlaylist() {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: () => api<PlaylistSummary>("/api/playlists", { method: "POST", json: { name } }),
    onSuccess: (playlist) => {
      void client.invalidateQueries({ queryKey: ["playlists"] });
      navigate(`/playlists/${playlist.id}`);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <input aria-label="Nombre de la playlist" placeholder="Nueva playlist" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
      <button className="ghost" type="submit" disabled={create.isPending}>Crear</button>
      {create.error instanceof ApiError && <p className="form-error" role="alert">{create.error.message}</p>}
    </form>
  );
}

export function Library() {
  const navigate = useNavigate();
  const tapes = useTapes();
  const invites = usePendingInvites();
  const playlists = usePlaylists();
  const follows = useFollows();
  const { join, dismiss } = useInviteActions();

  return (
    <>
      <h1 className="page-title">Tu biblioteca</h1>
      {invites.data?.map((invite) => (
        <Note key={invite.invite_id} tape color="yellow" className="invite invite-wide">
          {invite.inviter} te invitó a «{invite.title}»
          <div className="invite-actions">
            <button type="button" onClick={() => join.mutate(invite.invite_id, { onSuccess: (b) => navigate(`/tapes/${b.tape_id}`) })}>
              Unirme al casete
            </button>
            <button type="button" onClick={() => dismiss.mutate(invite.invite_id)}>Descartar</button>
          </div>
        </Note>
      ))}
      {join.error instanceof ApiError && <p className="form-error" role="alert">{join.error.message}</p>}
      <h2>Casetes</h2>
      {/* En escritorio este botón ya está en la barra lateral. */}
      <Link className="primary only-compact" to="/tapes/new"><Icon name="plus" />Crear casete</Link>
      {tapes.data?.length ? <TapePile tapes={tapes.data} /> : <p className="muted">Aún no tienes casetes. <Link to="/tapes/new">Crea uno</Link></p>}
      <h2>Playlists</h2>
      <NewPlaylist />
      <ul className="link-list">
        {playlists.data?.map((playlist) => (
          <li key={playlist.id}><Link to={`/playlists/${playlist.id}`}>{playlist.name}</Link></li>
        ))}
      </ul>
      <h2>Artistas que sigues</h2>
      {follows.data?.length ? (
        <ul className="link-list">
          {follows.data.map((artist) => <li key={artist.id}><Link to={`/artists/${artist.id}`}>{artist.name}</Link></li>)}
        </ul>
      ) : (
        <p className="muted">Sigue a un artista desde su página y sabrás cuándo publica.</p>
      )}
      <h2>Más</h2>
      <ul className="link-list">
        <li><Link to="/favorites">Favoritas</Link></li>
        <li><Link to="/history">Historial</Link></li>
        <li><Link to="/profile">Tu perfil</Link></li>
      </ul>
    </>
  );
}
