// Lado A · 2 (Miriam Amisadai López Hernández): láminas 6–8. Por ahora, solo la rama 03 (lámina 8).
const { C, F, texto, fondo, titulo, panel, caja, flecha, pista } = require('./tema');

const NOTAS_RAMA_03 = 'Aquí está la pieza que protege a todo lo demás: nginx en el borde. Cada petición pasa primero por auth_request, que valida el token JWT antes de llegar a cualquier servicio; si el token no sirve, ni siquiera entra. Detrás del borde tenemos dos réplicas del servicio de catálogo y streaming, y nginx reparte la carga entre ellas. Para comprobar que esto sirve, hicimos una prueba de carga y a mitad de ella apagamos una de las réplicas. Resultado: 0 de 293 peticiones fallaron; los usuarios no notaron nada. Tiene un precio, claro: verificar el token en cada petición cuesta alrededor de 3 milisegundos en p50. Y GET /api/songs se mantiene en 15 milisegundos en p50 y 34 en p95. Para nosotros, ese costo vale la tolerancia a fallos.';

function agregar(pres) {
  // Lámina 8 · A·08 · rama 03
  const s = pres.addSlide();
  fondo(s);
  titulo(s, 'Cae una réplica y nadie lo nota');
  caja(s, { x: 0.5, y: 2.85, w: 0.8, h: 0.7, nombre: 'caja-cliente' });
  texto(s, 'cliente', { x: 0.5, y: 2.85, w: 0.8, h: 0.7, bold: true, align: 'center', valign: 'middle', objectName: 'cliente' });
  caja(s, { x: 1.5, y: 2.3, w: 1.2, h: 1.8, nombre: 'caja-edge' });
  texto(s, 'edge · nginx', { x: 1.55, y: 2.4, w: 1.1, h: 0.5, bold: true, align: 'center', objectName: 'edge-nombre' });
  texto(s, 'auth_request valida el JWT', { x: 1.55, y: 2.95, w: 1.1, h: 1.05, fontSize: 13, color: C.atenuado, align: 'center', objectName: 'edge-subtitulo' });
  caja(s, { x: 3.05, y: 1.5, w: 1.9, h: 1.4, nombre: 'caja-replica-1' });
  texto(s, 'catalog-streaming #1', { x: 3.1, y: 1.5, w: 1.8, h: 1.4, bold: true, align: 'center', valign: 'middle', objectName: 'replica-1' });
  caja(s, { x: 3.05, y: 3.5, w: 1.9, h: 1.4, nombre: 'caja-replica-2', atenuada: true });
  texto(s, [{ text: 'catalog-streaming #2', options: { breakLine: true } }, { text: 'caída' }],
    { x: 3.1, y: 3.5, w: 1.8, h: 1.4, color: C.atenuado, align: 'center', valign: 'middle', objectName: 'replica-2' });
  texto(s, '×', { x: 4.6, y: 3.5, w: 0.3, h: 0.4, fontSize: 24, bold: true, color: C.rosa, align: 'center', valign: 'middle', objectName: 'equis-caida' });
  flecha(s, 1.3, 3.2, 1.5, 3.2, 'flecha-cliente');
  flecha(s, 2.7, 3.2, 3.05, 2.2, 'flecha-1');
  flecha(s, 2.7, 3.2, 3.05, 4.2, 'flecha-2', C.linea);
  panel(s, { x: 5.2, y: 1.4, w: 4.2, h: 2.0, nombre: 'panel-cifra' });
  texto(s, '0 / 293', { x: 5.3, y: 1.5, w: 4.0, h: 1.0, fontFace: F.titulo, bold: true, fontSize: 60, color: C.turquesa, valign: 'middle', objectName: 'cifra-0-293' });
  texto(s, 'peticiones fallidas al apagar una réplica', { x: 5.35, y: 2.6, w: 3.8, h: 0.6, fontSize: 15, objectName: 'cifra-leyenda' });
  texto(s, '+3 ms', { x: 5.2, y: 3.55, w: 2.2, h: 0.35, fontFace: F.titulo, bold: true, fontSize: 20, color: C.rosa, objectName: 'dato-auth-cifra' });
  texto(s, 'costo de auth_request en p50', { x: 5.2, y: 3.95, w: 2.3, h: 0.2, fontSize: 12, color: C.atenuado, objectName: 'dato-auth-etiqueta' });
  texto(s, '15 / 34 ms', { x: 7.6, y: 3.55, w: 1.95, h: 0.35, fontFace: F.titulo, bold: true, fontSize: 20, objectName: 'dato-songs-cifra' });
  texto(s, 'GET /api/songs p50 / p95', { x: 7.6, y: 3.95, w: 1.95, h: 0.2, fontSize: 12, color: C.atenuado, objectName: 'dato-songs-etiqueta' });
  pista(s, 'Lado A · 08 —\nfailover → 0 de 293 → costo: 3 ms', { w: 2.8, h: 0.9 });
  s.addNotes(NOTAS_RAMA_03);
}

module.exports = { agregar };
