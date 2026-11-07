import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import { api, ApiError, upload } from "../../api/client";
import type { Artist } from "../../api/types";
import { LINK_FIELDS } from "../../components/ArtistLinks";
import { FileDrop } from "../../components/FileDrop";

const KEY = ["composer-profile"];

function Photo({ url, name }: { url: string | null; name: string }) {
  const client = useQueryClient();
  const send = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.set("photo", file);
      return upload<Artist>("/api/composer/profile/photo", form);
    },
    onSuccess: () => void client.invalidateQueries({ queryKey: KEY }),
  });

  return (
    <div className="stack-form">
      {url && <img className="artist-photo" src={url} alt={`Foto de ${name}`} />}
      <FileDrop
        label="Foto"
        prompt="Arrastra tu foto aquí"
        hint="JPG o PNG"
        accept="image/jpeg,image/png"
        file={null}
        onPick={(file) => file && send.mutate(file)}
        disabled={send.isPending}
      />
      {send.isSuccess && <p className="muted" role="status">Foto guardada.</p>}
      {send.isError && (
        <p className="form-error" role="alert">
          {send.error instanceof ApiError ? send.error.message : "No se pudo subir la foto. Intenta de nuevo."}
        </p>
      )}
    </div>
  );
}

export function ComposerProfile() {
  const client = useQueryClient();
  const profile = useQuery({ queryKey: KEY, queryFn: () => api<Artist>("/api/composer/profile") });
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [links, setLinks] = useState<Record<string, string>>({});

  useEffect(() => {
    if (profile.data) {
      setName(profile.data.name);
      setBio(profile.data.bio ?? "");
      setLinks(profile.data.links ?? {});
    }
  }, [profile.data]);

  const save = useMutation({
    mutationFn: () => {
      const filled = Object.entries(links).filter(([, url]) => url.trim());
      return api("/api/composer/profile", { method: "PUT", json: { name, bio, links: Object.fromEntries(filled) } });
    },
    onSuccess: () => void client.invalidateQueries({ queryKey: KEY }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <>
      <h1 className="page-title">Perfil de artista</h1>
      {profile.data && <Photo url={profile.data.photo_url} name={profile.data.name} />}
      <form className="stack-form" onSubmit={submit}>
        <label>Nombre artístico<input required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label>Biografía<textarea rows={5} maxLength={2000} value={bio} onChange={(e) => setBio(e.target.value)} /></label>
        {LINK_FIELDS.map(({ key, label }) => (
          <label key={key}>
            {label}
            <input
              type="url"
              placeholder="https://"
              value={links[key] ?? ""}
              onChange={(e) => setLinks({ ...links, [key]: e.target.value })}
            />
          </label>
        ))}
        {save.isSuccess && <p className="muted" role="status">Perfil guardado.</p>}
        {save.error instanceof ApiError && <p className="form-error" role="alert">{save.error.message}</p>}
        <button className="primary" type="submit" disabled={save.isPending}>Guardar</button>
      </form>
    </>
  );
}
