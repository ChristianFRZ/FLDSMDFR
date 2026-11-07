import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, upload } from "../../api/client";
import { FileDrop } from "../../components/FileDrop";

const MP3_MB = 15;
const COVER_MB = 2;
const MB = 1024 * 1024;

type Album = { id: string; title: string };
type Errors = { audio?: string; cover?: string; form?: string };

function checkAudio(file: File | null): string | undefined {
  if (!file) return undefined;
  if (!file.name.toLowerCase().endsWith(".mp3")) return "El archivo debe ser MP3.";
  if (file.size > MP3_MB * MB) return `El MP3 supera ${MP3_MB} MB.`;
  return undefined;
}

function checkCover(file: File | null): string | undefined {
  if (!file) return undefined;
  if (!["image/jpeg", "image/png"].includes(file.type)) return "La portada debe ser JPG o PNG.";
  if (file.size > COVER_MB * MB) return `La portada supera ${COVER_MB} MB.`;
  return undefined;
}

function serverError(error: unknown): Errors {
  if (!(error instanceof ApiError)) return { form: "No se pudo subir la pista. Intenta de nuevo." };
  if (error.code.includes("audio")) return { audio: error.message };
  if (error.code.includes("cover")) return { cover: error.message };
  return { form: error.message };
}

export function TrackForm() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");
  const [license, setLicense] = useState("");
  const [albumId, setAlbumId] = useState("");
  const [publishAt, setPublishAt] = useState("");
  const [audio, setAudio] = useState<File | null>(null);
  const [cover, setCover] = useState<File | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [progress, setProgress] = useState<number | null>(null);
  const albums = useQuery({ queryKey: ["composer-albums"], queryFn: () => api<Album[]>("/api/composer/albums") });

  const send = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("title", title);
      form.set("genre", genre);
      form.set("license", license);
      form.set("audio", audio!);
      if (cover) form.set("cover", cover);
      if (albumId) form.set("album_id", albumId);
      if (publishAt) form.set("publish_at", new Date(publishAt).toISOString());
      setProgress(0);
      return upload("/api/composer/tracks", form, setProgress);
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["composer-tracks"] });
      navigate("/composer");
    },
    onError: (error) => {
      setProgress(null);
      setErrors(serverError(error));
    },
  });

  function pickAudio(file: File | null) {
    setAudio(file);
    setErrors((e) => ({ ...e, audio: checkAudio(file) }));
  }

  function pickCover(file: File | null) {
    setCover(file);
    setErrors((e) => ({ ...e, cover: checkCover(file) }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = { audio: audio ? checkAudio(audio) : "Elige un archivo MP3.", cover: checkCover(cover) };
    setErrors(found);
    if (!found.audio && !found.cover) send.mutate();
  }

  return (
    <>
      <h1 className="page-title">Subir pista</h1>
      <form className="stack-form" onSubmit={submit}>
        <label>Título<input required maxLength={300} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label>Género<input required maxLength={60} value={genre} onChange={(e) => setGenre(e.target.value)} /></label>
        <label>Licencia<input required maxLength={120} placeholder="CC BY 4.0" value={license} onChange={(e) => setLicense(e.target.value)} /></label>
        <label>
          Álbum o EP (opcional)
          <select value={albumId} onChange={(e) => setAlbumId(e.target.value)}>
            <option value="">Sin álbum</option>
            {albums.data?.map((album) => <option key={album.id} value={album.id}>{album.title}</option>)}
          </select>
        </label>
        <FileDrop
          label="Archivo MP3"
          prompt="Arrastra tu MP3 aquí"
          hint={`Hasta ${MP3_MB} MB y 10 minutos`}
          accept=".mp3,audio/mpeg"
          file={audio}
          onPick={pickAudio}
          invalid={!!errors.audio}
          describedBy={errors.audio ? "audio-error" : undefined}
        />
        {errors.audio && <span id="audio-error" className="form-error">{errors.audio}</span>}
        <FileDrop
          label="Portada (opcional)"
          prompt="Arrastra tu portada aquí"
          hint={`JPG o PNG, hasta ${COVER_MB} MB`}
          accept="image/jpeg,image/png"
          file={cover}
          onPick={pickCover}
          invalid={!!errors.cover}
          describedBy={errors.cover ? "cover-error" : undefined}
        />
        {errors.cover && <span id="cover-error" className="form-error">{errors.cover}</span>}
        <label>
          Programar publicación (opcional)
          <input type="datetime-local" value={publishAt} onChange={(e) => setPublishAt(e.target.value)} />
        </label>
        <small>Sin fecha, la pista queda en borrador hasta que la publiques.</small>
        {errors.form && <p className="form-error" role="alert">{errors.form}</p>}
        {progress !== null && (
          <div className="upload-progress">
            <progress aria-label="Subiendo" value={progress} max={1} />
            <span>{Math.round(progress * 100)} %</span>
          </div>
        )}
        <button className="primary" type="submit" disabled={send.isPending}>Subir pista</button>
      </form>
    </>
  );
}
