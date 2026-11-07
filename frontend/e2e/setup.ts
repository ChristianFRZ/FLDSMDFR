import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { request } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const API = "http://localhost:8080";
const PASSWORD = "contrasena-e2e";

export const statePath = join(here, ".state.json");
export type State = {
  admin: { email: string; password: string };
  composer: { email: string; password: string };
  listener: { email: string; password: string };
  songTitle: string;
  tapeId: string;
};

function adminFromEnv() {
  const lines = readFileSync(join(here, "../../.env"), "utf8").split("\n");
  const read = (key: string) => lines.find((line) => line.startsWith(`${key}=`))?.slice(key.length + 1).trim() ?? "";
  return { email: read("ADMIN_EMAIL"), password: read("ADMIN_PASSWORD") };
}

/** Crea por la API una pista local y un casete, para no depender de lo que haya en la base. */
export default async function setup() {
  const http = await request.newContext({ baseURL: API });
  const tag = Date.now().toString(36);
  const bearer = (token: string) => ({ authorization: `Bearer ${token}` });
  async function ok<T>(response: Awaited<ReturnType<typeof http.post>>): Promise<T> {
    if (!response.ok()) throw new Error(`${response.url()} → ${response.status()}: ${await response.text()}`);
    return (await response.json()) as T;
  }
  type Tokens = { access_token: string };
  const login = (email: string, password: string) =>
    http.post("/api/auth/login", { data: { email, password } }).then((r) => ok<Tokens>(r));
  const register = async (name: string) => {
    const email = `${name}-${tag}@meloxo.dev`;
    await http.post("/api/auth/register", { data: { email, password: PASSWORD, display_name: name } }).then((r) => ok(r));
    return { email, password: PASSWORD };
  };

  const admin = adminFromEnv();
  const adminToken = (await login(admin.email, admin.password)).access_token;
  const composer = await register("compositor");
  const listener = await register("oyente");

  const asked = await ok<{ id: string }>(
    await http.post("/api/composer-requests", {
      headers: bearer((await login(composer.email, PASSWORD)).access_token),
      data: { message: "e2e" },
    }),
  );
  await http
    .post(`/api/admin/composer-requests/${asked.id}/approve`, { headers: bearer(adminToken), data: {} })
    .then((r) => ok(r));

  const composerToken = (await login(composer.email, PASSWORD)).access_token;
  const songTitle = `Tono ${tag}`;
  const track = await ok<{ id: string }>(
    await http.post("/api/composer/tracks", {
      headers: bearer(composerToken),
      multipart: {
        title: songTitle,
        genre: "rock",
        license: "CC BY 4.0",
        audio: { name: "tone.mp3", mimeType: "audio/mpeg", buffer: readFileSync(join(here, "fixtures/tone.mp3")) },
      },
    }),
  );
  await http.post(`/api/composer/tracks/${track.id}/publish`, { headers: bearer(composerToken) }).then((r) => ok(r));

  const listenerToken = (await login(listener.email, PASSWORD)).access_token;
  const tape = await ok<{ id: string }>(
    await http.post("/api/tapes", { headers: bearer(listenerToken), data: { title: "Casete e2e", color: "teal" } }),
  );
  await http
    .post(`/api/tapes/${tape.id}/tracks`, {
      headers: bearer(listenerToken),
      data: { song_id: track.id, dedication: "Para probar", side: "A" },
    })
    .then((r) => ok(r));

  const state: State = { admin, composer, listener, songTitle, tapeId: tape.id };
  writeFileSync(statePath, JSON.stringify(state));
  await http.dispose();
}
