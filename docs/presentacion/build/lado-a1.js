// Lado A · 1 (Christian Franco Ramírez): láminas 1–5.
const path = require('path');
const { C, F, LOGO, texto, textoRico, fondo, titulo, panel, caja, flecha, pista, casete } = require('./tema');

const ASSET = n => path.join(__dirname, '..', 'assets', n);
const NOTAS_PROBLEMA = 'Empecemos por el problema. La primera versión de MELOXO fue un monolito: una sola aplicación, un solo proceso y una sola base de datos. Ahí conviven tres cargas muy distintas. Primero, el login y las listas, que son consultas cortas y frecuentes. Segundo, el audio continuo, que mantiene conexiones largas mientras alguien escucha. Y tercero, la telemetría, que registra cada reproducción. Las tres compiten por los mismos recursos: si la telemetría se satura, el audio lo siente. Y lo peor es el punto único de falla: si cae el servidor o cae la base de datos, cae todo, incluso la música que alguien estaba escuchando. Eso es justo lo que queremos evitar.';
const NOTAS_MELOXO = 'Entonces, ¿qué es MELOXO? Es un servicio de streaming musical construido alrededor del casete compartido. Un casete tiene hasta 12 pistas repartidas en dos lados, el lado A y el lado B, y se arma entre hasta 8 miembros. Cada pista puede llevar una dedicatoria de hasta 140 caracteres, como la nota que le dejarías a un amigo en un casete de verdad. Y para sumar gente no hay buscador de personas: se invita por enlace. Aquí a la derecha vemos un casete real de la app, con sus dos lados y sus dedicatorias. Lo importante: no hay feed, no hay seguidores de personas y no hay likes. Solo se siguen artistas; la música se comparte en pequeño.';
const NOTAS_USUARIOS = 'MELOXO tiene tres roles. El Oyente es el usuario base: arma casetes con sus amigos, deja dedicatorias y sigue artistas. El Compositor es un oyente aprobado que publica su propia música: sube un MP3 de hasta 15 megas, con portada de hasta 2, y puede programar la fecha de publicación. Y el Administrador aprueba a los compositores, revisa la auditoría, importa el catálogo de Jamendo y consulta las métricas y la salud del sistema. Abajo a la derecha está el objetivo de disponibilidad que guía todo el diseño: elegimos AP, es decir, que la música se pueda reproducir aunque fallen las métricas, los avisos o Jamendo. El reproductor que ven es el que no debe dejar de sonar.';
const NOTAS_DEMO = 'Ahora, en lugar de explicarlo, vamos a verlo. Este es un video corto, de unos 25 segundos, grabado sobre la aplicación real levantada con docker compose. Les pido que se fijen en tres momentos. Primero, cómo se crea un casete nuevo: le ponemos el nombre, Para el profe, y la etiqueta del casete se va escribiendo sola. Segundo, cómo se agregan dos pistas, cada una con su dedicatoria, y cómo el casete pasa a mostrar sus dos pistas en el lado A. Y tercero, al final, el reproductor sonando: la pista actual aparece en el panel de la derecha y en la barra de abajo. Mientras corre el video lo narramos. Después de la demo, Miriam les explica cómo está construido todo esto por dentro: la arquitectura de contenedores.';


const NOTAS_PORTADA = 'Buenas tardes a todos, somos el equipo FLDSMDFR: Christian Franco, Miriam López, Erick Nava y yo, Brent Pérez, de Sistemas Distribuidos. Les presentamos MELOXO, tu casetera de confianza. MELOXO es un servicio de streaming musical construido alrededor del casete compartido: un casete tiene hasta 12 pistas repartidas en dos lados, se arma entre amigos, lleva dedicatorias y se reparte por enlace. No hay feed ni recomendaciones: la música se descubre porque alguien te la regala. Hoy les vamos a contar cómo MELOXO pasó de ser un monolito a un sistema distribuido, y qué decisiones y mediciones nos llevaron ahí.';

const EQUIPO = [['Lado A · 1', 'Christian Franco Ramírez'], ['Lado A · 2', 'Miriam Amisadai López Hernández'],
  ['Lado B · 1', 'Erick Nava Santiago'], ['Lado B · 2', 'Brent Armando Pérez Paitán']];

