import { useState } from "react";
import { Link } from "react-router-dom";
import { useFollows, usePendingInvites, usePlaylists, useTapes } from "../api/queries";
import { Icon } from "./Icon";
import { orderLibrary } from "./libraryOrder";
import { useLibraryPrefs } from "./libraryPrefs";
import { LibrarySortSelect } from "./LibrarySortSelect";
import { PinButton } from "./PinButton";
import { tapeHex } from "./tapeColors";

type Tab = "tapes" | "playlists" | "artists";

const tabs: { id: Tab; label: string }[] = [
  { id: "tapes", label: "Casetes" },
  { id: "playlists", label: "Playlists" },
  { id: "artists", label: "Artistas" },
];

function Tapes() {
  const tapes = useTapes();
  const invites = usePendingInvites();
  const { pinned, sort } = useLibraryPrefs();
  const ordered = orderLibrary(tapes.data ?? [], pinned, sort, { id: (tape) => tape.id, name: (tape) => tape.title });
  return (
    <>
      {ordered.map((tape) => (
        <div className="lib-item" key={tape.id}>
          <Link className="lib-row" to={`/tapes/${tape.id}`}>
            <span className="swatch" style={{ background: tapeHex(tape.color) }} />
            <span>
              <b>{tape.title}</b>
              <small>{tape.track_count} de {tape.max_tracks} · {tape.member_count === 1 ? "1 persona" : `${tape.member_count} personas`}</small>
            </span>
          </Link>
          <PinButton id={tape.id} label={tape.title} />
        </div>
      ))}
      {invites.data?.map((invite) => (
        <Link className="lib-row" key={invite.invite_id} to="/library">
          <span className="swatch swatch-paper" />
          <span>
            <b>{invite.title}</b>
            <small>Invitación pendiente</small>
          </span>
        </Link>
      ))}
    </>
  );
}

function Playlists() {
  const playlists = usePlaylists();
  const { pinned, sort } = useLibraryPrefs();
  const ordered = orderLibrary(playlists.data ?? [], pinned, sort, { id: (playlist) => playlist.id, name: (playlist) => playlist.name });
  return (
    <>
      {ordered.map((playlist) => (
        <div className="lib-item" key={playlist.id}>
          <Link className="lib-row" to={`/playlists/${playlist.id}`}>
            <span className="swatch swatch-paper" />
            <span><b>{playlist.name}</b></span>
          </Link>
          <PinButton id={playlist.id} label={playlist.name} />
        </div>
      ))}
    </>
  );
}

function Artists() {
  const follows = useFollows();
  const { pinned, sort } = useLibraryPrefs();
  const ordered = orderLibrary(follows.data ?? [], pinned, sort, { id: (artist) => artist.id, name: (artist) => artist.name });
  return (
    <>
      {ordered.map((artist) => (
        <div className="lib-item" key={artist.id}>
          <Link className="lib-row" to={`/artists/${artist.id}`}>
            <span className="swatch swatch-teal" />
            <span><b>{artist.name}</b></span>
          </Link>
          <PinButton id={artist.id} label={artist.name} />
        </div>
      ))}
    </>
  );
}

export function Sidebar() {
  const [tab, setTab] = useState<Tab>("tapes");
  return (
    <>
      <Link className="primary create" to="/tapes/new"><Icon name="plus" />Crear casete</Link>
      <div className="pills" role="group" aria-label="Filtrar biblioteca">
        {tabs.map((item) => (
          <button key={item.id} type="button" aria-pressed={tab === item.id} onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      <LibrarySortSelect />
      <div className="lib">
        {tab === "tapes" && <Tapes />}
        {tab === "playlists" && <Playlists />}
        {tab === "artists" && <Artists />}
      </div>
    </>
  );
}
