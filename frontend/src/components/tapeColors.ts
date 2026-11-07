/** Los cuatro primeros conservan su nombre: así están guardados los casetes que ya existen. */
export const TAPE_COLORS = [
  { value: "pink", hex: "#ff3d8b", label: "Rosa" },
  { value: "yellow", hex: "#ffd233", label: "Amarillo" },
  { value: "teal", hex: "#00d1be", label: "Turquesa" },
  { value: "cobalt", hex: "#4a5cff", label: "Cobalto" },
  { value: "#ff6b4a", hex: "#ff6b4a", label: "Coral" },
  { value: "#ff9a2e", hex: "#ff9a2e", label: "Naranja" },
  { value: "#b6e03c", hex: "#b6e03c", label: "Lima" },
  { value: "#2fb672", hex: "#2fb672", label: "Verde" },
  { value: "#4cc3ff", hex: "#4cc3ff", label: "Cielo" },
  { value: "#b58cff", hex: "#b58cff", label: "Lila" },
  { value: "#efe3c8", hex: "#efe3c8", label: "Crema" },
  { value: "#5a5763", hex: "#5a5763", label: "Grafito" },
];

/** Un color guardado es un nombre de la paleta o un `#RRGGBB` elegido a mano. */
export function tapeHex(color: string): string {
  return TAPE_COLORS.find((item) => item.value === color)?.hex ?? color;
}
