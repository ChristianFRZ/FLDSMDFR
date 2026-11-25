// Tema de la presentación: colores, fuentes y motivos reutilizables. Medidas en pulgadas.
const path = require('path');

const C = {
  tinta: '141317', panel: '201F25', linea: '4A4852', papel: 'F4F1EA', atenuado: 'BDB9AF',
  rosa: 'FF3D8B', turquesa: '00D1BE', amarillo: 'FFD233', cobalto: '4A5CFF',
};
const F = { titulo: 'Montserrat', cuerpo: 'Roboto', mano: 'Caveat' };
const FONDO = path.join(__dirname, '..', 'assets', 'fondo-puntos.png');
const LOGO = path.join(__dirname, '..', 'assets', 'meloxo-horizontal-color-dark.png');

let SH = null; // tipos de forma de pptxgenjs, se fija con iniciar(pres)
function iniciar(pres) { SH = pres.ShapeType; }

/** Cuadro de texto base: Roboto 14 pt, color papel, sin margen. */
function texto(slide, contenido, o) {
  slide.addText(contenido, Object.assign(
    { isTextBox: true, margin: 0, valign: 'top', color: C.papel, fontFace: F.cuerpo, fontSize: 14 }, o));
}

/** Texto con partes de formato distinto: textoRico([['normal'], ['clave', {color: C.rosa}]]). */
function textoRico(partes) {
  return partes.map(([text, options]) => ({ text, options: options || {} }));
}

function fondo(slide) { slide.background = { path: FONDO }; }

function titulo(slide, contenido, o) {
  texto(slide, contenido, Object.assign(
    { x: 0.5, y: 0.5, w: 9, h: 0.6, fontFace: F.titulo, bold: true, fontSize: 30, objectName: 'titulo' }, o));
}

/** Panel destacado: borde papel con sombra rosa desplazada. */
function panel(slide, { x, y, w, h, nombre = 'panel' }) {
  slide.addShape(SH.roundRect, { x: x + 0.08, y: y + 0.08, w, h, rectRadius: 0.12,
    fill: { color: C.rosa }, line: { color: C.rosa, width: 0 }, objectName: nombre + '-sombra' });
  slide.addShape(SH.roundRect, { x, y, w, h, rectRadius: 0.12,
    fill: { color: C.panel }, line: { color: C.papel, width: 1.5 }, objectName: nombre });
}

/** Caja de diagrama (línea discontinua si atenuada). */
function caja(slide, { x, y, w, h, nombre, atenuada }) {
  slide.addShape(SH.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: C.panel },
    line: { color: C.linea, width: 1.5, dashType: atenuada ? 'dash' : 'solid' }, objectName: nombre });
}

function flecha(slide, x1, y1, x2, y2, nombre, color) {
  slide.addShape(SH.line, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipV: y2 < y1, line: { color: color || C.atenuado, width: 2, endArrowType: 'triangle' }, objectName: nombre });
}

/** Nota de pista: papel rotado -2° con cinta amarilla. Por defecto, esquina inferior derecha. */
function pista(slide, contenido, { y, w = 2.1, h = 0.7 } = {}) {
  const x = 10 - 0.4 - w;
  const yy = y === undefined ? 5.625 - 0.4 - h : y;
  slide.addShape(SH.rect, { x, y: yy, w, h, fill: { color: C.papel }, line: { color: C.papel, width: 0 },
    rotate: -2, objectName: 'pista-papel' });
  slide.addShape(SH.rect, { x: x + w / 2 - 0.35, y: yy - 0.09, w: 0.7, h: 0.18,
    fill: { color: C.amarillo, transparency: 15 }, line: { color: C.amarillo, width: 0, transparency: 15 },
    rotate: 3, objectName: 'pista-cinta' });
  texto(slide, contenido, { x: x + 0.1, y: yy, w: w - 0.2, h, fontFace: F.mano, fontSize: 15, color: C.tinta,
    align: 'left', valign: 'middle', rotate: -2, objectName: 'pista' });
}

/** Casete dibujado con formas. w es el ancho; el alto es w*2.2/3.4. rot en grados. */
function casete(slide, { x, y, w, rot = 0, color = C.rosa, etiqueta = 'Lado A' }) {
  const k = w / 3.4, h = 2.2 * k, cx = x + w / 2, cy = y + h / 2, ang = rot * Math.PI / 180;
  const lugar = (px, py, pw, ph) => {
    const dx = px + pw / 2 - cx, dy = py + ph / 2 - cy;
    const rx = cx + dx * Math.cos(ang) - dy * Math.sin(ang), ry = cy + dx * Math.sin(ang) + dy * Math.cos(ang);
    return { x: rx - pw / 2, y: ry - ph / 2, w: pw, h: ph, rotate: rot };
  };
  slide.addShape(SH.roundRect, Object.assign(lugar(x, y, w, h),
    { rectRadius: 0.15 * k, fill: { color }, line: { color, width: 0 }, objectName: 'casete-cuerpo' }));
  const et = lugar(x + 0.3 * k, y + 0.26 * k, 2.8 * k, 0.92 * k);
  slide.addShape(SH.roundRect, Object.assign({}, et,
    { rectRadius: 0.06 * k, fill: { color: C.papel }, line: { color: C.papel, width: 0 }, objectName: 'casete-etiqueta' }));
  texto(slide, etiqueta, Object.assign({}, et, { fontFace: F.mano, fontSize: Math.round(32 * k), color: C.tinta,
    align: 'center', valign: 'middle', objectName: 'casete-lado' }));
  [x + 0.65 * k, x + w - 0.65 * k - 0.72 * k].forEach((rx, i) => {
    slide.addShape(SH.ellipse, Object.assign(lugar(rx, y + 1.35 * k, 0.72 * k, 0.72 * k),
      { fill: { color: C.tinta }, line: { color: C.tinta, width: 0 }, objectName: 'carrete-' + i }));
    slide.addShape(SH.ellipse, Object.assign(lugar(rx + 0.24 * k, y + 1.59 * k, 0.24 * k, 0.24 * k),
      { fill: { color: C.papel }, line: { color: C.papel, width: 0 }, objectName: 'carrete-centro-' + i }));
  });
}

module.exports = { C, F, LOGO, FONDO, iniciar, texto, textoRico, fondo, titulo, panel, caja, flecha, pista, casete };
