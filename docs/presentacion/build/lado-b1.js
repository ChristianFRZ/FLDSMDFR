// Lado B · 1 (Erick Nava Santiago): láminas 9–12. Divisor, circuit breaker, cola y sesiones, mensajería.
const { C, F, texto, textoRico, fondo, titulo, panel, caja, flecha, pista, casete } = require('./tema');

const NOTAS_DIVISOR = 'Gracias, Miriam. Hasta aquí vimos cómo MELOXO se reparte en servicios y qué cuesta medirlo. Ahora damos vuelta al casete: en el lado B van las canciones difíciles, lo que pasa cuando algo falla. Soy Erick Nava y les voy a contar tres cosas. Primero, cómo un servicio caído no arrastra a los demás, con timeouts, reintentos y un circuit breaker. Segundo, cómo no perdemos reproducciones cuando playback-metrics se cae, y cómo cerramos una sesión en el mismo instante en que cambia el rol. Y tercero, cómo los avisos de lanzamientos siguen funcionando aunque catálogo no responda, gracias a la mensajería con Redis Streams. Todo esto lo medimos, así que vienen cifras.';
const NOTAS_BREAKER = 'Empecemos por la primera línea de defensa. Cada llamada entre servicios espera como máximo 1,5 segundos la lectura, y las lecturas se reintentan dos veces, con esperas de 200 y 400 milisegundos. Pero reintentar contra un servicio caído solo empeora las cosas, así que cada cliente lleva un circuit breaker con tres estados. Cerrado: las llamadas pasan. Si acumula cinco fallos en 30 segundos, se abre: ya no llama y falla de inmediato. A los 15 segundos pasa a semiabierto y deja pasar una sola llamada de prueba: si sale bien, se cierra; si falla, vuelve a abrirse. Lo comprobamos congelando catálogo: la primera llamada tardó 5,1 segundos, y con el breaker abierto la respuesta tardó 17 milisegundos. Un detalle honesto: el breaker vive en la memoria de cada réplica, así que con dos réplicas cada una abre por su cuenta.';
const NOTAS_COLA = 'Ahora dos casos donde antes algo dependía de una espera. El primero, las reproducciones. Cuando playback-metrics está caído, POST /api/playbacks no falla: catálogo responde 202 y deja la reproducción en una cola de Redis Streams. Antes dependíamos de que el navegador reintentara, y si se cerraba la pestaña, se perdía. En la prueba detuvimos playback-metrics y hicimos tres reproducciones: las tres respondieron 202 y, al volver el servicio, se aplicaron las tres sin duplicar. Incluso con Redis reiniciado y 20 eventos pendientes, se aplicaron exactamente los 20. El segundo caso, la revocación de sesión. Antes, si un administrador cambiaba un rol o suspendía una cuenta, el token anterior podía seguir valiendo hasta 30 segundos por la caché. Ahora la revocación vive en Redis: el token anterior tarda 0,04 segundos en dar 401. Y un evento de reproducción se ve en el historial con una mediana de 0,033 segundos y un máximo de 0,07. La saga con estados la dejamos fuera a propósito.';
const NOTAS_OUTBOX = 'Cerramos con mensajería. Cuando se publica una pista, quienes siguen al artista reciben un aviso, y antes eso dependía de que catálogo respondiera. Ahora catálogo escribe la pista y el evento track_published en la misma transacción: es el patrón outbox. Un relevo, cada 2 segundos, lee los eventos sin relevar y los publica en Redis Streams; solo después los marca como relevados. Users-playlists consume de forma idempotente: la clave es el identificador de la pista, así que un evento repetido no cambia nada. Y si un mensaje falla, tras 5 intentos va a la cola de mensajes muertos, sin atascar a los demás. El resultado: 132 eventos relevados y 0 pendientes; de ellos, 101 llegaron como avisos, porque las pistas de Jamendo, ocultas o borradas se marcan sin publicar. Y los avisos ya no dependen de catálogo: con catálogo caído responden completos. Queda pendiente track_hidden: una pista que se oculta después de publicarse sigue apareciendo en los avisos ya guardados.';