function agregar(pres) {
  // Lámina 1 · A·01 · portada
  const s = pres.addSlide();
  fondo(s);
  s.addImage({ path: LOGO, x: 0.5, y: 0.6, w: 5.4, h: 5.4 * 325 / 1200, objectName: 'logo', altText: 'MELOXO' });
  texto(s, 'Tu casetera de confianza', { x: 0.5, y: 2.4, w: 5.6, h: 0.45, fontFace: F.titulo, bold: true, fontSize: 26, objectName: 'lema' });
  texto(s, textoRico([['Música para '], ['compartir en pequeño', { color: C.rosa }], [', no para exhibir en grande.']]),
    { x: 0.5, y: 3.1, w: 5.4, h: 0.65, fontSize: 18, color: C.atenuado, objectName: 'frase' });
  texto(s, 'Equipo FLDSMDFR · Sistemas Distribuidos', { x: 0.5, y: 4.1, w: 6, h: 0.25, fontSize: 12, color: C.atenuado, objectName: 'equipo-titulo' });
  EQUIPO.forEach(([lado, nombre], i) => {
    const x = 0.5 + i * 2.3;
    texto(s, lado, { x, y: 4.5, w: 2.1, h: 0.3, fontFace: F.mano, fontSize: 16, color: C.rosa, objectName: 'integrante-lado-' + (i + 1) });
    texto(s, nombre, { x, y: 4.8, w: 2.1, h: 0.45, fontSize: 13, objectName: 'integrante-nombre-' + (i + 1) });
  });
  casete(s, { x: 6.15, y: 0.6, w: 3.4, rot: 4, color: C.rosa, etiqueta: 'Lado A' });
  pista(s, 'Lado A · 01 — quiénes somos\n→ qué es → por qué casete', { y: 3.45, w: 2.4 });
  s.addNotes(NOTAS_PORTADA);

  // Lámina 2 · A·02 · el problema
  const p = pres.addSlide();
  fondo(p);
  titulo(p, textoRico([['En un monolito, todo '], ['compite', { color: C.rosa }]]));
  caja(p, { x: 0.5, y: 1.45, w: 6.4, h: 3.75, nombre: 'caja-monolito' });
  texto(p, 'monolito', { x: 0.7, y: 1.55, w: 3, h: 0.3, bold: true, fontSize: 14, color: C.atenuado, objectName: 'monolito-rotulo' });
  [['login', 'Login y\nlistas', 'consultas cortas'], ['audio', 'Audio\ncontinuo', 'conexiones largas'], ['telemetria', 'Telemetría', 'un evento por escucha']].forEach(([id, nombre, desc], i) => {
    const x = 0.7 + i * 2.05;
    caja(p, { x, y: 1.95, w: 1.9, h: 1.5, nombre: 'caja-' + id });
    texto(p, nombre, { x: x + 0.1, y: 2.05, w: 1.7, h: 0.6, bold: true, fontSize: 16, objectName: 'flujo-' + id });
    texto(p, desc, { x: x + 0.1, y: 2.9, w: 1.7, h: 0.4, fontSize: 12, color: C.atenuado, objectName: 'flujo-' + id + '-detalle' });
    flecha(p, x + 0.95, 3.45, x + 0.95, 3.72, 'flecha-' + id);
  });
  caja(p, { x: 0.7, y: 3.75, w: 6.0, h: 0.6, nombre: 'caja-base' });
  texto(p, 'una sola base de datos', { x: 0.8, y: 3.75, w: 5.8, h: 0.6, bold: true, align: 'center', valign: 'middle', objectName: 'base-unica' });
  texto(p, 'Tres cargas distintas pelean por el mismo proceso y la misma base.', { x: 0.7, y: 4.5, w: 6.0, h: 0.5, fontSize: 14, color: C.atenuado, objectName: 'monolito-nota' });
  panel(p, { x: 7.2, y: 1.45, w: 2.3, h: 2.7 });
  texto(p, textoRico([['Un solo punto de '], ['falla', { color: C.rosa }]]), { x: 7.35, y: 1.6, w: 2.0, h: 0.75, bold: true, fontSize: 18, objectName: 'punto-falla-titulo' });
  texto(p, 'Si cae el servidor o la base de datos, cae todo, incluso el audio.', { x: 7.35, y: 2.5, w: 2.0, h: 1.4, fontSize: 14, objectName: 'punto-falla-texto' });
  pista(p, 'Lado A · 02 — monolito\n→ compiten → cae todo', { w: 2.4 });
  p.addNotes(NOTAS_PROBLEMA);

  // Lámina 3 · A·03 · MELOXO
  const m = pres.addSlide();
  fondo(m);
  titulo(m, 'El casete compartido');
  panel(m, { x: 0.5, y: 1.45, w: 5.6, h: 3.2 });
  m.addImage({ path: ASSET('cap-casete.png'), x: 0.6, y: 1.55, w: 5.4, h: 3.0375, objectName: 'captura-casete', altText: 'Un casete abierto en MELOXO, con dos lados y dedicatorias' });
  [['pistas', '12 pistas', 'en dos lados, A y B'], ['miembros', '8 miembros', 'por casete'], ['dedicatoria', '140', 'caracteres por dedicatoria'], ['enlace', 'Por enlace', 'así se invita a alguien']].forEach(([id, cifra, et], i) => {
    const y = 1.45 + i * 0.7;
    texto(m, cifra, { x: 6.5, y, w: 3.0, h: 0.4, fontFace: F.titulo, bold: true, fontSize: 24, objectName: 'cifra-' + id });
    texto(m, et, { x: 6.5, y: y + 0.4, w: 3.0, h: 0.25, fontSize: 13, color: C.atenuado, objectName: 'cifra-' + id + '-etiqueta' });
  });
  texto(m, textoRico([['Sin feed', { color: C.rosa }], [', sin seguidores de personas y sin likes: solo se siguen artistas.']]),
    { x: 0.5, y: 4.85, w: 6.0, h: 0.45, fontSize: 14, objectName: 'sin-feed' });
  pista(m, 'Lado A · 03 — 12 pistas\n→ 8 miembros → sin feed', { w: 2.4 });
  m.addNotes(NOTAS_MELOXO);

  // Lámina 4 · A·04 · usuarios
  const u = pres.addSlide();
  fondo(u);
  titulo(u, 'Tres roles, una meta: que suene');
  [['oyente', 'Oyente', 'Arma casetes con hasta 8 amigos\nDeja dedicatorias y sigue artistas'],
    ['compositor', 'Compositor', 'Oyente aprobado que publica su música\nMP3 de 15 MB, portada de 2 MB, publicación programada'],
    ['administrador', 'Administrador', 'Aprueba Compositores y lleva la auditoría\nImporta Jamendo y ve métricas y Salud']].forEach(([id, nombre, fn], i) => {
    const y = 1.45 + i * 1.2;
    caja(u, { x: 0.5, y, w: 5.2, h: 1.1, nombre: 'caja-' + id });
    texto(u, nombre, { x: 0.7, y: y + 0.12, w: 4.8, h: 0.3, bold: true, fontSize: 18, objectName: 'rol-' + id });
    texto(u, fn, { x: 0.7, y: y + 0.5, w: 4.8, h: 0.5, fontSize: 13, color: C.atenuado, objectName: 'rol-' + id + '-funciones' });
  });
  panel(u, { x: 6.0, y: 1.45, w: 3.5, h: 2.1 });
  u.addImage({ path: ASSET('cap-reproductor.png'), x: 6.1, y: 1.55, w: 3.3, h: 3.3 * 9 / 16, objectName: 'captura-reproductor', altText: 'El reproductor de MELOXO' });
  texto(u, textoRico([['Objetivo AP: se reproduce '], ['aunque fallen', { color: C.rosa }], [' las métricas, los avisos o Jamendo.']]),
    { x: 6.0, y: 3.8, w: 3.5, h: 0.55, fontSize: 14, objectName: 'objetivo-ap' });
  pista(u, 'Lado A · 04 — tres roles\n→ AP  → sigue sonando', { w: 2.4 });
  u.addNotes(NOTAS_USUARIOS);

  // Lámina 5 · A·05 · así se ve
  const v = pres.addSlide();
  fondo(v);
  titulo(v, 'Así se ve');
  panel(v, { x: 0.5, y: 1.35, w: 6.5, h: 3.74 });
  v.addImage({ path: ASSET('demo-fotograma.png'), x: 0.6, y: 1.45, w: 6.3, h: 6.3 * 9 / 16, objectName: 'video-demo', altText: 'Fotograma del video de demostración de MELOXO' });
  texto(v, 'video', { x: 7.5, y: 1.4, w: 2.0, h: 0.5, fontFace: F.mano, fontSize: 28, color: C.rosa, objectName: 'etiqueta-video' });
  texto(v, 'Crear un casete', { x: 7.5, y: 2.1, w: 2.0, h: 0.3, fontSize: 16, objectName: 'paso-crear' });
  texto(v, 'Agregar pistas', { x: 7.5, y: 2.6, w: 2.0, h: 0.3, fontSize: 16, objectName: 'paso-agregar' });
  texto(v, 'Reproducir', { x: 7.5, y: 3.1, w: 2.0, h: 0.3, fontSize: 16, objectName: 'paso-reproducir' });
  pista(v, 'Lado A · 05 — crear\n→ agregar → reproducir', { w: 2.4 });
  v.addNotes(NOTAS_DEMO);
}

module.exports = { agregar };
