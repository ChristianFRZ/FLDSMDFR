# Animaciones del logo (apertura, post-login, crear casete)

## Intención
Dar identidad a tres momentos de la app usando el símbolo del logo (un casete con dos carretes), sin añadir dependencias.

## Objetivos
- Apertura: pantalla de bienvenida (~1,2 s) antes del login. El casete aparece, los carretes giran y el wordmark se dibuja. En cada carga o recarga de la página sin sesión (la del login), saltable con clic.
- Post-login: el casete se "inserta" y cruza hacia el reproductor (~0,9 s). Solo al entrar por el formulario, no al recargar una sesión abierta.
- Crear casete: el casete cae desde arriba y rebota en la pila; después navega al detalle.

## No objetivos
Librerías de animación, sonido, cambios al logo, animar otras pantallas.

## Anti-objetivos
Bloquear el uso (siempre saltable), retrasar la navegación más de ~1 s, ignorar `prefers-reduced-motion`.

## Restricciones
- CSS puro + SVG inline (el proyecto no usa librerías de animación; `app.css` ya usa `@keyframes`).
- Respetar tema claro/oscuro (`useTheme`, como `Logo.tsx`).
- Con `prefers-reduced-motion: reduce` se muestra el estado final sin movimiento.
- Puntos de enganche: `App.tsx`/`main.tsx` (apertura), `Login.tsx`/`Register.tsx` + `AuthContext` (post-login), `TapeCreate.tsx` `onSuccess` (crear).

## Enfoques
1. **SVG inline + CSS keyframes, un componente `LogoAnimation` con tres variantes (elegido).** Sin dependencias, consistente con el código; control fino sobre los carretes.
2. Librería (framer-motion/lottie): más cómodo para secuencias, pero añade peso y dependencia para tres animaciones cortas.
3. Imágenes/GIF/vídeo: no respetan el tema ni reduced-motion.

## Decisiones (llamadas mías, corregibles)
Duraciones 1,2 s / 0,9 s; apertura en cada carga de la página sin sesión (sin `sessionStorage`); post-login solo desde el formulario; tests de que cada variante se monta, se salta y respeta reduced-motion.

## Para quien construya
Colores exactos, easing, y el mecanismo para señalar "acaba de entrar por el formulario" (estado de navegación o flag en el contexto). Implementación delegada a un subagente Opus.
