import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { RequireAuth } from "../auth/RequireAuth";
import { renderApp } from "../test-utils";
import { TapeInvite } from "./TapeInvite";

vi.mock("../api/client", async (original) => ({
  ...(await original<typeof import("../api/client")>()),
  api: vi.fn(),
}));
vi.mock("../auth/AuthContext", () => ({ useAuth: vi.fn() }));

function Where() {
  const location = useLocation();
  return <p>En {location.pathname + location.search}</p>;
}

const app = (
  <Routes>
    <Route element={<RequireAuth />}>
      <Route path="/invite/:token" element={<TapeInvite />} />
      <Route path="/tapes/:id" element={<Where />} />
      <Route path="/" element={<Where />} />
    </Route>
    <Route path="/login" element={<Where />} />
  </Routes>
);

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(useAuth).mockReturnValue({ user: { id: "u1" }, loading: false } as ReturnType<typeof useAuth>);
});

test("invitación sin sesión lleva a entrar y vuelve al enlace", async () => {
  vi.mocked(useAuth).mockReturnValue({ user: null, loading: false } as ReturnType<typeof useAuth>);
  renderApp(app, "/invite/abc");
  expect(await screen.findByText("En /login?next=%2Finvite%2Fabc")).toBeInTheDocument();
});

test("muestra solo el nombre del casete y quién invita", async () => {
  vi.mocked(api).mockResolvedValue({ title: "Noches de patio", color: "pink", inviter: "Leo", already_member: false, tape_id: null });
  renderApp(app, "/invite/abc");
  expect(await screen.findByText(/Leo te invitó a «Noches de patio»/)).toBeInTheDocument();
});

test("unirse lleva al casete", async () => {
  vi.mocked(api).mockImplementation((async (path: string) =>
    path.startsWith("/api/tapes/join/")
      ? { tape_id: "t9", joined: true }
      : { title: "Patio", color: "pink", inviter: "Leo", already_member: false, tape_id: null }) as typeof api);
  renderApp(app, "/invite/abc");
  await userEvent.click(await screen.findByRole("button", { name: "Unirme al casete" }));
  expect(await screen.findByText("En /tapes/t9")).toBeInTheDocument();
});

test("quien ya es miembro va directo al casete", async () => {
  vi.mocked(api).mockResolvedValue({ title: "Patio", color: "pink", inviter: "Leo", already_member: true, tape_id: "t9" });
  renderApp(app, "/invite/abc");
  expect(await screen.findByText("En /tapes/t9")).toBeInTheDocument();
});

test("enlace vencido explica qué pasó", async () => {
  vi.mocked(api).mockRejectedValue(new ApiError(410, "invite_expired", "Este enlace ya caducó"));
  renderApp(app, "/invite/abc");
  expect(await screen.findByRole("alert")).toHaveTextContent("Este enlace ya caducó");
  expect(screen.getByRole("link", { name: "Volver a Inicio" })).toBeInTheDocument();
});

test("si el casete se llena al unirse, lo explica", async () => {
  vi.mocked(api).mockImplementation((async (path: string) => {
    if (path.startsWith("/api/tapes/join/")) throw new ApiError(409, "tape_full_members", "Este casete ya tiene todos sus miembros");
    return { title: "Patio", color: "pink", inviter: "Leo", already_member: false, tape_id: null };
  }) as typeof api);
  renderApp(app, "/invite/abc");
  await userEvent.click(await screen.findByRole("button", { name: "Unirme al casete" }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("todos sus miembros"));
});
