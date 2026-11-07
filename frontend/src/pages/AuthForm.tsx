import type { FormEvent, ReactNode } from "react";
import logo from "../assets/meloxo-stacked-color-dark.svg";
import { Note } from "../components/Note";

type Props = {
  title: string;
  dedication: string;
  error: string | null;
  busy: boolean;
  action: string;
  onSubmit: () => void;
  children: ReactNode;
  footer: ReactNode;
};

export function AuthForm({ title, dedication, error, busy, action, onSubmit, children, footer }: Props) {
  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }
  return (
    <main className="auth">
      <div className="auth-brand">
        <img src={logo} alt="MELOXO" />
        <Note tape className="auth-note">{dedication}</Note>
      </div>
      <form className="panel auth-form" onSubmit={submit}>
        <h1>{title}</h1>
        {children}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>{busy ? "Un momento…" : action}</button>
        <p className="auth-footer">{footer}</p>
      </form>
    </main>
  );
}
