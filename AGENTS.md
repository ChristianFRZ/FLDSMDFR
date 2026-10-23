# AGENTS.md

## 1. Arquitectura del proyecto

Para construir un monolito necesitamos:

- **Módulos claros:** cada módulo debe tener una responsabilidad específica.
- **Límites bien definidos:** cada módulo debe tener funciones y responsabilidades delimitadas.
- **Dependencias controladas:** evitar acoplamiento innecesario entre módulos.

### 1.1. Estructura general

Todo se ejecuta dentro de una sola aplicación, organizada por responsabilidades:

```text
/ui       # Interfaz de usuario
/core     # Lógica de negocio
/db       # Acceso y gestión de datos
```

### 1.2. Archivos del proyecto

- `AGENTS.md`: define cómo debe trabajar el agente de programación.
- `DESIGN.md`: define cómo debe verse el producto, incluyendo su diseño visual, componentes y experiencia de usuario.
- `SKILLS.md`: reúne habilidades, procedimientos y prompts reutilizables para tareas de desarrollo.

## 2. Herramientas para el proyecto

### 2.1. Laravel

Framework de desarrollo web de código abierto escrito en PHP. Permite construir aplicaciones web y API mediante una arquitectura organizada, siguiendo principalmente el patrón Modelo-Vista-Controlador (MVC). Destaca por su sintaxis expresiva, sus herramientas integradas y su amplio ecosistema.

### 2.2. Vue.js

Framework progresivo de JavaScript para construir interfaces de usuario. Proporciona herramientas, componentes y convenciones que facilitan el desarrollo de interfaces interactivas, reutilizables y mantenibles.

### 2.3. MySQL

Sistema de gestión de bases de datos relacionales desarrollado por Oracle. Utiliza SQL para organizar, almacenar, consultar y modificar información de manera estructurada.

Documentación: https://www.oracle.com/latam/mysql/what-is-mysql/

### 2.4. Plataformas de despliegue

- **Vercel:** plataforma para desplegar aplicaciones web, especialmente proyectos frontend y frameworks como Next.js. También admite otros frameworks mediante sus configuraciones correspondientes.
- **Netlify:** plataforma para desplegar y gestionar sitios web y aplicaciones frontend.
- **Railway:** plataforma para desplegar aplicaciones backend, servicios y bases de datos.

La plataforma debe seleccionarse según la arquitectura del proyecto y los requisitos de despliegue.

Enlaces:
- https://vercel.com/
- https://www.netlify.com/
- https://railway.com/

### 2.5. Cursor AI

Entorno de desarrollo basado en Visual Studio Code e integrado con herramientas de inteligencia artificial. Permite analizar código, generar implementaciones, detectar errores y facilitar la comprensión de proyectos existentes.

### 2.6. Durable AI

Plataforma basada en inteligencia artificial generativa orientada a la creación rápida de sitios web y herramientas para pequeños negocios.

## 3. Herramientas generales

- **Husky:** permite ejecutar scripts y verificaciones asociados a eventos de Git, como los commits.
  - https://github.com/typicode/husky
- **Codex / Claude Code:** agentes de programación que pueden analizar repositorios, modificar archivos, ejecutar comandos y apoyar en tareas de desarrollo.
- **Copy.ai:** plataforma de inteligencia artificial orientada a la generación de contenido comercial, marketing y automatización de procesos de ventas.
  - https://www.copy.ai/

## 4. Reglas de trabajo del agente

1. Analizar la estructura existente antes de modificar archivos.
2. Respetar la arquitectura y las responsabilidades de cada módulo.
3. Evitar duplicación de código y dependencias innecesarias.
4. Priorizar legibilidad, modularidad y mantenibilidad.
5. No modificar funcionalidades existentes sin justificación.
6. Validar entradas y manejar errores de manera explícita.
7. Escribir y ejecutar pruebas cuando corresponda.
8. Evitar agregar dependencias sin una necesidad concreta.
9. Documentar los cambios relevantes y explicar las decisiones técnicas.
10. No afirmar que una prueba pasó si no se ejecutó.
11. Mantener la documentación actualizada cuando cambie la arquitectura.
12. Identificar riesgos y limitaciones antes de proponer cambios importantes.

## 5. Criterios de aceptación

Un cambio se considera terminado cuando:

- Cumple con los requisitos solicitados.
- Respeta la arquitectura del proyecto.
- No introduce duplicación innecesaria.
- Maneja errores y casos límite relevantes.
- Cuenta con pruebas apropiadas cuando corresponda.
- No rompe funcionalidades existentes.
- Se documentan las decisiones importantes.
- Las validaciones ejecutadas y sus resultados se reportan con precisión.
