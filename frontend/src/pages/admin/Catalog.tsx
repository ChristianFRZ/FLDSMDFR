import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Page, Song } from "../../api/types";
import { Pager, query } from "./shared";

type Job = { id: string; status: string; imported: number; error: string | null };

const unfinished = (job?: Job) => job?.status === "pending" || job?.status === "running";

function jobText(job: Job): string {
  if (job.status === "done") return `Terminada: ${job.imported} pistas importadas`;
  if (job.status === "failed") return `Se detuvo tras ${job.imported} pistas${job.error ? `: ${job.error}` : ""}`;
  if (job.status === "pending") return "En espera";
  return `En curso: ${job.imported} pistas importadas`;
}

function ImportPanel() {
  const client = useQueryClient();
  const [genres, setGenres] = useState("");
  const [limit, setLimit] = useState(50);
  const [jobId, setJobId] = useState<string | null>(null);
  const jobs = useQuery({ queryKey: ["import-jobs"], queryFn: () => api<Job[]>("/api/admin/catalog/import") });
  const job = useQuery({
    queryKey: ["import-job", jobId],
    queryFn: () => api<Job>(`/api/admin/catalog/import/${jobId}`),
    enabled: jobId !== null,
    refetchInterval: (current) => (unfinished(current.state.data) ? 2000 : false),
  });
  const start = useMutation({
    mutationFn: () =>
      api<{ job_id: string }>("/api/admin/catalog/import", {
        method: "POST",
        json: { genres: genres.split(",").map((g) => g.trim()).filter(Boolean), limit_per_genre: limit },
      }),
    onSuccess: (created) => setJobId(created.job_id),
  });
  const resume = useMutation({
    mutationFn: (id: string) => api(`/api/admin/catalog/import/${id}/resume`, { method: "POST" }),
    onSuccess: (_, id) => {
      setJobId(id);
      void client.invalidateQueries({ queryKey: ["import-job", id] });
      void client.invalidateQueries({ queryKey: ["import-jobs"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    start.mutate();
  }

  const failure = start.error ?? resume.error;
  const earlier = jobs.data?.filter((item) => item.id !== jobId).slice(0, 5) ?? [];
  return (
    <section>
      <h2>Importar de Jamendo</h2>
      <form className="stack-form" onSubmit={submit}>
        <label>Géneros<input placeholder="rock, jazz, ambient" value={genres} onChange={(e) => setGenres(e.target.value)} /></label>
        <label>
          Pistas por género
          <input type="number" min={1} max={5000} value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
        </label>
        {failure instanceof ApiError && <p className="form-error" role="alert">{failure.message}</p>}
        <button className="primary" type="submit" disabled={start.isPending || unfinished(job.data)}>Importar de Jamendo</button>
      </form>
      {job.data && <p role="status">{jobText(job.data)}</p>}
      {job.data?.status === "failed" && jobId && (
        <button className="ghost" type="button" onClick={() => resume.mutate(jobId)}>Reanudar</button>
      )}
      {earlier.length > 0 && (
        <ul className="plain-list">
          {earlier.map((item) => (
            <li key={item.id}>
              {jobText(item)}{" "}
              {item.status === "failed" && <button className="link" type="button" onClick={() => resume.mutate(item.id)}>Reanudar</button>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

type AdminSong = Song & { hidden_by_admin: boolean };

const STATUS: Record<string, string> = { draft: "Borrador", scheduled: "Programada", published: "Publicada", hidden: "Oculta" };

function statusLabel(song: AdminSong): string {
  if (song.status === "hidden" && !song.hidden_by_admin) return "Oculta por su Compositor";
  return STATUS[song.status] ?? song.status;
}

function SongRow({ song, onError }: { song: AdminSong; onError: (message: string | null) => void }) {
  const client = useQueryClient();
  const [hiding, setHiding] = useState(false);
  const [reason, setReason] = useState("");
  const act = useMutation({
    mutationFn: (restore: boolean) =>
      restore
        ? api(`/api/admin/songs/${song.id}/restore`, { method: "POST" })
        : api(`/api/admin/songs/${song.id}/hide`, { method: "POST", json: { reason: reason.trim() } }),
    onMutate: () => onError(null),
    onError: (error) => onError(error instanceof ApiError ? error.message : "No se pudo. Intenta de nuevo."),
    onSettled: () => {
      setHiding(false);
      void client.invalidateQueries({ queryKey: ["admin-songs"] });
    },
  });
  return (
    <tr>
      <td>{song.title}</td>
      <td>{song.artist}</td>
      <td>{song.source === "jamendo" ? "Jamendo" : "Local"}</td>
      <td>{statusLabel(song)}</td>
      <td className="cell-actions">
        {song.hidden_by_admin && <button className="ghost" type="button" onClick={() => act.mutate(true)}>Restaurar</button>}
        {!song.hidden_by_admin && !hiding && <button className="ghost" type="button" onClick={() => setHiding(true)}>Ocultar</button>}
        {hiding && (
          <>
            <input aria-label={`Motivo para ocultar ${song.title}`} placeholder="Motivo" maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
            <button className="ghost danger" type="button" disabled={!reason.trim()} onClick={() => act.mutate(false)}>Confirmar</button>
            <button className="ghost" type="button" onClick={() => setHiding(false)}>Cancelar</button>
          </>
        )}
      </td>
    </tr>
  );
}

export function Catalog() {
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [source, setSource] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [problem, setProblem] = useState<string | null>(null);
  const songs = useQuery({
    queryKey: ["admin-songs", q, source, status, page],
    queryFn: () => api<Page<AdminSong>>(`/api/admin/songs?${query({ q, source, status, page })}`),
    placeholderData: keepPreviousData,
  });

  function search(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setQ(text);
  }

  return (
    <>
      <ImportPanel />
      <section>
        <h2>Pistas</h2>
        <form className="filters" onSubmit={search}>
          <label>Buscar<input type="search" value={text} onChange={(e) => setText(e.target.value)} /></label>
          <label>
            Fuente
            <select value={source} onChange={(e) => { setSource(e.target.value); setPage(1); }}>
              <option value="">Todas</option>
              <option value="jamendo">Jamendo</option>
              <option value="local">Local</option>
            </select>
          </label>
          <label>
            Estado
            <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
              <option value="">Todos</option>
              <option value="published">Publicada</option>
              <option value="hidden">Oculta</option>
            </select>
          </label>
        </form>
        {problem && <p className="form-error" role="alert">{problem}</p>}
        {songs.isError && <p className="form-error" role="alert">No se pudo cargar el catálogo.</p>}
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th scope="col">Título</th><th scope="col">Artista</th><th scope="col">Fuente</th><th scope="col">Estado</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead>
            <tbody>{songs.data?.items.map((song) => <SongRow key={song.id} song={song} onError={setProblem} />)}</tbody>
          </table>
        </div>
        {songs.isSuccess && !songs.data.items.length && <p className="muted">No hay pistas con esos filtros.</p>}
        {songs.data && <Pager page={songs.data.page} size={songs.data.size} total={songs.data.total} onPage={setPage} />}
      </section>
    </>
  );
}
