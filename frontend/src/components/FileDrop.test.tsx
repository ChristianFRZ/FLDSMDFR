import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, test, vi } from "vitest";
import { FileDrop } from "./FileDrop";

const mp3 = new File([new Uint8Array(1024 * 1024)], "mi-rola.mp3", { type: "audio/mpeg" });

function Controlled({ onPick }: { onPick?: (file: File | null) => void }) {
  const [file, setFile] = useState<File | null>(null);
  return (
    <FileDrop
      label="Archivo MP3"
      prompt="Arrastra tu MP3 aquí"
      hint="Hasta 15 MB"
      accept=".mp3"
      file={file}
      onPick={(next) => {
        setFile(next);
        onPick?.(next);
      }}
    />
  );
}

test("sin archivo invita a arrastrar o elegir", () => {
  render(<Controlled />);
  expect(screen.getByText("Arrastra tu MP3 aquí")).toBeInTheDocument();
  expect(screen.getByText("Elegir archivo")).toBeInTheDocument();
  expect(screen.getByText("Hasta 15 MB")).toBeInTheDocument();
});

test("al elegir un archivo muestra su nombre y tamaño", async () => {
  render(<Controlled />);
  await userEvent.upload(screen.getByLabelText("Archivo MP3"), mp3);
  expect(screen.getByText("mi-rola.mp3")).toBeInTheDocument();
  expect(screen.getByText(/1 MB/)).toBeInTheDocument();
  expect(screen.queryByText("Arrastra tu MP3 aquí")).not.toBeInTheDocument();
});

test("acepta un archivo soltado sobre la zona", () => {
  const onPick = vi.fn();
  render(<Controlled onPick={onPick} />);
  fireEvent.drop(screen.getByText("Arrastra tu MP3 aquí"), { dataTransfer: { files: [mp3] } });
  expect(onPick).toHaveBeenCalledWith(mp3);
});

test("Quitar vacía la zona y devuelve el foco al control", async () => {
  const onPick = vi.fn();
  render(<Controlled onPick={onPick} />);
  await userEvent.upload(screen.getByLabelText("Archivo MP3"), mp3);
  await userEvent.click(screen.getByRole("button", { name: "Quitar mi-rola.mp3" }));
  expect(onPick).toHaveBeenLastCalledWith(null);
  expect(screen.getByText("Arrastra tu MP3 aquí")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByLabelText("Archivo MP3")).toHaveFocus());
});
