import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { TapeSummary } from "../api/types";
import { DURATIONS, useDone } from "../components/motion";
import { Tape, type TapeColor } from "../components/Tape";
import { TAPE_COLORS, tapeHex } from "../components/tapeColors";

/**
 * El casete recién creado cae desde arriba y rebota; al terminar (o con un clic o cualquier tecla) se va a su
 * página. Con menos movimiento navega en el siguiente tick.
 */
function TapeDrop({ tape }: { tape: TapeSummary }) {
  const navigate = useNavigate();
  const done = useRef(false);
  const finish = useCallback(() => {
    if (done.current) return;
    done.current = true;
    navigate(`/tapes/${tape.id}`, { replace: true });
  }, [navigate, tape.id]);

  useDone(DURATIONS.drop, finish);

  useEffect(() => {
    window.addEventListener("keydown", finish);
    return () => window.removeEventListener("keydown", finish);
  }, [finish]);

  return (
    <div role="status" aria-label="Casete creado" className="tape-drop-overlay" onClick={finish}>
      <Tape title={tape.title} color={tape.color} className="tape-drop" />
    </div>
  );
}

export function TapeCreate() {
  const client = useQueryClient();
  const [title, setTitle] = useState("");
  const [color, setColor] = useState<TapeColor>(TAPE_COLORS[0].value);
  const [created, setCreated] = useState<TapeSummary | null>(null);
  const formArea = useRef<HTMLDivElement>(null);
  const create = useMutation({
    mutationFn: () => api<TapeSummary>("/api/tapes", { method: "POST", json: { title, color } }),
    onSuccess: (tape) => {
      void client.invalidateQueries({ queryKey: ["tapes"] });
      setCreated(tape);
    },
  });

  // Con el casete cayendo, el formulario de debajo no recibe foco ni clics (React 18 no conoce `inert` como prop).
  useEffect(() => {
    formArea.current?.toggleAttribute("inert", created !== null);
  }, [created]);

  function submit(event: FormEvent) {
    event.preventDefault();
    // Enter para saltar la animación también envía el formulario: sin esta guarda se crearía otro casete.
    if (created || create.isPending) return;
    create.mutate();
  }

  return (
    <>
      <h1 className="page-title">Crear casete</h1>
      <div className="tape-create" ref={formArea}>
        <Tape title={title || "Tu casete"} color={color} tilt={-3} />
        <form className="stack-form" onSubmit={submit}>
          <label>
            Nombre
            <input required maxLength={80} value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <fieldset>
            <legend>Color: {TAPE_COLORS.find((item) => item.value === color)?.label ?? color.toUpperCase()}</legend>
            <div className="color-shelf">
              {TAPE_COLORS.map((item) => (
                <label key={item.value} title={item.label}>
                  <input
                    type="radio"
                    name="color"
                    aria-label={item.label}
                    checked={color === item.value}
                    onChange={() => setColor(item.value)}
                  />
                  <Tape title="" color={item.value} className="tape-mini" />
                </label>
              ))}
            </div>
            <label className="color-free">
              <input type="color" value={tapeHex(color)} onChange={(e) => setColor(e.target.value)} />
              Color libre
            </label>
          </fieldset>
          {create.error instanceof ApiError && <p className="form-error" role="alert">{create.error.message}</p>}
          <button className="primary" type="submit" disabled={create.isPending}>Crear casete</button>
        </form>
      </div>
      {created && <TapeDrop tape={created} />}
    </>
  );
}
