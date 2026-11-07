export type Repeat = "off" | "all" | "one";

export type Queue<T> = {
  items: T[];
  order: number[];
  cursor: number;
  shuffle: boolean;
  repeat: Repeat;
};

export type Step<T> = { queue: Queue<T>; restart: boolean; ended: boolean };

type Mode = { shuffle: boolean; repeat: Repeat };

function shuffled(indexes: number[]): number[] {
  const copy = [...indexes];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

const allIndexes = <T,>(items: T[]) => items.map((_, index) => index);

export function createQueue<T>(items: T[], start: number, mode: Mode): Queue<T> {
  const indexes = allIndexes(items);
  if (!mode.shuffle) return { items, order: indexes, cursor: start, ...mode };
  const rest = shuffled(indexes.filter((index) => index !== start));
  return { items, order: items.length ? [start, ...rest] : [], cursor: 0, ...mode };
}

export const currentItem = <T,>(queue: Queue<T>): T | undefined => queue.items[queue.order[queue.cursor]];

export const upcoming = <T,>(queue: Queue<T>): T[] =>
  queue.order.slice(queue.cursor + 1).map((index) => queue.items[index]);

/** `auto` es true cuando la pista terminó sola, false cuando alguien pidió la siguiente. */
export function next<T>(queue: Queue<T>, auto: boolean): Step<T> {
  if (auto && queue.repeat === "one") return { queue, restart: true, ended: false };
  if (queue.cursor + 1 < queue.order.length) {
    return { queue: { ...queue, cursor: queue.cursor + 1 }, restart: false, ended: false };
  }
  if (queue.repeat === "off") return { queue, restart: false, ended: true };
  const order = queue.shuffle ? shuffled(allIndexes(queue.items)) : queue.order;
  return { queue: { ...queue, order, cursor: 0 }, restart: false, ended: false };
}

export function prev<T>(queue: Queue<T>, position: number): Step<T> {
  if (position > 3 || queue.cursor === 0) return { queue, restart: true, ended: false };
  return { queue: { ...queue, cursor: queue.cursor - 1 }, restart: false, ended: false };
}

export function setShuffle<T>(queue: Queue<T>, shuffle: boolean): Queue<T> {
  const current = queue.order[queue.cursor];
  if (current === undefined) return { ...queue, shuffle };
  return createQueue(queue.items, current, { shuffle, repeat: queue.repeat });
}

export const setRepeat = <T,>(queue: Queue<T>, repeat: Repeat): Queue<T> => ({ ...queue, repeat });

/** `offset` cuenta desde la pista actual: 0 es la siguiente de `upcoming`. */
export const jumpTo = <T,>(queue: Queue<T>, offset: number): Queue<T> => ({
  ...queue,
  cursor: queue.cursor + 1 + offset,
});
