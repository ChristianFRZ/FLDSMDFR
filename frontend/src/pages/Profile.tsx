import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { type ThemePref, useTheme } from "../theme";
import { ComposerRequest } from "./composer/Request";

const appearances: { value: ThemePref; label: string }[] = [
  { value: "system", label: "Sistema" },
  { value: "dark", label: "Oscuro" },
  { value: "light", label: "Claro" },
];

export function Profile() {
  const { user, logout } = useAuth();
  const { pref, setPref } = useTheme();
  const [name, setName] = useState(user?.display_name ?? "");
  const save = useMutation({
    mutationFn: () => api("/api/users/me", { method: "PATCH", json: { display_name: name } }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <>
      <h1 className="page-title">Tu perfil</h1>
      <p className="muted">{user?.email}</p>
      <form className="stack-form" onSubmit={submit}>
        <label>
          Tu nombre
          <input required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        {save.isSuccess && <p className="muted" role="status">Nombre guardado.</p>}
        {save.error instanceof ApiError && <p className="form-error" role="alert">{save.error.message}</p>}
        <button className="ghost" type="submit" disabled={save.isPending}>Guardar nombre</button>
      </form>
      <fieldset className="appearance">
        <legend id="appearance-label">Apariencia</legend>
        <div role="radiogroup" aria-labelledby="appearance-label">
          {appearances.map((option) => (
            <label key={option.value}>
              <input type="radio" name="appearance" value={option.value} checked={pref === option.value} onChange={() => setPref(option.value)} />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>
      {user?.role === "listener" && <ComposerRequest />}
      <button className="ghost" type="button" onClick={() => void logout()}>Cerrar sesión</button>
    </>
  );
}
