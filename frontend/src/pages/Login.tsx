import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AuthForm } from "./AuthForm";

/** Solo rutas internas: un `next` a otro dominio sería una redirección abierta. */
export function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function Login() {
  const { user, login } = useAuth();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const next = safeNext(params.get("next"));

  if (user) return <Navigate to={next} replace />;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No pudimos entrar. Intenta de nuevo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthForm
      title="Entrar"
      dedication="te guardé un lado A"
      error={error}
      busy={busy}
      action="Entrar"
      onSubmit={() => void submit()}
      footer={<>¿Primera vez? <Link to={`/register?next=${encodeURIComponent(next)}`}>Crea tu cuenta</Link></>}
    >
      <label>
        Correo
        <input type="text" inputMode="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Contraseña
        <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
    </AuthForm>
  );
}
