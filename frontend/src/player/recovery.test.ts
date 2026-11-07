import { describe, expect, test, vi } from "vitest";
import { ApiError } from "../api/client";
import { recoverStream } from "./recovery";

const base = { songId: "s1", position: 72 };

describe("recuperar el audio", () => {
  test("un error de audio por ticket vencido pide uno nuevo y retoma en la misma posición", async () => {
    const requestTicket = vi.fn().mockResolvedValue("nuevo");
    const probe = vi.fn().mockResolvedValue(206);
    const result = await recoverStream({ ...base, requestTicket, probe });
    expect(requestTicket).toHaveBeenCalledWith("s1");
    expect(result).toEqual({ action: "resume", src: "/api/songs/s1/stream?ticket=nuevo", position: 72 });
  });

  test("503 de Jamendo muestra aviso y pasa a la siguiente", async () => {
    const result = await recoverStream({
      ...base,
      requestTicket: vi.fn().mockResolvedValue("t"),
      probe: vi.fn().mockResolvedValue(503),
    });
    expect(result.action).toBe("skip");
    expect(result).toHaveProperty("notice", expect.stringContaining("Jamendo"));
  });

  test("una pista retirada pasa a la siguiente", async () => {
    const result = await recoverStream({
      ...base,
      requestTicket: vi.fn().mockRejectedValue(new ApiError(404, "song_not_found", "x")),
      probe: vi.fn(),
    });
    expect(result.action).toBe("skip");
  });

  test("sin red se detiene en vez de saltarse toda la cola", async () => {
    const result = await recoverStream({
      ...base,
      requestTicket: vi.fn().mockRejectedValue(new ApiError(0, "network_error", "x")),
      probe: vi.fn(),
    });
    expect(result.action).toBe("stop");
  });

  test("un archivo que responde otro error pasa a la siguiente", async () => {
    const result = await recoverStream({
      ...base,
      requestTicket: vi.fn().mockResolvedValue("t"),
      probe: vi.fn().mockResolvedValue(500),
    });
    expect(result.action).toBe("skip");
  });
});
