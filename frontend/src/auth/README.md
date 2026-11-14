# Sesión

| Archivo | Para qué sirve |
| --- | --- |
| [`AuthContext.tsx`](AuthContext.tsx) | `useAuth()` da el usuario actual, `login`, `register` y `logout`, y `entered`/`clearEntered`, que marcan que se acaba de entrar por el formulario para mostrar la animación de entrada |
| [`RequireAuth.tsx`](RequireAuth.tsx) | Sin sesión, manda a iniciar sesión y recuerda la ruta de origen para que una invitación no se pierda |
| [`RequireRole.tsx`](RequireRole.tsx) | Saca de las rutas de otro rol |

Esto solo organiza la interfaz: el permiso real lo revisa el backend en cada ruta.
