import { ApiError } from "../api/client";

export type Recovery =
  | { action: "resume"; src: string; position: number }
  | { action: "skip"; notice: string }
  | { action: "stop"; notice: string };

type Input = {
  songId: string;
  position: number;
  requestTicket: (songId: string) => Promise<string>;
  probe: (src: string) => Promise<number>;
};

export const streamUrl = (songId: string, ticket: string) =>
  `/api/songs/${songId}/stream?ticket=${encodeURIComponent(ticket)}`;

/**
 * El elemento <audio> no dice por qué falló. Un ticket nuevo y una petición de un byte separan los tres casos: permiso
 * vencido (se retoma), fuente caída (se pasa a la siguiente) y red caída (se detiene, para no saltarse toda la cola).
 */
export async function recoverStream({ songId, position, requestTicket, probe }: Input): Promise<Recovery> {
  let src: string;
  try {
    src = streamUrl(songId, await requestTicket(songId));
  } catch (error) {
    if (error instanceof ApiError && error.status === 0) {
      return { action: "stop", notice: "Se perdió la conexión. Dale a reproducir cuando vuelva." };
    }
    return { action: "skip", notice: "Esta pista ya no está disponible. Pasamos a la siguiente." };
  }
  const status = await probe(src).catch(() => 0);
  if (status === 200 || status === 206) return { action: "resume", src, position };
  if (status === 0) return { action: "stop", notice: "Se perdió la conexión. Dale a reproducir cuando vuelva." };
  if (status === 503) return { action: "skip", notice: "Jamendo no responde. Pasamos a la siguiente." };
  return { action: "skip", notice: "No pudimos reproducir esta pista. Pasamos a la siguiente." };
}
