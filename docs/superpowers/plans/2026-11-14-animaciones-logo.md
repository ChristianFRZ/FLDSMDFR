# Animaciones del logo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tres animaciones con el símbolo del logo: apertura antes del login, entrada tras el login y creación de casete.

**Architecture:** Un componente `LogoAnimation` (SVG inline + CSS keyframes) con tres variantes. Un hook `useDone` dispara `onDone` tras la duración de la variante (o de inmediato con reduced-motion). Cada momento lo monta como overlay: `IntroGate` en `App.tsx`, un flag `entered` en `AuthContext` para el post-login y un estado `created` en `TapeCreate`.

**Tech Stack:** React 18, react-router-dom 6, @tanstack/react-query, vitest + Testing Library, CSS puro (`frontend/src/styles/app.css`).

**Spec:** `docs/superpowers/specs/2026-11-14-animaciones-logo-design.md`

## Global Constraints

- Sin dependencias nuevas (nada de framer-motion/lottie).
- Duraciones: intro 1200 ms, enter 900 ms, drop ~900 ms; la navegación tras crear no se retrasa más de 1000 ms.
- Símbolo del logo: path de `frontend/src/assets/meloxo-stacked-color-light.svg` (`#symbol`, relleno `#FF3D8B`); wordmark según tema vía `useTheme` (como `components/Logo.tsx`).
- `prefers-reduced-motion: reduce`: sin movimiento, `onDone` se llama de inmediato.
- Toda animación es saltable con clic o tecla y nunca bloquea la interacción más allá de su duración.
- Textos de UI en español. Los README de cada carpeta se actualizan si cambian (`components/README.md`, `styles/README.md`).
- Commits sin `Co-Authored-By` (regla del usuario para MELOXO).
- Pruebas desde `frontend/`: `npx vitest run <archivo>`; al final `npm test` y `npx tsc --noEmit`.

## Review Focus

- Recarga con sesión abierta: no debe mostrar ni la apertura ni la entrada.
- Registro (`Register`) también entra por formulario: debe mostrar la entrada igual que el login.
- Login fallido: no debe mostrar la entrada.
- `sessionStorage` bloqueado (lanza excepción): la app debe arrancar igual, mostrando la apertura.
- Crear casete con error de API: sin animación y el formulario sigue usable.

---

### Task 1: Componente `LogoAnimation` y hook `useDone`

**Files:**
- Create: `frontend/src/components/LogoAnimation.tsx`, `frontend/src/components/LogoAnimation.test.tsx`, `frontend/src/components/motion.ts`
- Modify: `frontend/src/styles/app.css` (keyframes y clases `.logo-anim*`), `frontend/src/components/README.md`, `frontend/src/styles/README.md`

**Interfaces:**
- Produces: `motion.ts`: `prefersReducedMotion(): boolean` (false si no existe `matchMedia`), `DURATIONS = { intro: 1200, enter: 900, drop: 900 } as const`, `useDone(ms: number, onDone: () => void): void` (llama `onDone` una sola vez tras `ms`, o en el siguiente tick si `prefersReducedMotion()`; limpia el timer al desmontar).
- Produces: `LogoAnimation({ variant, onDone }: { variant: "intro" | "enter"; onDone: () => void })`. Renderiza un overlay `role="status"` con `aria-label="Cargando MELOXO"` (intro) o `"Entrando"` (enter), `className="logo-anim logo-anim-<variant>"`. Clic o cualquier tecla llama `onDone` (una sola vez). `intro` muestra símbolo (carretes girando) + wordmark; `enter` muestra solo el símbolo cruzando hacia abajo a la derecha.

- [ ] **Step 1: Write the failing tests** en `LogoAnimation.test.tsx` (fake timers):
  - `intro llama onDone tras 1200 ms y no antes` (a 1199 ms 0 llamadas, a 1200 ms 1).
  - `enter llama onDone tras 900 ms`.
  - `un clic salta y onDone se llama solo una vez` (clic y luego avanzar 2000 ms → 1 llamada).
  - `con reduced-motion llama onDone de inmediato` (mock `window.matchMedia` → `matches: true`).
  - `expone el estado accesible` (`getByRole("status", { name: "Cargando MELOXO" })`).
- [ ] **Step 2: Run** `npx vitest run src/components/LogoAnimation.test.tsx` → FAIL (módulo no existe).
- [ ] **Step 3: Implement** `motion.ts` y `LogoAnimation.tsx` con las firmas de arriba. Copiar los paths del SVG (`#symbol`, `#wordmark`); colores del wordmark por tema con `useTheme().resolved` (`#141317` claro, el del `...-dark.svg` en oscuro). Keyframes en `app.css`: `.logo-anim` overlay fijo a pantalla completa con fondo `var(--bg)` (verificar el token en `styles/tokens.css`), aparición del casete con escala+opacidad, carretes con `spin` ya existente, wordmark con `stroke-dashoffset`/fade; `enter` desliza y desvanece. Añadir `@media (prefers-reduced-motion: reduce)` que anula animaciones.
- [ ] **Step 4: Run** el test → PASS. Añadir una línea por archivo nuevo en los README.
- [ ] **Step 5: Commit** `git add frontend/src/components frontend/src/styles && git commit -m "feat: componente LogoAnimation con variantes intro y enter"`

### Task 2: Apertura (`IntroGate`)

