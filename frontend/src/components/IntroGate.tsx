import { useState, type ReactNode } from "react";
import { hasSession } from "../api/client";
import { LogoAnimation } from "./LogoAnimation";

/**
 * Muestra la apertura animada del logo encima de `children` cada vez que se carga o se recarga la página sin
 * sesión (sin sesión toda ruta termina en el login). Los hijos se renderizan siempre debajo, sin esperar a que
 * termine.
 */
export function IntroGate({ children }: { children: ReactNode }) {
  const [show, setShow] = useState(() => !hasSession());

  return (
    <>
      {children}
      {show && <LogoAnimation variant="intro" onDone={() => setShow(false)} />}
    </>
  );
}
