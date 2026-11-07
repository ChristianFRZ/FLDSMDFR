import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AuthForm } from "./AuthForm";
import { safeNext } from "./Login";

export function Register() {
  const { user, register } = useAuth();
  const [params] = useSearchParams();
  const [name, setName] = useState("");
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
      await register(email, password, name);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No pudimos crear tu cuenta. Intenta de nuevo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthForm
      title="Crea tu cuenta"
      dedication="la música se comparte en pequeño"
      error={error}
      busy={busy}
      action="Crear cuenta"
      onSubmit={() => void submit()}
      footer={<>¿Ya tienes cuenta? <Link to={`/login?next=${encodeURIComponent(next)}`}>Entra</Link></>}
    >
      <label>
        Tu nombre
        <input type="text" autoComplete="name" required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label>
        Correo
        <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Contraseña
        <input type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} />
        <small>Al menos 8 caracteres.</small>
      </label>
    </AuthForm>
  );
}
