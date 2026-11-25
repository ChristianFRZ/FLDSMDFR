// Lado B · 2 (Brent Armando Pérez Paitán): láminas 13–16. Caché, carga, aprendizajes y cierre con QR.
const { C, F, LOGO, texto, textoRico, fondo, titulo, panel, caja, pista, casete } = require('./tema');
const { RUTA_QR } = require('./qr');

const NOTAS_CACHE = 'Gracias, Erick. Yo soy Brent Pérez y cierro el lado B con la última rama, la 06: una caché de lectura. Es redis-cache, una instancia de Redis aparte del Redis durable. Tiene 64 megas, desalojo LRU y ninguna persistencia, así que sacar lo menos usado nunca toca las colas ni la revocación de sesiones. Y nada espera a la caché: si cae o se pone lenta, las lecturas van a PostgreSQL y responden igual. Con ella, GET /api/songs pasó de una mediana de 38 milisegundos a 13, y el percentil 95 de 70 a 28. En las gráficas, el top de métricas bajó de 31,6 a 7,1 milisegundos. Dos advertencias. El top lo medimos con 300 lecturas seguidas del administrador, no con 50 clientes. Y esos 38 milisegundos sin caché son más lentos que los 15 de la rama 03: no investigamos por qué, así que solo comparamos corridas hechas en las mismas condiciones.';
const NOTAS_CARGA = 'Para ver si aguantaba, usamos Locust: 50 clientes durante 2 minutos, primero sin redis-cache y luego con ella, con los mismos parámetros y sin tocar nada más. Sin caché fueron 5373 peticiones, con caché 5203, y en las dos corridas cero fallos. Con la caché, redis-cache terminó con 1368 aciertos, 1189 fallos y ninguna clave desalojada. Y ahora la parte honesta. La búsqueda de Locust usa solo seis palabras distintas, así que casi todas sus búsquedas son aciertos de caché. Además, el contador de 1368 aciertos y 1189 fallos incluye otras claves: los fallos incluyen las lecturas de versión y de estado de cuenta, no solo la lista. Con consultas más variadas la mejora sería menor: por eso decimos que estas cifras son optimistas. Las playlists y el primer byte de audio no cambian, porque esas rutas no se cachean; la diferencia entre corridas es ruido.';
const NOTAS_APRENDIZAJES = 'Nos quedan tres aprendizajes. Primero, la caché va en su propia instancia: con límite de memoria y desalojo LRU, y sin tocar el Redis que lleva las colas y la revocación. Segundo, nada debe esperar a una optimización: ningún servicio la declara como dependencia y, sin ella, todo responde igual desde PostgreSQL. Y tercero, medir bien es comparar dentro de las mismas condiciones, y decir lo que no sabemos. También hay cosas que dejamos fuera. La saga con estados, que hoy se resuelve con auditoría antes del commit y rollback. MongoDB, que el equipo descartó: todo sigue en PostgreSQL, una base por servicio. Los eventos track_hidden y track_restored, de modo que una pista oculta puede seguir en avisos ya guardados. Y la sala de escucha sincronizada, que no tuvo rama.';
const NOTAS_CIERRE = 'Con esto cerramos el casete. Empezamos con un monolito donde todo competía, y terminamos con servicios que se reparten el trabajo: una base por servicio, réplicas que se pueden caer sin que nadie lo note, un circuit breaker, colas que no pierden reproducciones, una revocación de sesión de 0,04 segundos y una caché que baja las lecturas de 38 a 13 milisegundos. Cada cifra que mostramos sale de la documentación del repositorio. Si quieren revisar el código, las decisiones o repetir las pruebas, el repositorio es público: escaneen el código QR o usen la dirección que está debajo. Muchas gracias por su atención. Ahora los escuchamos: estamos listos para sus preguntas.';

// Escala común de las barras de la lámina 13: pulgadas por milisegundo.
const ESC = 0.1;

