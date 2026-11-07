import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { TapeSummary } from "../api/types";
import { Tape, type TapeColor } from "../components/Tape";
import { TAPE_COLORS, tapeHex } from "../components/tapeColors";

export function TapeCreate() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const [title, setTitle] = useState("");
  const [color, setColor] = useState<TapeColor>(TAPE_COLORS[0].value);
  const create = useMutation({
    mutationFn: () => api<TapeSummary>("/api/tapes", { method: "POST", json: { title, color } }),
    onSuccess: (tape) => {
      void client.invalidateQueries({ queryKey: ["tapes"] });
      navigate(`/tapes/${tape.id}`, { replace: true });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <>
      <h1 className="page-title">Crear casete</h1>
      <div className="tape-create">
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
    </>
  );
}
