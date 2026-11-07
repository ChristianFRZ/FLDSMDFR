import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, ApiError, upload } from "../../api/client";

type Album = { id: string; title: string; kind: string };

export function Albums() {
  const client = useQueryClient();
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("album");
  const albums = useQuery({ queryKey: ["composer-albums"], queryFn: () => api<Album[]>("/api/composer/albums") });
  const create = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("title", title);
      form.set("kind", kind);
      return upload("/api/composer/albums", form);
    },
    onSuccess: () => {
      setTitle("");
      void client.invalidateQueries({ queryKey: ["composer-albums"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <>
      <h1 className="page-title">Álbumes y EP</h1>
      <form className="stack-form" onSubmit={submit}>
        <label>Título<input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label>
          Tipo
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="album">Álbum</option>
            <option value="ep">EP</option>
          </select>
        </label>
        {create.error instanceof ApiError && <p className="form-error" role="alert">{create.error.message}</p>}
        <button className="primary" type="submit" disabled={create.isPending}>Crear</button>
      </form>
      {albums.isSuccess && !albums.data.length && <p className="muted">Aún no tienes álbumes.</p>}
      <ul className="link-list plain-list">
        {albums.data?.map((album) => <li key={album.id}>{album.title} <small>{album.kind === "ep" ? "EP" : "Álbum"}</small></li>)}
      </ul>
    </>
  );
}
