import type { LibrarySort } from "./libraryOrder";
import { useLibraryPrefs } from "./libraryPrefs";

export function LibrarySortSelect() {
  const { sort, setSort } = useLibraryPrefs();
  return (
    <select className="sort" aria-label="Ordenar biblioteca" value={sort} onChange={(event) => setSort(event.target.value as LibrarySort)}>
      <option value="default">Predeterminado</option>
      <option value="name">Nombre (A–Z)</option>
    </select>
  );
}
