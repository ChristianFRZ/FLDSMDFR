import type { ReactNode } from "react";

type Props = { children: ReactNode; tape?: boolean; color?: "paper" | "yellow"; className?: string };

/** Papel rasgado, con cinta adhesiva si se pide. */
export function Note({ children, tape, color = "paper", className = "" }: Props) {
  const classes = ["note-wrap", tape ? "note-taped" : "", color === "yellow" ? "note-yellow" : "", className];
  return (
    <div className={classes.filter(Boolean).join(" ")}>
      <div className="note">{children}</div>
    </div>
  );
}
