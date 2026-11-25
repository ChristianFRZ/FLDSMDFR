// Lado A · 2 (Miriam Amisadai López Hernández): láminas 6–8. Por ahora, solo la rama 03 (lámina 8).
const { C, F, texto, textoRico, fondo, titulo, panel, caja, flecha, pista } = require('./tema');

const NOTAS_RAMA_03 = 'Aquí está la pieza que protege a todo lo demás: nginx en el borde. Cada petición pasa primero por auth_request, que valida el token JWT antes de llegar a cualquier servicio; si el token no sirve, ni siquiera entra. Detrás del borde tenemos dos réplicas del servicio de catálogo y streaming, y nginx reparte la carga entre ellas. Para comprobar que esto sirve, hicimos una prueba de carga y a mitad de ella apagamos una de las réplicas. Resultado: 0 de 293 peticiones fallaron; los usuarios no notaron nada. Tiene un precio, claro: verificar el token en cada petición cuesta alrededor de 3 milisegundos en p50. Y GET /api/songs se mantiene en 15 milisegundos en p50 y 34 en p95. Para nosotros, ese costo vale la tolerancia a fallos.';

const NOTAS_ARQUITECTURA = 'Gracias, Christian. Ahora veamos cómo está construido todo esto por dentro. MELOXO corre en nueve contenedores de larga vida con Docker Compose. Arriba está el edge: nginx es la entrada única; hacia fuera solo entra nginx, y en local también se publica PostgreSQL para las pruebas. Para cada petición a la API, nginx le consulta a gateway-auth con auth_request, que valida el token y el rol y no tiene base de datos; después reparte por ruta a users-playlists, a las dos réplicas de catalog-streaming o a playback-metrics. Entre servicios hablamos HTTP por rutas internas: users-playlists le pide pistas a catalog-streaming, y catalog-streaming consulta a users-playlists; playback-metrics le pide pistas a catalog-streaming y el estado de cuenta a users-playlists; y gateway-auth consulta el estado de cuenta a users-playlists. Abajo están los datos. PostgreSQL, con una base y un rol por servicio. Redis, durable, con dos Redis Streams: playbacks, de catalog-streaming a playback-metrics, y track_published, de catalog-streaming a users-playlists; además guarda la revocación de sesiones. Y redis-cache, una instancia aparte con desalojo LRU y sin persistencia, que usan catalog-streaming, playback-metrics y gateway-auth. El stack: Python 3.12, FastAPI, PostgreSQL 16, Redis, React 18 y Docker Compose.';
const NOTAS_RAMA_01_02 = 'Separar el monolito en servicios no fue gratis, así que lo medimos. Hicimos la misma prueba de carga sobre el monolito y sobre los tres servicios, en la misma computadora, con 50 usuarios simultáneos. Estas son las medianas y los percentiles 95, en milisegundos. El primer byte de audio pasó de 12 y 39 a 9 y 20. GET /api/songs pasó de 36 y 71 a 12 y 26: el catálogo ya no compite con el resto por el mismo proceso. Pero fíjense en la fila de abajo: en GET /api/playlists, la mediana sube de 27 a 31 milisegundos, probablemente por el salto HTTP extra, porque ahora la lista le pide las pistas al servicio de catálogo. Es una inferencia nuestra, no lo aislamos. Lo decimos tal cual: ahí la separación parece costar. Eso sí, el p95 baja de 66 a 55, así que las peores peticiones mejoran. Los tres umbrales de latencia se siguen cumpliendo.';

