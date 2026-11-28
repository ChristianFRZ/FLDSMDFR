import { describe, expect, test } from "vitest";
import { orderLibrary } from "./libraryOrder";

type Item = { id: string; name: string };
const key = { id: (item: Item) => item.id, name: (item: Item) => item.name };
const items: Item[] = [
  { id: "1", name: "Zeta" },
  { id: "2", name: "Álbum" },
  { id: "3", name: "beta" },
  { id: "4", name: "Carretera" },
];
const ids = (list: Item[]) => list.map((item) => item.id);

describe("orden de la biblioteca", () => {
  test("el orden predeterminado respeta el que llega", () => {
    expect(ids(orderLibrary(items, [], "default", key))).toEqual(["1", "2", "3", "4"]);
  });

  test("las fijadas van primero y conservan su orden relativo", () => {
    expect(ids(orderLibrary(items, ["4", "2"], "default", key))).toEqual(["2", "4", "1", "3"]);
  });

  test("por nombre ordena sin distinguir mayúsculas ni acentos", () => {
    expect(ids(orderLibrary(items, [], "name", key))).toEqual(["2", "3", "4", "1"]);
  });

  test("por nombre, las fijadas van primero y cada grupo va ordenado", () => {
    expect(ids(orderLibrary(items, ["1", "4"], "name", key))).toEqual(["4", "1", "2", "3"]);
  });

  test("una fijada que ya no existe se ignora", () => {
    expect(ids(orderLibrary(items, ["borrada"], "default", key))).toEqual(["1", "2", "3", "4"]);
  });

  test("no modifica la lista original", () => {
    const copy = [...items];
    orderLibrary(items, ["4"], "name", key);
    expect(items).toEqual(copy);
  });

  test("una lista vacía queda vacía", () => {
    expect(orderLibrary([], ["1"], "name", key)).toEqual([]);
  });
});
