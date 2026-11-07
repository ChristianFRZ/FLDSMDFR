# Sesión

| Archivo | Para qué sirve |
| --- | --- |
| [`AuthContext.tsx`](AuthContext.tsx) | `useAuth()` da el usuario actual, `login`, `register` y `logout` |
| [`RequireAuth.tsx`](RequireAuth.tsx) | Sin sesión, manda a iniciar sesión y recuerda la ruta de origen para que una invitación no se pierda |
| [`RequireRole.tsx`](RequireRole.tsx) | Saca de las rutas de otro rol |

Esto solo organiza la interfaz: el permiso real lo revisa el backend en cada ruta.
