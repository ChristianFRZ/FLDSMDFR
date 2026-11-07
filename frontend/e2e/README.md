# Pruebas de navegador

Playwright sobre la app real: Vite en el puerto 5174 y el backend de Docker en el 8080. Playwright inicia Vite por su cuenta; el backend hay que levantarlo antes.

```bash
docker compose up -d              # desde la raíz del repositorio
cd frontend
npx playwright install chromium   # solo la primera vez
npm run e2e
```

No hace falta la semilla, porque [`setup.ts`](setup.ts) crea lo que necesita.

| Archivo | Para qué sirve |
| --- | --- |
| [`setup.ts`](setup.ts) | Crea por la API un Compositor, una pista y un casete. Lee `ADMIN_EMAIL` y `ADMIN_PASSWORD` de `.env` |
| [`helpers.ts`](helpers.ts) | Inicio de sesión, avance con Tab y revisión con axe |
| [`responsive.spec.ts`](responsive.spec.ts) | Teléfono a 390 y 320 px: pestañas, reproductor, hoja y desbordes |
| [`a11y.spec.ts`](a11y.spec.ts) | Escritorio: flujo solo con teclado, foco visible y axe |
| [`fixtures/`](fixtures/README.md) | Archivos que usan las pruebas |

[`playwright.config.ts`](../playwright.config.ts) define dos proyectos: `telefono` corre `responsive.spec.ts` y `escritorio` corre `a11y.spec.ts`.

Cada ejecución agrega a la base de datos local usuarios `compositor-…` y `oyente-…@meloxo.dev`, una pista y un casete. No corras estas pruebas contra una base con datos que quieras conservar.
