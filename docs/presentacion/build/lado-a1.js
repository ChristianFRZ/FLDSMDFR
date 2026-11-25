// Lado A · 1 (Christian Franco Ramírez): láminas 1–5. Por ahora, solo la portada.
const { C, F, LOGO, texto, textoRico, fondo, pista, casete } = require('./tema');

const NOTAS_PORTADA = 'Buenas tardes a todos, somos el equipo FLDSMDFR: Christian Franco, Miriam López, Erick Nava y yo, Brent Pérez, de Sistemas Distribuidos. Les presentamos MELOXO, tu casetera de confianza. MELOXO es un servicio de streaming musical construido alrededor del casete compartido: un casete tiene hasta 12 pistas repartidas en dos lados, se arma entre amigos, lleva dedicatorias y se reparte por enlace. No hay feed ni recomendaciones: la música se descubre porque alguien te la regala. Hoy les vamos a contar cómo MELOXO pasó de ser un monolito a un sistema distribuido, y qué decisiones y mediciones nos llevaron ahí.';

const EQUIPO = [['Lado A · 1', 'Christian Franco Ramírez'], ['Lado A · 2', 'Miriam Amisadai López Hernández'],
  ['Lado B · 1', 'Erick Nava Santiago'], ['Lado B · 2', 'Brent Armando Pérez Paitán']];

function agregar(pres) {
  // Lámina 1 · A·01 · portada
  const s = pres.addSlide();
  fondo(s);
  s.addImage({ path: LOGO, x: 0.5, y: 0.6, w: 5.4, h: 5.4 * 325 / 1200, objectName: 'logo', altText: 'MELOXO' });
  texto(s, 'Tu casetera de confianza', { x: 0.5, y: 2.4, w: 5.6, h: 0.95, fontFace: F.titulo, bold: true, fontSize: 26, objectName: 'lema' });
  texto(s, textoRico([['Música para '], ['compartir en pequeño', { color: C.rosa }], [', no para exhibir en grande.']]),
    { x: 0.5, y: 3.4, w: 5.4, h: 0.6, fontSize: 18, color: C.atenuado, objectName: 'frase' });
  texto(s, 'Equipo FLDSMDFR · Sistemas Distribuidos', { x: 0.5, y: 4.2, w: 6, h: 0.2, fontSize: 12, color: C.atenuado, objectName: 'equipo-titulo' });
  EQUIPO.forEach(([lado, nombre], i) => {
    const x = 0.5 + i * 2.3;
    texto(s, lado, { x, y: 4.5, w: 2.1, h: 0.3, fontFace: F.mano, fontSize: 16, color: C.rosa, objectName: 'integrante-lado-' + (i + 1) });
    texto(s, nombre, { x, y: 4.8, w: 2.1, h: 0.45, fontSize: 13, objectName: 'integrante-nombre-' + (i + 1) });
  });
  casete(s, { x: 6.15, y: 0.6, w: 3.4, rot: 4, color: C.rosa, etiqueta: 'Lado A' });
  pista(s, 'Lado A · 01 — quiénes somos\n→ qué es → por qué casete', { y: 3.45, w: 2.4 });
  s.addNotes(NOTAS_PORTADA);
}

module.exports = { agregar };
