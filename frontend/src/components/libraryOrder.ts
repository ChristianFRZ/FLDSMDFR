export type LibrarySort = "default" | "name";

type Key<T> = { id: (item: T) => string; name: (item: T) => string };

const collator = new Intl.Collator("es", { sensitivity: "base" });

/** Las fijadas van primero. Dentro de cada grupo manda el orden elegido: el que llega o el nombre. */
export function orderLibrary<T>(items: T[], pinned: readonly string[], sort: LibrarySort, key: Key<T>): T[] {
  const fixed = new Set(pinned);
  const arrange = (list: T[]) => (sort === "name" ? [...list].sort((a, b) => collator.compare(key.name(a), key.name(b))) : list);
  return [
    ...arrange(items.filter((item) => fixed.has(key.id(item)))),
    ...arrange(items.filter((item) => !fixed.has(key.id(item)))),
  ];
}
