import { describe, expect, test } from "vitest";
import { createQueue, currentItem, next, prev, setShuffle, upcoming, jumpTo } from "./queue";

const items = ["a", "b", "c", "d"];
const noShuffle = { shuffle: false, repeat: "off" as const };

describe("cola", () => {
  test("arranca en la pista pedida", () => {
    expect(currentItem(createQueue(items, 2, noShuffle))).toBe("c");
  });

  test("siguiente avanza en orden y termina sin repetir", () => {
    let q = createQueue(items, 2, noShuffle);
    let step = next(q, true);
    expect(currentItem(step.queue)).toBe("d");
    q = step.queue;
    step = next(q, true);
    expect(step.ended).toBe(true);
  });

  test("aleatorio no repite hasta agotar la cola", () => {
    let q = createQueue(items, 1, { shuffle: true, repeat: "off" });
    const seen = [currentItem(q)];
    for (let i = 0; i < 3; i++) {
      q = next(q, true).queue;
      seen.push(currentItem(q));
    }
    expect(seen[0]).toBe("b");
    expect([...seen].sort()).toEqual(items);
    expect(next(q, true).ended).toBe(true);
  });

  test("aleatorio con repeat all baraja de nuevo al agotarse", () => {
    let q = createQueue(items, 0, { shuffle: true, repeat: "all" });
    for (let i = 0; i < 3; i++) q = next(q, true).queue;
    const step = next(q, true);
    expect(step.ended).toBe(false);
    expect(items).toContain(currentItem(step.queue));
  });

  test("repeat one reinicia la pista al terminar", () => {
    const q = createQueue(items, 1, { shuffle: false, repeat: "one" });
    const step = next(q, true);
    expect(step.restart).toBe(true);
    expect(currentItem(step.queue)).toBe("b");
  });

  test("repeat one avanza si la persona pide siguiente", () => {
    const q = createQueue(items, 1, { shuffle: false, repeat: "one" });
    expect(currentItem(next(q, false).queue)).toBe("c");
  });

  test("repeat all vuelve al inicio", () => {
    const q = createQueue(items, 3, { shuffle: false, repeat: "all" });
    expect(currentItem(next(q, true).queue)).toBe("a");
  });

  test("anterior reinicia si van más de 3 s", () => {
    const q = createQueue(items, 2, noShuffle);
    const step = prev(q, 3.5);
    expect(step.restart).toBe(true);
    expect(currentItem(step.queue)).toBe("c");
  });

  test("anterior retrocede si van menos de 3 s", () => {
    expect(currentItem(prev(createQueue(items, 2, noShuffle), 1).queue)).toBe("b");
  });

  test("anterior en la primera pista la reinicia", () => {
    expect(prev(createQueue(items, 0, noShuffle), 1).restart).toBe(true);
  });

  test("activar aleatorio conserva la pista actual", () => {
    const q = setShuffle(createQueue(items, 2, noShuffle), true);
    expect(currentItem(q)).toBe("c");
    expect(upcoming(q)).toHaveLength(3);
  });

  test("quitar aleatorio sigue en orden desde la pista actual", () => {
    const q = setShuffle(createQueue(items, 1, { shuffle: true, repeat: "off" }), false);
    expect(upcoming(q)).toEqual(["c", "d"]);
  });

  test("saltar a una pista de la cola", () => {
    const q = createQueue(items, 0, noShuffle);
    expect(currentItem(jumpTo(q, 1))).toBe("c");
  });

  test("una cola vacía no tiene pista actual", () => {
    expect(currentItem(createQueue([], 0, noShuffle))).toBeUndefined();
  });
});
