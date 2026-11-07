import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Page } from "../../api/types";
import { Pager, query } from "./shared";

type AdminUser = { id: string; email: string; display_name: string; role: string; status: string };

const roles = [
  { value: "listener", label: "Oyente" },
  { value: "composer", label: "Compositor" },
  { value: "admin", label: "Administrador" },
];

function Row({ user, onError }: { user: AdminUser; onError: (message: string | null) => void }) {
  const client = useQueryClient();
  const [asking, setAsking] = useState(false);
  const change = useMutation({
    mutationFn: ({ path, json }: { path: string; json?: object }) =>
      api(`/api/admin/users/${user.id}/${path}`, { method: "POST", json }),
    onMutate: () => onError(null),
    onError: (error) => onError(error instanceof ApiError ? error.message : "No se pudo. Intenta de nuevo."),
    onSettled: () => {
      setAsking(false);
      void client.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
  const suspended = user.status === "suspended";
  return (
    <tr>
      <td>{user.display_name}</td>
      <td>{user.email}</td>
      <td>
        <select
          aria-label={`Rol de ${user.display_name}`}
          value={user.role}
          disabled={change.isPending}
          onChange={(event) => change.mutate({ path: "role", json: { role: event.target.value } })}
        >
          {roles.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
        </select>
      </td>
      <td>{suspended ? "Suspendida" : "Activa"}</td>
      <td className="cell-actions">
        {suspended && (
          <button className="ghost" type="button" onClick={() => change.mutate({ path: "reactivate" })}>Reactivar</button>
        )}
        {!suspended && !asking && (
          <button className="ghost" type="button" aria-label={`Suspender a ${user.display_name}`} onClick={() => setAsking(true)}>
            Suspender
          </button>
        )}
        {!suspended && asking && (
          <>
            <button className="ghost danger" type="button" onClick={() => change.mutate({ path: "suspend", json: {} })}>
              Confirmar suspensión
            </button>
            <button className="ghost" type="button" onClick={() => setAsking(false)}>Cancelar</button>
          </>
        )}
      </td>
    </tr>
  );
}

export function Users() {
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [problem, setProblem] = useState<string | null>(null);
  const users = useQuery({
    queryKey: ["admin-users", q, role, status, page],
    queryFn: () => api<Page<AdminUser>>(`/api/admin/users?${query({ q, role, status, page })}`),
    placeholderData: keepPreviousData,
  });

  function search(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setQ(text);
  }

  return (
    <>
      <form className="filters" onSubmit={search}>
        <label>Buscar<input type="search" value={text} onChange={(e) => setText(e.target.value)} /></label>
        <label>
          Rol
          <select value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }}>
            <option value="">Todos</option>
            {roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </label>
        <label>
          Estado
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="">Todos</option>
            <option value="active">Activa</option>
            <option value="suspended">Suspendida</option>
          </select>
        </label>
      </form>
      {problem && <p className="form-error" role="alert">{problem}</p>}
      {users.isError && <p className="form-error" role="alert">No se pudo cargar la lista de usuarios.</p>}
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th scope="col">Nombre</th><th scope="col">Correo</th><th scope="col">Rol</th><th scope="col">Estado</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead>
          <tbody>{users.data?.items.map((user) => <Row key={user.id} user={user} onError={setProblem} />)}</tbody>
        </table>
      </div>
      {users.isSuccess && !users.data.items.length && <p className="muted">Nadie coincide con esa búsqueda.</p>}
      {users.data && <Pager page={users.data.page} size={users.data.size} total={users.data.total} onPage={setPage} />}
    </>
  );
}
