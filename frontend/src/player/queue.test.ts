import { describe, expect, test } from "vitest";
import {
  createQueue,
  currentItem,
  enqueueLast,
  enqueueNext,
  jumpTo,
  moveUpcoming,
  next,
  prev,
  removeUpcoming,
  setShuffle,
  upcoming,
} from "./queue";

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

describe("cola editable", () => {
  test("reproducir siguiente la pone justo después de la actual", () => {
    const q = enqueueNext(createQueue(items, 1, noShuffle), "x");
    expect(currentItem(q)).toBe("b");
    expect(upcoming(q)).toEqual(["x", "c", "d"]);
  });

  test("dos pedidos de siguiente: el último queda primero", () => {
    const q = enqueueNext(enqueueNext(createQueue(items, 0, noShuffle), "x"), "y");
    expect(upcoming(q)).toEqual(["y", "x", "b", "c", "d"]);
  });

  test("agregar a la cola la pone al final de lo que sigue", () => {
    const q = enqueueLast(createQueue(items, 1, noShuffle), "x");
    expect(currentItem(q)).toBe("b");
    expect(upcoming(q)).toEqual(["c", "d", "x"]);
  });

  test("lo agregado suena cuando llega su turno", () => {
    let q = enqueueNext(createQueue(items, 3, noShuffle), "x");
    q = next(q, true).queue;
    expect(currentItem(q)).toBe("x");
  });

  test("agregar en modo aleatorio no cambia la pista actual", () => {
    const q = enqueueLast(createQueue(items, 2, { shuffle: true, repeat: "off" }), "x");
    expect(currentItem(q)).toBe("c");
    expect(upcoming(q)).toHaveLength(4);
    expect(upcoming(q)).toContain("x");
  });

  test("quitar una pista de lo que sigue", () => {
    const q = removeUpcoming(createQueue(items, 0, noShuffle), 1);
    expect(currentItem(q)).toBe("a");
    expect(upcoming(q)).toEqual(["b", "d"]);
  });

  test("una pista quitada no vuelve cuando la cola da la vuelta", () => {
    let q = removeUpcoming(createQueue(items, 0, { shuffle: true, repeat: "all" }), 0);
    const removed = items.filter((item) => item !== currentItem(q) && !upcoming(q).includes(item))[0];
    for (let i = 0; i < upcoming(q).length + 1; i++) q = next(q, true).queue;
    const seen = new Set<string>();
    for (let i = 0; i < 6; i++) {
      seen.add(currentItem(q)!);
      q = next(q, true).queue;
    }
    expect(seen.has(removed)).toBe(false);
  });

  test("quitar no toca la pista actual ni las anteriores", () => {
    const q = removeUpcoming(createQueue(items, 2, noShuffle), 0);
    expect(currentItem(q)).toBe("c");
    expect(q.items).toEqual(["a", "b", "c"]);
  });

  test("reordenar lo que sigue", () => {
    const q = moveUpcoming(createQueue(items, 0, noShuffle), 0, 2);
    expect(currentItem(q)).toBe("a");
    expect(upcoming(q)).toEqual(["c", "d", "b"]);
  });

  test("reordenar fuera de rango no cambia nada", () => {
    const q = createQueue(items, 0, noShuffle);
    expect(upcoming(moveUpcoming(q, 0, 9))).toEqual(["b", "c", "d"]);
    expect(upcoming(removeUpcoming(q, 9))).toEqual(["b", "c", "d"]);
  });
});