function agregar(pres) {
  // Lámina 6 · A·06 · arquitectura
  const a = pres.addSlide();
  fondo(a);
  titulo(a, textoRico([['Nueve', { color: C.rosa }], [' contenedores']]), { w: 6 });
  const nodo = (id, lineas, x, y, w, h) => {
    caja(a, { x, y, w, h, nombre: 'caja-' + id });
    const partes = lineas.map((l, k) => {
      const runs = (Array.isArray(l) ? l : [[l]]).map(([t, o]) => ({ text: t, options: Object.assign(k === 0 ? { bold: true } : { fontSize: 12, color: C.atenuado }, o || {}) }));
      runs[runs.length - 1].options.breakLine = k < lineas.length - 1;
      return runs;
    }).flat();
    texto(a, partes, { x: x + 0.05, y, w: w - 0.1, h, fontSize: 13, align: 'center', valign: 'middle', objectName: id });
  };
  nodo('edge', ['edge · nginx', 'entrada única: valida sesión y reparte rutas'], 0.45, 1.3, 8.82, 0.6);
  const SV = [['gateway-auth', 'token y rol, sin base'], ['users-playlists', 'cuentas y casetes'], ['catalog-streaming', 'réplica 1 · audio'],
    ['catalog-streaming', 'réplica 2 · audio'], ['playback-metrics', 'reproducciones']];
  const cx = [];
  SV.forEach(([nombre, rol], i) => {
    const x = 0.45 + i * 1.78;
    cx.push(x + 0.85);
    nodo('servicio-' + (i + 1), [nombre, rol], x, 2.45, 1.7, 0.75);
    flecha(a, x + 0.85, 1.9, x + 0.85, 2.45, 'flecha-edge-' + (i + 1));
  });
  texto(a, 'auth_request', { x: 1.4, y: 2.0, w: 1.5, h: 0.25, fontSize: 12, color: C.atenuado, objectName: 'rotulo-auth' });
  texto(a, 'proxy por ruta', { x: 3.2, y: 2.0, w: 1.5, h: 0.25, fontSize: 12, color: C.atenuado, objectName: 'rotulo-proxy' });
  // una sola conexión punteada entre servicios
  const punteada = (x, y, w, h, nombre) => a.addShape(pres.ShapeType.line, { x, y, w, h, line: { color: C.atenuado, width: 1.5, dashType: 'dash' }, objectName: nombre });
  cx.forEach((x, i) => punteada(x, 3.2, 0, 0.25, 'enlace-servicio-' + (i + 1)));
  punteada(cx[0], 3.45, cx[4] - cx[0], 0, 'enlace-internal');
  texto(a, 'HTTP /internal entre servicios', { x: 3.0, y: 3.5, w: 4.4, h: 0.25, fontSize: 12, color: C.atenuado, align: 'center', objectName: 'rotulo-internal' });
  nodo('postgres', ['postgres', 'una base y un rol por servicio', 'usan: users-playlists, catalog, playback-metrics'], 0.45, 3.85, 3.2, 1.05);
  nodo('redis-cache', ['redis-cache', 'caché LRU, sin persistencia', 'usan: catalog, playback-metrics, gateway-auth'], 3.8, 3.85, 2.7, 1.05);
  nodo('redis', ['redis', [['Redis Streams', { color: C.rosa, bold: true }], [' · durable']], 'playbacks y track_published', 'y revocación de sesiones'], 6.65, 3.85, 2.65, 1.05);
  texto(a, 'Python 3.12 · FastAPI · PostgreSQL 16 · Redis · React 18 · Docker Compose',
    { x: 0.5, y: 5.02, w: 8.7, h: 0.25, fontSize: 13, color: C.atenuado, objectName: 'stack' });
  pista(a, 'Lado A · 06 — edge\n→ servicios → datos', { x: 6.9, y: 0.45, w: 2.4, h: 0.7 });
  a.addNotes(NOTAS_ARQUITECTURA);

  // Lámina 7 · A·07 · rama 01→02
  const r = pres.addSlide();
  fondo(r);
  titulo(r, textoRico([['Monolito contra '], ['tres servicios', { color: C.rosa }]]));
  panel(r, { x: 6.1, y: 1.3, w: 3.4, h: 3.05, nombre: 'panel-servicios' });
  texto(r, 'monolito', { x: 3.7, y: 1.45, w: 2.2, h: 0.3, bold: true, fontSize: 14, color: C.atenuado, objectName: 'col-monolito' });
  texto(r, '3 servicios', { x: 6.3, y: 1.45, w: 3.0, h: 0.3, bold: true, fontSize: 14, objectName: 'col-servicios' });
  texto(r, 'p50 / p95, en ms', { x: 0.5, y: 1.45, w: 3.0, h: 0.3, fontSize: 12, color: C.atenuado, objectName: 'col-unidad' });
  [['audio', 'Primer byte de audio', 'objetivo p95 < 500 ms', '12 / 39', '9 / 20', C.turquesa],
    ['songs', 'GET /api/songs', 'objetivo p95 < 300 ms', '36 / 71', '12 / 26', C.turquesa],
    ['playlists', 'GET /api/playlists/{id}', 'objetivo p95 < 200 ms', '27 / 66', '31 / 55', C.papel]].forEach(([id, nombre, obj, antes, despues, color], i) => {
    const y = 1.85 + i * 0.85;
    texto(r, nombre, { x: 0.5, y, w: 3.1, h: 0.3, bold: true, fontSize: 14, objectName: 'fila-' + id });
    texto(r, obj, { x: 0.5, y: y + 0.32, w: 3.1, h: 0.25, fontSize: 12, color: C.atenuado, objectName: 'fila-' + id + '-objetivo' });
    texto(r, antes, { x: 3.7, y, w: 2.2, h: 0.5, fontFace: F.titulo, bold: true, fontSize: 24, color: C.atenuado, valign: 'middle', objectName: 'antes-' + id });
    texto(r, despues, { x: 6.3, y, w: 3.0, h: 0.5, fontFace: F.titulo, bold: true, fontSize: 24, color, valign: 'middle', objectName: 'despues-' + id });
  });
  texto(r, textoRico([['En playlists el '], ['p50 sube', { color: C.rosa }], [' de 27 a 31 ms, probablemente por el salto HTTP extra entre servicios. El p95 sí baja, de 66 a 55 ms.']]),
    { x: 0.5, y: 4.6, w: 6.4, h: 0.6, fontSize: 13, color: C.atenuado, objectName: 'nota-playlists' });
  pista(r, 'Lado A · 07 — medir\n→ comparar → un salto extra', { y: 4.68, w: 2.4, h: 0.62 });
  r.addNotes(NOTAS_RAMA_01_02);

  // Lámina 8 · A·08 · rama 03
  const s = pres.addSlide();
  fondo(s);
  titulo(s, 'Si cae una réplica, nadie lo nota');
  caja(s, { x: 0.5, y: 2.85, w: 0.8, h: 0.7, nombre: 'caja-cliente' });
  texto(s, 'cliente', { x: 0.5, y: 2.85, w: 0.8, h: 0.7, bold: true, align: 'center', valign: 'middle', objectName: 'cliente' });
  caja(s, { x: 1.5, y: 2.3, w: 1.2, h: 1.8, nombre: 'caja-edge' });
  texto(s, 'edge · nginx', { x: 1.55, y: 2.78, w: 1.1, h: 0.3, bold: true, align: 'center', objectName: 'edge-nombre' });
  texto(s, 'auth_request valida el JWT', { x: 1.55, y: 3.18, w: 1.1, h: 0.45, fontSize: 13, color: C.atenuado, align: 'center', objectName: 'edge-subtitulo' });
  caja(s, { x: 3.05, y: 1.5, w: 1.9, h: 1.4, nombre: 'caja-replica-1' });
  texto(s, 'catalog-streaming #1', { x: 3.1, y: 1.5, w: 1.8, h: 1.4, bold: true, align: 'center', valign: 'middle', objectName: 'replica-1' });
  caja(s, { x: 3.05, y: 3.5, w: 1.9, h: 1.4, nombre: 'caja-replica-2', atenuada: true });
  texto(s, [{ text: 'catalog-streaming #2', options: { breakLine: true } }, { text: 'caída' }],
    { x: 3.1, y: 3.5, w: 1.8, h: 1.4, color: C.atenuado, align: 'center', valign: 'middle', objectName: 'replica-2' });
  texto(s, '×', { x: 4.6, y: 3.5, w: 0.3, h: 0.4, fontSize: 24, bold: true, color: C.rosa, align: 'center', valign: 'middle', objectName: 'equis-caida' });
  flecha(s, 1.3, 3.2, 1.5, 3.2, 'flecha-cliente');
  flecha(s, 2.7, 3.2, 3.05, 2.2, 'flecha-1');
  flecha(s, 2.7, 3.2, 3.05, 4.2, 'flecha-2', C.linea);
  panel(s, { x: 5.1, y: 1.4, w: 4.4, h: 2.0, nombre: 'panel-cifra' });
  texto(s, '0 / 293', { x: 5.2, y: 1.5, w: 4.2, h: 1.15, fontFace: F.titulo, bold: true, fontSize: 80, color: C.turquesa, valign: 'middle', objectName: 'cifra-0-293' });
  texto(s, 'peticiones fallidas al apagar una réplica', { x: 5.25, y: 2.75, w: 4.1, h: 0.4, fontSize: 16, objectName: 'cifra-leyenda' });
  texto(s, '+3 ms', { x: 5.2, y: 3.55, w: 2.2, h: 0.35, fontFace: F.titulo, bold: true, fontSize: 20, color: C.rosa, objectName: 'dato-auth-cifra' });
  texto(s, 'costo de auth_request en p50', { x: 5.2, y: 3.95, w: 2.3, h: 0.2, fontSize: 12, color: C.atenuado, objectName: 'dato-auth-etiqueta' });
  texto(s, '15 / 34 ms', { x: 7.6, y: 3.55, w: 1.95, h: 0.35, fontFace: F.titulo, bold: true, fontSize: 20, objectName: 'dato-songs-cifra' });
  texto(s, 'GET /api/songs p50 / p95', { x: 7.6, y: 3.95, w: 1.95, h: 0.2, fontSize: 12, color: C.atenuado, objectName: 'dato-songs-etiqueta' });
  pista(s, 'Lado A · 08 —\nfailover → 0 de 293 → costo: 3 ms', { w: 2.8, h: 0.9 });
  s.addNotes(NOTAS_RAMA_03);
}

module.exports = { agregar };
