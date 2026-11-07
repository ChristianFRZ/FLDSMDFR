import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useInviteActions, usePendingInvites, useTapes } from "../api/queries";
import type { HistoryItem, Page, Releases, Song } from "../api/types";
import { Cover } from "../components/Cover";
import { Note } from "../components/Note";
import { TapePile } from "../components/TapePile";
import { usePlayer } from "../player/PlayerProvider";

const dateFormat = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });

function Invitations() {
  const navigate = useNavigate();
  const invites = usePendingInvites();
  const { join, dismiss } = useInviteActions();
  return (
    <div className="invites">
      {invites.data?.map((invite) => (
        <Note key={invite.invite_id} tape color="yellow" className="invite">
          {invite.inviter} te invitó a «{invite.title}»
          <div className="invite-actions">
            <button
              type="button"
              onClick={() => join.mutate(invite.invite_id, { onSuccess: (body) => navigate(`/tapes/${body.tape_id}`) })}
            >
              Unirme al casete
            </button>
            <button type="button" onClick={() => dismiss.mutate(invite.invite_id)}>Ahora no</button>
          </div>
        </Note>
      ))}
      {join.error instanceof ApiError && <p className="form-error" role="alert">{join.error.message}</p>}
    </div>
  );
}

function KeepListening() {
  const { play } = usePlayer();
  const history = useQuery({
    queryKey: ["history", "home"],
    queryFn: () => api<Page<HistoryItem>>("/api/playbacks/history?size=12"),
  });
  const songs = [
    ...new Map(
      (history.data?.items ?? []).flatMap((item) => (item.song ? [[item.song.id, item.song] as const] : [])),
    ).values(),
  ].slice(0, 5);
  return (
    <div className="quick">
      {songs.map((song: Song) => (
        <button key={song.id} type="button" disabled={!song.available} onClick={() => play([song])}>
          <Cover id={song.id} url={song.cover_url} className="cover-quick" />
          <b>{song.title}</b>
        </button>
      ))}
      <Link to="/favorites"><span className="swatch swatch-yellow" /><b>Favoritas</b></Link>
    </div>
  );
}

function Launches() {
  const { play } = usePlayer();
  const releases = useQuery({ queryKey: ["releases"], queryFn: () => api<Releases>("/api/releases") });
  if (releases.data?.degraded) return <p className="muted">Los lanzamientos no están disponibles por ahora.</p>;
  const scheduled = releases.data?.scheduled ?? [];
  const published = releases.data?.published ?? [];
  if (!scheduled.length && !published.length) {
    return <p className="muted">Sigue a un artista y aquí verás lo que publique.</p>;
  }
  return (
    <div className="launches">
      {scheduled.map((item) => (
        <div key={item.song_id}>
          <Cover id={item.song_id} url={null} />
          <b>{item.title}</b>
          <small>{item.artist} · Sale el {dateFormat.format(new Date(item.publish_at))}</small>
        </div>
      ))}
      {published.map(({ song }) => (
        <button key={song.id} type="button" aria-label={`Reproducir ${song.title}`} onClick={() => play([song])}>
          <Cover id={song.id} url={song.cover_url} />
          <b>{song.title}</b>
          <small>{song.artist}</small>
        </button>
      ))}
    </div>
  );
}

export function Home() {
  const tapes = useTapes();
  return (
    <div className="home">
      <h1 className="page-title">Tus casetes</h1>
      <Invitations />
      {tapes.data?.length ? (
        <TapePile tapes={tapes.data} />
      ) : (
        tapes.isSuccess && (
          <Note tape className="empty-note">
            Aún no hay casetes. Arma uno con tus amigos.
            <Link to="/tapes/new">Crear tu primer casete</Link>
          </Note>
        )
      )}
      <h2>Seguir escuchando</h2>
      <KeepListening />
      <h2>Lanzamientos de artistas que sigues</h2>
      <Launches />
    </div>
  );
}
