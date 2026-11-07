import { type DragEvent, useEffect, useId, useRef, useState } from "react";
import { clock } from "../player/format";

type Props = {
  label: string;
  prompt: string;
  hint?: string;
  accept: string;
  file: File | null;
  onPick: (file: File | null) => void;
  disabled?: boolean;
  invalid?: boolean;
  describedBy?: string;
};

const KB = 1024;
const MB = KB * KB;
const decimal = (value: number) => value.toLocaleString("es-MX", { maximumFractionDigits: 1 });
const size = (bytes: number) => (bytes < MB ? `${decimal(bytes / KB)} KB` : `${decimal(bytes / MB)} MB`);

/** Duración leída del propio archivo. Si el navegador no puede leerla, solo se muestra el tamaño. */
function useDuration(file: File | null) {
  const [seconds, setSeconds] = useState<number | null>(null);
  useEffect(() => {
    setSeconds(null);
    if (!file?.type.startsWith("audio/") || !URL.createObjectURL) return;
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      if (Number.isFinite(audio.duration)) setSeconds(audio.duration);
    };
    audio.src = url;
    return () => {
      audio.onloadedmetadata = null;
      URL.revokeObjectURL(url);
    };
  }, [file]);
  return seconds;
}

/** Zona de arrastre sobre un `input` real: el teclado, los lectores de pantalla y el diálogo del sistema siguen igual. */
export function FileDrop({ label, prompt, hint, accept, file, onPick, disabled, invalid, describedBy }: Props) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const seconds = useDuration(file);

  function drop(event: DragEvent) {
    event.preventDefault();
    setOver(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped && !disabled) onPick(dropped);
  }

  function remove() {
    if (input.current) input.current.value = "";
    onPick(null);
    input.current?.focus();
  }

  const state = [over && "over", file && "filled", invalid && "invalid", disabled && "disabled"].filter(Boolean).join(" ");

  return (
    <div
      className="file-field"
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={drop}
    >
      <span>{label}</span>
      <input
        ref={input}
        id={id}
        className="file-input"
        type="file"
        accept={accept}
        aria-label={label}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        disabled={disabled}
        onChange={(event) => onPick(event.target.files?.[0] ?? null)}
      />
      {file ? (
        <div className={`file-drop ${state}`}>
          <span className="file-note" aria-hidden="true">♪</span>
          <div className="file-info">
            <b>{file.name}</b>
            <small>{size(file.size)}{seconds !== null && ` · ${clock(seconds)}`}</small>
          </div>
          <button className="file-remove" type="button" aria-label={`Quitar ${file.name}`} disabled={disabled} onClick={remove}>
            Quitar
          </button>
        </div>
      ) : (
        <label className={`file-drop ${state}`} htmlFor={id}>
          <span className="file-note" aria-hidden="true">♪</span>
          <b>{prompt}</b>
          <span className="primary">Elegir archivo</span>
          {hint && <small>{hint}</small>}
        </label>
      )}
    </div>
  );
}