**Files:**
- Create: `frontend/src/components/IntroGate.tsx`, `frontend/src/components/IntroGate.test.tsx`
- Modify: `frontend/src/App.tsx` (envolver `<Routes>` con `<IntroGate>`)

**Interfaces:**
- Consumes: `LogoAnimation`, `hasSession` de `api/client`.
- Produces: `IntroGate({ children }: { children: ReactNode })`: muestra `<LogoAnimation variant="intro">` encima de `children` solo si no hay sesión (`!hasSession()`) y `sessionStorage["meloxo.intro"]` no existe; al terminar guarda la marca (en `try/catch`; si falla no importa) y deja de mostrarse.

- [ ] **Step 1: Write failing tests:** `muestra la apertura sin sesión` ; `no la muestra con sesión abierta` (mock `hasSession → true`); `no se repite en la misma pestaña tras terminar`; `arranca aunque sessionStorage lance` (mock `Storage.prototype.setItem/getItem` que lanzan → muestra apertura y luego los hijos).
- [ ] **Step 2: Run** `npx vitest run src/components/IntroGate.test.tsx` → FAIL.
- [ ] **Step 3: Implement** `IntroGate` con las reglas de arriba; los `children` siempre se renderizan debajo (no se retrasan).
- [ ] **Step 4: Run** → PASS; `npx vitest run src/App` si existe test de App.
- [ ] **Step 5: Commit** `feat: apertura animada antes del login`

### Task 3: Entrada tras el login/registro

**Files:**
- Modify: `frontend/src/auth/AuthContext.tsx`, `frontend/src/components/AppShell.tsx` (o `Shell` en `App.tsx`)
- Test: `frontend/src/auth/AuthContext.test.tsx` (crear si no existe), `frontend/src/components/AppShell.test.tsx`

**Interfaces:**
- Produces: `Auth` gana `entered: boolean` y `clearEntered: () => void`. `entered` pasa a `true` solo dentro de `enter()` (login y registro tras éxito); la carga inicial de sesión (`/api/users/me` en el `useEffect`) NO lo activa; `logout` y fin de sesión lo ponen en `false`.
- Consumes: `Shell` en `App.tsx` monta `{entered && <LogoAnimation variant="enter" onDone={clearEntered} />}`.

- [ ] **Step 1: Write failing tests:** `login correcto activa entered`; `login fallido no activa entered`; `register correcto activa entered`; `cargar una sesión guardada no activa entered`; `clearEntered lo apaga`; en Shell: `muestra la animación de entrada cuando entered` y `no la muestra si no`.
- [ ] **Step 2: Run** `npx vitest run src/auth src/components/AppShell.test.tsx` → FAIL.
- [ ] **Step 3: Implement** el estado `entered` en `AuthProvider` (añadirlo al `useMemo` y sus deps) y el montaje en `Shell`.
- [ ] **Step 4: Run** → PASS y `npm test` completo sin regresiones (los tests de `Login`/`Register` existentes).
- [ ] **Step 5: Commit** `feat: animación de entrada tras el login`

### Task 4: Caída del casete al crearlo

**Files:**
- Modify: `frontend/src/pages/TapeCreate.tsx`, `frontend/src/styles/app.css` (`.tape-drop`), `frontend/src/pages/TapeCreate.test.tsx`

**Interfaces:**
- Consumes: `useDone`, `DURATIONS.drop`, `Tape`.
- Behavior: `onSuccess` ya no navega directo: guarda `created` (el `TapeSummary`) y renderiza un overlay `role="status"` `aria-label="Casete creado"` con `<Tape title={created.title} color={created.color} className="tape-drop" />` que cae y rebota; `useDone(DURATIONS.drop, () => navigate(\`/tapes/${created.id}\`, { replace: true }))`. Con reduced-motion navega de inmediato. En error no hay overlay.

- [ ] **Step 1: Write failing tests** (fake timers donde haga falta): `tras crear muestra "Casete creado" y navega a /tapes/t1 a los 900 ms` (comprobar con una ruta destino en el `MemoryRouter`); `no navega antes de tiempo`; `con reduced-motion navega sin esperar`; `con error de API no muestra la animación y el botón sigue activo`. Los tests existentes siguen verdes.
- [ ] **Step 2: Run** `npx vitest run src/pages/TapeCreate.test.tsx` → FAIL.
- [ ] **Step 3: Implement** el estado `created` y el overlay; CSS `.tape-drop` con keyframes de caída (translateY desde -120vh, rebote final) y su bloque `prefers-reduced-motion`.
- [ ] **Step 4: Run** `npm test` y `npx tsc --noEmit` → todo PASS. Probar a mano en `npm run dev`: apertura, entrada y creación, en tema claro y oscuro.
- [ ] **Step 5: Commit** `feat: caída animada al crear un casete`

## Self-review
- Cobertura: apertura (T2), entrada (T3), creación (T4), reduced-motion/saltable/tema (T1), sessionStorage y sesión abierta (T2/T3), error de API (T4).
- Tipos: `LogoAnimation` variantes `"intro" | "enter"` (la caída usa `Tape`, no `LogoAnimation`); `useDone`/`DURATIONS` definidos en T1 y usados en T4.
- Nota: la spec habla de "símbolo del logo" también en la caída; se usa el `Tape` existente (mismo casete) para no duplicar el dibujo. Llamada mía, corregible.
