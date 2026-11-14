import { Icon } from "./Icon";
import { useLibraryPrefs } from "./libraryPrefs";

/** Fija o suelta un elemento de la biblioteca. El nombre no cambia: el estado va en `aria-pressed`. */
export function PinButton({ id, label }: { id: string; label: string }) {
  const { pinned, togglePin } = useLibraryPrefs();
  const on = pinned.includes(id);
  return (
    <button className={on ? "pin on" : "pin"} type="button" aria-pressed={on} aria-label={`Fijar ${label}`} onClick={() => togglePin(id)}>
      <Icon name="pin" filled={on} />
    </button>
  );
}