function agregar(pres) {
  // Lámina 13 · B·05 · caché
  const k = pres.addSlide();
  fondo(k);
  titulo(k, textoRico([['Una '], ['caché', { color: C.rosa }], [' separada que acelera']]));
  const grupo = (id, y, cabecera, sub, sin, con) => {
    texto(k, cabecera, { x: 0.5, y, w: 3.0, h: 0.3, bold: true, fontSize: 15, objectName: id + '-titulo' });
    texto(k, sub, { x: 3.0, y: y + 0.03, w: 3.5, h: 0.25, fontSize: 12, color: C.atenuado, objectName: id + '-sub' });
    [['sin', 'sin caché', sin, C.atenuado], ['con', 'con caché', con, C.turquesa]].forEach(([q, rotulo, ms, color], i) => {
      const yy = y + 0.4 + i * 0.4;
      texto(k, rotulo, { x: 0.5, y: yy, w: 1.2, h: 0.32, fontFace: F.mano, fontSize: 16, color: q === 'con' ? C.turquesa : C.atenuado, valign: 'middle', objectName: `rotulo-${id}-${q}` });
      k.addShape(pres.ShapeType.rect, { x: 1.75, y: yy, w: ms * ESC, h: 0.32, fill: { color }, line: { color, width: 0 }, objectName: `barra-${id}-p50-${q}` });
      texto(k, String(ms).replace('.', ',') + ' ms', { x: 1.75 + ms * ESC + 0.1, y: yy, w: 1.0, h: 0.32, fontSize: 14, bold: true, color: q === 'con' ? C.turquesa : C.papel, valign: 'middle', objectName: `valor-${id}-${q}` });
    });
  };
  grupo('lista', 1.3, 'GET /api/songs', 'mediana (p50)', 38, 13);
  grupo('top', 2.75, 'Top de métricas', 'mediana (p50), 300 lecturas', 31.6, 7.1);
  panel(k, { x: 6.7, y: 1.3, w: 2.8, h: 1.55, nombre: 'panel-p95' });
  texto(k, 'p50 / p95 con caché', { x: 6.85, y: 1.4, w: 2.5, h: 0.25, fontSize: 12, color: C.atenuado, objectName: 'p95-con-rotulo' });
  texto(k, '13 / 28 ms', { x: 6.85, y: 1.65, w: 2.5, h: 0.5, fontFace: F.titulo, bold: true, fontSize: 28, color: C.turquesa, valign: 'middle', objectName: 'p95-con-cifra' });
  texto(k, textoRico([['sin caché  ', { color: C.atenuado }], ['38 / 70 ms', { bold: true }]]), { x: 6.85, y: 2.25, w: 2.5, h: 0.3, fontSize: 14, objectName: 'p95-sin-cifra' });
  texto(k, textoRico([['Con caché, el top baja de', { breakLine: true }], ['31,6 a 7,1 ms', { bold: true, color: C.turquesa }]]), { x: 6.7, y: 3.0, w: 2.8, h: 0.8, fontSize: 14, objectName: 'top-resumen' });
  texto(k, 'redis-cache: otra instancia, LRU de 64 MB, sin persistencia', { x: 0.5, y: 4.3, w: 6.2, h: 0.3, fontSize: 13, objectName: 'nota-instancia' });
  texto(k, 'El top lo midió una sola persona. Los 38 ms sin caché superan los 15 ms de la rama 03: no se investigó, y solo se compara dentro de la misma prueba.', { x: 0.5, y: 4.7, w: 6.2, h: 0.5, fontSize: 12, color: C.atenuado, objectName: 'nota-honesta' });
  pista(k, 'Lado B · 13 — caché\n→ 38 a 13  → LRU', { w: 2.4 });
  k.addNotes(NOTAS_CACHE);

  // Lámina 14 · B·06 · carga
  const g = pres.addSlide();
  fondo(g);
  titulo(g, textoRico([['Aguantó la '], ['carga', { color: C.rosa }]]));
  panel(g, { x: 0.5, y: 1.4, w: 4.4, h: 2.4, nombre: 'panel-cero' });
  texto(g, '0 fallos', { x: 0.7, y: 1.55, w: 4.0, h: 1.2, fontFace: F.titulo, bold: true, fontSize: 60, color: C.turquesa, valign: 'middle', objectName: 'cero-fallos' });
  texto(g, '50 clientes · 2 min', { x: 0.7, y: 2.8, w: 4.0, h: 0.4, fontFace: F.titulo, bold: true, fontSize: 20, objectName: 'carga-clientes' });
  texto(g, 'sin y con redis-cache, mismos parámetros', { x: 0.7, y: 3.28, w: 4.0, h: 0.3, fontSize: 13, color: C.atenuado, objectName: 'carga-parametros' });
  [['sin', 1.4, '5373', 'peticiones sin caché'], ['con', 2.65, '5203', 'peticiones con caché']].forEach(([q, y, cifra, rotulo]) => {
    caja(g, { x: 5.2, y, w: 4.3, h: 1.15, nombre: 'caja-peticiones-' + q });
    texto(g, cifra, { x: 5.4, y: y + 0.1, w: 1.9, h: 0.95, fontFace: F.titulo, bold: true, fontSize: 36, valign: 'middle', objectName: 'peticiones-' + q + '-cifra' });
    texto(g, textoRico([[rotulo, {}], ['\n0 fallos', { color: C.atenuado }]]), { x: 7.35, y: y + 0.1, w: 2.0, h: 0.95, fontSize: 14, valign: 'middle', objectName: 'peticiones-' + q + '-texto' });
  });
  caja(g, { x: 0.5, y: 4.05, w: 6.3, h: 1.2, nombre: 'caja-advertencia', atenuada: true });
  texto(g, textoRico([['Cifras ', { bold: true }], ['optimistas', { bold: true, color: C.rosa }]]), { x: 0.7, y: 4.15, w: 5.9, h: 0.3, fontSize: 15, objectName: 'advertencia-titulo' });
  texto(g, 'La búsqueda de la prueba usa solo 6 palabras distintas, así que casi todas las búsquedas son aciertos. Con consultas más variadas la mejora sería menor.', { x: 0.7, y: 4.5, w: 5.9, h: 0.65, fontSize: 13, color: C.atenuado, objectName: 'advertencia-texto' });
  pista(g, 'Lado B · 14 — carga\n→ 0 fallos  → optimista', { w: 2.4 });
  g.addNotes(NOTAS_CARGA);

  // Lámina 15 · B·07 · aprendizajes y pendientes
  const a = pres.addSlide();
  fondo(a);
  titulo(a, textoRico([['Lo que '], ['aprendimos', { color: C.rosa }], [' y lo que falta']]));
  const APR = [['Cada cosa en su Redis', 'la caché, con límite y desalojo LRU, no toca las colas ni la revocación'],
    ['Nada espera a la caché', 'si cae, las lecturas van a PostgreSQL y responden igual'],
    ['Medir en las mismas condiciones', 'y decir lo que no se sabe, como los 38 ms sin caché']];
  APR.forEach(([t, d], i) => {
    const y = 1.4 + i * 1.2;
    texto(a, String(i + 1), { x: 0.5, y, w: 0.5, h: 0.6, fontFace: F.mano, fontSize: 36, color: C.atenuado, objectName: `aprendizaje-${i + 1}-numero` });
    texto(a, t, { x: 1.1, y: y + 0.02, w: 4.2, h: 0.3, bold: true, fontSize: 16, objectName: `aprendizaje-${i + 1}` });
    texto(a, d, { x: 1.1, y: y + 0.36, w: 4.2, h: 0.6, fontSize: 13, color: C.atenuado, objectName: `aprendizaje-${i + 1}-detalle` });
  });
  panel(a, { x: 5.6, y: 1.3, w: 3.9, h: 2.95, nombre: 'panel-fuera' });
  texto(a, textoRico([['Quedó ', {}], ['fuera', { color: C.rosa }]]), { x: 5.85, y: 1.42, w: 3.4, h: 0.35, fontFace: F.titulo, bold: true, fontSize: 18, objectName: 'fuera-titulo' });
  const FUERA = [['Saga con estados', 'hoy: auditoría antes del commit y rollback'],
    ['MongoDB', 'decisión del equipo; solo PostgreSQL'],
    ['track_hidden', 'pista oculta sigue en avisos guardados'],
    ['Sala sincronizada', 'sala de escucha, sin rama asignada']];
  FUERA.forEach(([t, d], i) => {
    const y = 1.9 + i * 0.54;
    texto(a, t, { x: 5.85, y, w: 3.4, h: 0.26, bold: true, fontSize: 14, objectName: `fuera-${i + 1}` });
    texto(a, d, { x: 5.85, y: y + 0.26, w: 3.4, h: 0.24, fontSize: 12, color: C.atenuado, objectName: `fuera-${i + 1}-detalle` });
  });
  pista(a, 'Lado B · 15 — aprender\n→ medir  → pendiente', { w: 2.6 });
  a.addNotes(NOTAS_APRENDIZAJES);

  // Lámina 16 · B·08 · cierre
  const z = pres.addSlide();
  fondo(z);
  titulo(z, 'Gracias', { fontSize: 36 });
  texto(z, textoRico([['¿Alguna ', {}], ['pregunta', { color: C.rosa }], ['?', {}]]), { x: 0.5, y: 1.2, w: 5.0, h: 0.5, fontFace: F.titulo, bold: true, fontSize: 22, objectName: 'preguntas' });
  casete(z, { x: 0.6, y: 1.95, w: 3.6, rot: -5, color: C.rosa, etiqueta: 'Lado B' });
  z.addImage({ path: LOGO, x: 0.5, y: 4.45, w: 2.8, h: 2.8 * 325 / 1200, objectName: 'logo', altText: 'MELOXO' });
  texto(z, 'FLDSMDFR', { x: 3.5, y: 4.5, w: 1.6, h: 0.4, fontFace: F.mano, fontSize: 20, color: C.atenuado, valign: 'middle', objectName: 'equipo' });
  panel(z, { x: 5.9, y: 1.2, w: 3.6, h: 3.05, nombre: 'panel-qr' });
  z.addImage({ path: RUTA_QR, x: 6.6, y: 1.35, w: 2.2, h: 2.2, objectName: 'qr-repo', altText: 'Código QR del repositorio de MELOXO en GitHub' });
  texto(z, 'github.com/zmd-brnt/MELOXO', { x: 6.0, y: 3.65, w: 3.4, h: 0.3, fontSize: 14, bold: true, align: 'center', objectName: 'url-repo' });
  texto(z, 'el código y las decisiones, públicos', { x: 6.0, y: 3.93, w: 3.4, h: 0.25, fontFace: F.mano, fontSize: 16, color: C.atenuado, align: 'center', objectName: 'url-nota' });
  pista(z, 'Lado B · 16 — gracias\n→ repo  → preguntas', { w: 2.6 });
  z.addNotes(NOTAS_CIERRE);
}

module.exports = { agregar };