function agregar(pres) {
  // Lámina 9 · B·01 · divisor
  const d = pres.addSlide();
  fondo(d);
  titulo(d, textoRico([['Lado B: cuando algo '], ['falla', { color: C.rosa }]]));
  casete(d, { x: 0.6, y: 1.55, w: 4.6, rot: -7, color: C.cobalto, etiqueta: 'Lado B' });
  texto(d, 'Lado B · 1', { x: 5.8, y: 1.9, w: 3.7, h: 0.35, fontFace: F.mano, fontSize: 20, color: C.atenuado, objectName: 'divisor-lado' });
  texto(d, 'Erick Nava Santiago', { x: 5.8, y: 2.35, w: 3.7, h: 0.45, fontFace: F.titulo, bold: true, fontSize: 20, objectName: 'divisor-expositor' });
  texto(d, 'Timeouts, circuit breaker, colas y mensajería', { x: 5.8, y: 2.95, w: 3.7, h: 0.65, fontSize: 16, color: C.atenuado, objectName: 'divisor-temas' });
  pista(d, 'Lado B · 09 — algo falla\n→ se aísla  → sigue', { w: 2.6 });
  d.addNotes(NOTAS_DIVISOR);

  // Lámina 10 · B·02 · circuit breaker
  const b = pres.addSlide();
  fondo(b);
  titulo(b, textoRico([['Un '], ['breaker', { color: C.rosa }], [' que deja de esperar']]));
  const estado = (id, nombre, detalle, x, y, w, h, atenuada) => {
    caja(b, { x, y, w, h, nombre: 'caja-' + id, atenuada });
    texto(b, nombre, { x: x + 0.1, y: y + 0.12, w: w - 0.2, h: 0.35, bold: true, fontSize: 18, align: 'center', objectName: 'estado-' + id });
    texto(b, detalle, { x: x + 0.1, y: y + 0.52, w: w - 0.2, h: h - 0.6, fontSize: 13, color: C.atenuado, align: 'center', objectName: 'estado-' + id + '-detalle' });
  };
  estado('cerrado', 'cerrado', 'las llamadas pasan', 0.5, 2.55, 2.3, 1.1);
  estado('abierto', 'abierto', 'falla sin esperar', 3.85, 1.35, 2.3, 1.5);
  estado('semiabierto', 'semiabierto', 'deja pasar una llamada de prueba', 7.2, 2.55, 2.3, 1.1);
  texto(b, '17 ms', { x: 3.95, y: 2.1, w: 2.1, h: 0.45, fontFace: F.titulo, bold: true, fontSize: 22, color: C.turquesa, align: 'center', valign: 'middle', objectName: 'abierto-cifra' });
  texto(b, 'en vez de 5,1 s (1.ª llamada)', { x: 3.9, y: 2.55, w: 2.2, h: 0.25, fontSize: 12, color: C.atenuado, align: 'center', objectName: 'abierto-cifra-nota' });
  flecha(b, 2.8, 2.9, 3.85, 2.2, 'flecha-abre');
  flecha(b, 6.15, 2.2, 7.2, 2.9, 'flecha-prueba');
  flecha(b, 8.35, 3.65, 8.35, 4.0, 'flecha-cierra-1', C.atenuado);
  b.addShape(pres.ShapeType.line, { x: 1.65, y: 4.0, w: 6.7, h: 0, flipH: true, line: { color: C.atenuado, width: 2 }, objectName: 'flecha-cierra-2' });
  flecha(b, 1.65, 4.0, 1.65, 3.65, 'flecha-cierra-3');
  texto(b, '5 fallos en 30 s', { x: 0.5, y: 2.1, w: 2.4, h: 0.3, bold: true, fontSize: 14, color: C.papel, align: 'right', objectName: 'transicion-abre' });
  texto(b, 'a los 15 s, una llamada de prueba', { x: 6.9, y: 1.95, w: 2.6, h: 0.55, bold: true, fontSize: 14, align: 'right', objectName: 'transicion-prueba' });
  texto(b, 'si la prueba sale bien, se cierra; si falla, vuelve a abrirse', { x: 2.0, y: 4.07, w: 6.0, h: 0.3, fontSize: 13, color: C.atenuado, align: 'center', objectName: 'transicion-cierra' });
  texto(b, textoRico([['Antes: ', { bold: true }], ['lectura con timeout de 1,5 s y 2 reintentos, de 200 y 400 ms.']]),
    { x: 0.5, y: 4.6, w: 6.4, h: 0.55, fontSize: 13, color: C.atenuado, objectName: 'nota-timeouts' });
  pista(b, 'Lado B · 10 — contar\n→ abrir  → probar', { w: 2.6 });
  b.addNotes(NOTAS_BREAKER);

  // Lámina 11 · B·03 · cola y sesiones
  const c = pres.addSlide();
  fondo(c);
  titulo(c, textoRico([['Sin '], ['perder', { color: C.rosa }], [', sin '], ['esperar', { color: C.rosa }]]));
  const tarjeta = (id, x, cabecera, sub) => {
    texto(c, cabecera, { x: x + 0.25, y: 1.45, w: 3.9, h: 0.3, bold: true, fontSize: 16, objectName: id + '-titulo' });
    texto(c, sub, { x: x + 0.25, y: 1.78, w: 3.9, h: 0.25, fontSize: 12, color: C.atenuado, objectName: id + '-subtitulo' });
    texto(c, 'antes', { x: x + 0.25, y: 2.2, w: 1.0, h: 0.25, fontFace: F.mano, fontSize: 16, color: C.atenuado, objectName: id + '-antes-rotulo' });
    texto(c, 'ahora', { x: x + 0.25, y: 3.0, w: 1.0, h: 0.25, fontFace: F.mano, fontSize: 16, color: C.turquesa, objectName: id + '-despues-rotulo' });
  };
  caja(c, { x: 0.5, y: 1.3, w: 4.4, h: 2.9, nombre: 'caja-cola' });
  tarjeta('cola', 0.5, 'Cola de reproducciones', 'con playback-metrics caído');
  texto(c, 'Solo el navegador reintentaba: si se cerraba la pestaña, se perdía.', { x: 0.75, y: 2.5, w: 3.9, h: 0.5, fontSize: 13, color: C.atenuado, objectName: 'cola-antes-texto' });
  texto(c, '202', { x: 0.75, y: 3.2, w: 1.5, h: 0.6, fontFace: F.titulo, bold: true, fontSize: 40, color: C.turquesa, valign: 'middle', objectName: 'cola-despues-cifra' });
  texto(c, 'responde y encola en Redis Streams', { x: 2.35, y: 3.2, w: 2.4, h: 0.6, fontSize: 13, valign: 'middle', objectName: 'cola-despues-texto' });
  texto(c, textoRico([['3 de 3', { bold: true, color: C.turquesa }], [' aplicadas al volver']]), { x: 0.75, y: 3.85, w: 3.9, h: 0.25, fontSize: 13, objectName: 'cola-resultado' });
  panel(c, { x: 5.1, y: 1.3, w: 4.4, h: 2.9, nombre: 'panel-revocacion' });
  tarjeta('revocacion', 5.1, 'Revocación de sesión', 'al cambiar un rol o suspender');
  texto(c, '30 s', { x: 5.35, y: 2.45, w: 1.5, h: 0.5, fontFace: F.titulo, bold: true, fontSize: 28, color: C.atenuado, valign: 'middle', objectName: 'revocacion-antes-cifra' });
  texto(c, 'el token anterior valía hasta que vencía la caché', { x: 6.95, y: 2.45, w: 2.4, h: 0.5, fontSize: 13, color: C.atenuado, valign: 'middle', objectName: 'revocacion-antes-texto' });
  texto(c, '0,04 s', { x: 5.35, y: 3.2, w: 1.9, h: 0.6, fontFace: F.titulo, bold: true, fontSize: 36, color: C.turquesa, valign: 'middle', objectName: 'revocacion-despues-cifra' });
  texto(c, 'es lo que tarda en dar 401 el token anterior', { x: 7.35, y: 3.2, w: 2.0, h: 0.6, fontSize: 13, valign: 'middle', objectName: 'revocacion-despues-texto' });
  texto(c, 'La revocación vive en Redis', { x: 5.35, y: 3.85, w: 3.9, h: 0.25, fontSize: 12, color: C.atenuado, objectName: 'revocacion-nota' });
  pista(c, 'Lado B · 11 — encolar\n→ 202  → revocar', { w: 2.4 });
  c.addNotes(NOTAS_COLA);

  // Lámina 12 · B·04 · mensajería
  const m = pres.addSlide();
  fondo(m);
  titulo(m, textoRico([['El '], ['outbox', { color: C.rosa }], [' no pierde avisos']]));
  const PASOS = [['catalog-streaming', 'guarda la pista y el evento en la misma transacción'],
    ['relevo de catálogo', 'cada 2 s publica lo no relevado en Redis Streams'],
    ['users-playlists', 'consume de forma idempotente: un repetido no cambia nada'],
    ['aviso', 'se lee de la tabla local, sin llamar a catálogo']];
  PASOS.forEach(([quien, que], i) => {
    const x = 0.5 + i * 2.3;
    caja(m, { x, y: 1.4, w: 2.0, h: 2.0, nombre: 'caja-paso-' + (i + 1) });
    texto(m, String(i + 1), { x: x + 0.15, y: 1.5, w: 0.4, h: 0.35, fontFace: F.mano, fontSize: 20, color: C.atenuado, objectName: 'numero-paso-' + (i + 1) });
    texto(m, quien, { x: x + 0.1, y: 1.9, w: 1.8, h: 0.3, bold: true, fontSize: 13, objectName: 'paso-' + (i + 1) });
    texto(m, que, { x: x + 0.1, y: 2.25, w: 1.8, h: 1.05, fontSize: 13, color: C.atenuado, objectName: 'paso-' + (i + 1) + '-detalle' });
    if (i < 3) flecha(m, x + 2.0, 2.4, x + 2.3, 2.4, 'flecha-paso-' + (i + 1));
  });
  flecha(m, 6.0, 3.4, 6.0, 3.85, 'flecha-dlq');
  caja(m, { x: 5.2, y: 3.85, w: 1.6, h: 1.2, nombre: 'caja-dlq', atenuada: true });
  texto(m, 'cola de mensajes muertos tras 5 intentos', { x: 5.25, y: 3.85, w: 1.5, h: 1.2, fontSize: 13, color: C.atenuado, align: 'center', valign: 'middle', objectName: 'dlq-texto' });
  panel(m, { x: 0.5, y: 3.85, w: 4.3, h: 1.4, nombre: 'panel-resultado' });
  texto(m, [{ text: '132 relevados', options: { breakLine: true } }, { text: '0 sin relevar' }],
    { x: 0.7, y: 3.95, w: 3.9, h: 0.85, fontFace: F.titulo, bold: true, fontSize: 24, color: C.turquesa, valign: 'middle', objectName: 'resultado-cifra' });
  texto(m, 'en published_events, 0 con relayed_at nulo', { x: 0.7, y: 4.85, w: 3.9, h: 0.25, fontSize: 12, color: C.atenuado, objectName: 'resultado-nota' });
  pista(m, 'Lado B · 12 — outbox\n→ relevo  → idempotente', { w: 2.7 });
  m.addNotes(NOTAS_OUTBOX);
}

module.exports = { agregar };
